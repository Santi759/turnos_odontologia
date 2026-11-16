# Autoprueba del runner y de la higiene del repositorio (ASCII, PowerShell 5.1).
# Termina con codigo distinto de cero si alguna verificacion falla.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot '..\lib\Pasos.ps1')

$script:Fallos = New-Object System.Collections.ArrayList

function Invoke-Caso {
    param([string]$Nombre, [scriptblock]$Bloque)
    try {
        & $Bloque
        Write-Host ("[OK]    " + $Nombre)
    } catch {
        [void]$script:Fallos.Add($Nombre)
        Write-Host ("[FALLA] " + $Nombre + " -> " + $_.Exception.Message)
    }
}

function Assert-Verdadero {
    param([bool]$Condicion, [string]$Mensaje)
    if (-not $Condicion) { throw $Mensaje }
}

Invoke-Caso 'Un paso falla' {
    $script:tercero = $false
    $mensaje = $null
    try {
        Invoke-Paso -Nombre 'paso uno' -Comando { cmd /c exit 0 }
        Invoke-Paso -Nombre 'paso dos' -Comando { cmd /c exit 3 }
        Invoke-Paso -Nombre 'paso tres' -Comando { $script:tercero = $true }
    } catch {
        $mensaje = $_.Exception.Message
    }
    Assert-Verdadero ($null -ne $mensaje) 'el runner no informo error'
    Assert-Verdadero ($mensaje -like '*paso dos*') 'el error no nombra el segundo paso'
    Assert-Verdadero (-not $script:tercero) 'el tercer paso se ejecuto'
}

Invoke-Caso 'Todos los pasos de la secuencia pasan' {
    $script:ejecutados = New-Object System.Collections.ArrayList
    Invoke-Paso -Nombre 'a' -Comando { [void]$script:ejecutados.Add('a'); cmd /c exit 0 }
    Invoke-Paso -Nombre 'b' -Comando { [void]$script:ejecutados.Add('b'); cmd /c exit 0 }
    Assert-Verdadero ($script:ejecutados.Count -eq 2) 'no se ejecutaron ambos pasos'
}

Invoke-Caso 'Falta el archivo .env' {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('autoprueba-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        $mensaje = $null
        try { Assert-RequisitosPrevios -Raiz $tmp } catch { $mensaje = $_.Exception.Message }
        Assert-Verdadero ($null -ne $mensaje) 'no informo error sin .env'
        Assert-Verdadero ($mensaje -like '*copiar .env.example a .env*') 'el mensaje no indica copiar .env.example a .env'
        Set-Content -Path (Join-Path $tmp '.env') -Value 'APP_ENV=local'
        Assert-RequisitosPrevios -Raiz $tmp
    } finally {
        Remove-Item -Recurse -Force $tmp
    }
    Assert-Verdadero (-not (Test-Path $tmp)) 'el directorio temporal no se elimino'
}

Invoke-Caso '.env ignorado por Git' {
    Push-Location $Raiz
    try {
        git check-ignore -q .env
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'Git no ignora .env'
    } finally { Pop-Location }
}

Invoke-Caso 'Plantilla completa con valores ficticios' {
    $ruta = Join-Path $Raiz '.env.example'
    Assert-Verdadero (Test-Path -LiteralPath $ruta) '.env.example no existe'
    $valores = @{}
    foreach ($linea in (Get-Content -LiteralPath $ruta)) {
        if ($linea -match '^\s*([A-Z_]+)=(.*)$') { $valores[$Matches[1]] = $Matches[2] }
    }
    $requeridas = @('DATABASE_URL', 'DATABASE_LOGIN_URL', 'DATABASE_MIGRATION_URL', 'TEST_DATABASE_URL', 'CORS_ALLOWED_ORIGINS', 'APP_ENV',
                    'AUTH_SECRET_KEY', 'AUTH_SESSION_MINUTES', 'AUTH_SESSION_MAX_HOURS', 'AUTH_COOKIE_SECURE',
                    'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'VITE_API_BASE_URL')
    foreach ($nombre in $requeridas) {
        Assert-Verdadero ($valores.ContainsKey($nombre)) ('falta la variable ' + $nombre)
    }
    Assert-Verdadero ($valores['POSTGRES_PASSWORD'] -eq 'app') 'POSTGRES_PASSWORD no es el valor ficticio app'
    $usuariosEsperados = [ordered]@{ DATABASE_URL = 'turnos_app'; DATABASE_LOGIN_URL = 'turnos_login'; DATABASE_MIGRATION_URL = 'app' }
    foreach ($nombre in $usuariosEsperados.Keys) {
        $esperado = $usuariosEsperados[$nombre]
        $coincide = $valores.ContainsKey($nombre) -and ($valores[$nombre] -like ('*://' + $esperado + ':*@*'))
        Assert-Verdadero $coincide ('el usuario de ' + $nombre + ' no es ' + $esperado)
    }
    Assert-Verdadero ($valores['TEST_DATABASE_URL'] -like '*@db-test:*/*_test') 'TEST_DATABASE_URL no apunta a db-test / base *_test'
    Assert-Verdadero ($valores['AUTH_SECRET_KEY'] -eq 'REEMPLAZAR_generar_con_secrets_token_urlsafe_48') 'AUTH_SECRET_KEY no es el marcador rechazado de la plantilla'
    Assert-Verdadero ($valores['AUTH_COOKIE_SECURE'] -eq 'true') 'AUTH_COOKIE_SECURE de la plantilla no es true'
    $textoPlantilla = Get-Content -LiteralPath $ruta -Raw
    Assert-Verdadero ($textoPlantilla.Contains('secrets.token_urlsafe(48)')) 'falta el comentario con secrets.token_urlsafe(48)'
    $prohibidas = @($valores.Keys | Where-Object { $_ -like 'EMAIL_*' })
    Assert-Verdadero ($prohibidas.Count -eq 0) ('variables no permitidas: ' + ($prohibidas -join ', '))
}

function Get-ConfiguracionCompose {
    Push-Location $Raiz
    try {
        $texto = docker compose --profile test config --format json | Out-String
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'docker compose config fallo'
        return ($texto | ConvertFrom-Json)
    } finally { Pop-Location }
}

Invoke-Caso 'El arranque de la API no migra' {
    $compose = Get-ConfiguracionCompose
    $comando = @($compose.services.api.command) -join ' '
    Assert-Verdadero ($comando -like '*uvicorn*') 'el comando de api no es uvicorn'
    Assert-Verdadero ($comando -notlike '*alembic*') 'el arranque de api invoca alembic'
    $entrypoint = ''
    if ($compose.services.api.PSObject.Properties.Name -contains 'entrypoint') {
        $entrypoint = @($compose.services.api.entrypoint) -join ' '
    }
    Assert-Verdadero ($entrypoint -notlike '*alembic*') 'el entrypoint de api invoca alembic'
}

Invoke-Caso 'El arranque de la API no ejecuta el seed' {
    $compose = Get-ConfiguracionCompose
    $comando = @($compose.services.api.command) -join ' '
    Assert-Verdadero ($comando -notlike '*app.seed*') 'el arranque de api invoca el seed'
    $entrypoint = ''
    if ($compose.services.api.PSObject.Properties.Name -contains 'entrypoint') {
        $entrypoint = @($compose.services.api.entrypoint) -join ' '
    }
    Assert-Verdadero ($entrypoint -notlike '*app.seed*') 'el entrypoint de api invoca el seed'
}

Invoke-Caso 'El arranque de la API no procesa cabeceras de proxy' {
    # DD-19: la IP del limite es la de la conexion directa; uvicorn no debe reescribirla desde
    # X-Forwarded-For (por defecto confia en 127.0.0.1). Se inspecciona el comando EFECTIVO de compose.
    $compose = Get-ConfiguracionCompose
    $comando = @($compose.services.api.command) -join ' '
    Assert-Verdadero ($comando -like '*uvicorn*') 'el comando de api no es uvicorn'
    Assert-Verdadero ($comando -like '*--no-proxy-headers*') 'el comando de api no incluye --no-proxy-headers'
    Assert-Verdadero ($comando -notlike '*--proxy-headers*') 'el comando de api habilita --proxy-headers'
    Assert-Verdadero ($comando -notlike '*--forwarded-allow-ips*') 'el comando de api configura --forwarded-allow-ips'
}

Invoke-Caso 'Base de pruebas separada y efimera' {
    $compose = Get-ConfiguracionCompose
    $servicio = $compose.services.'db-test'
    Assert-Verdadero ($servicio.profiles -contains 'test') 'db-test no esta en el perfil test'
    $nombres = $servicio.PSObject.Properties.Name
    $puertos = @()
    if ($nombres -contains 'ports') { $puertos = @($servicio.ports) }
    Assert-Verdadero ($puertos.Count -eq 0) 'db-test publica puertos en el host'
    $tmpfs = @()
    if ($nombres -contains 'tmpfs') { $tmpfs = @($servicio.tmpfs) }
    Assert-Verdadero ($tmpfs -contains '/var/lib/postgresql') 'db-test no usa tmpfs en /var/lib/postgresql'
    $volumenes = @()
    if ($nombres -contains 'volumes') { $volumenes = @($servicio.volumes) }
    # Unico montaje admitido: el script de roles de prueba, bind de solo lectura (DD-14).
    Assert-Verdadero ($volumenes.Count -eq 1) 'db-test debe declarar exactamente un montaje (el script de roles)'
    Assert-Verdadero ($volumenes[0].type -eq 'bind') 'el montaje de db-test no es de tipo bind (volumen con nombre)'
    Assert-Verdadero ($volumenes[0].read_only -eq $true) 'el montaje del script de roles no es de solo lectura'
    Assert-Verdadero ($volumenes[0].target -eq '/docker-entrypoint-initdb.d/10_roles_prueba.sh') 'el destino del montaje no es el script de roles'
    Assert-Verdadero ($volumenes[0].source -like '*10_roles_prueba.sh') 'el origen del montaje no es 10_roles_prueba.sh'
    # Las contrasenas se declaran por nombre, sin valor (se leen del archivo, no de config).
    $textoCompose = Get-Content -LiteralPath (Join-Path $Raiz 'docker-compose.yml') -Raw
    $bloque = [regex]::Match($textoCompose, '(?ms)^  db-test:.*?(?=^  api:)').Value
    foreach ($variable in @('TURNOS_APP_TEST_PASSWORD', 'TURNOS_LOGIN_TEST_PASSWORD')) {
        Assert-Verdadero ($bloque -match ('(?m)^      - ' + $variable + '\s*$')) ('db-test no declara ' + $variable + ' por nombre')
        Assert-Verdadero (-not ($bloque -match ($variable + '\s*[:=]'))) ('db-test da valor a ' + $variable)
    }
    Assert-Verdadero ($servicio.image -eq 'postgres:18.6-trixie') 'db-test no usa postgres:18.6-trixie'
    $dev = $compose.services.db
    $montajes = @($dev.volumes | Where-Object { $_.source -eq 'pgdata' })
    Assert-Verdadero ($montajes.Count -eq 1) 'db (desarrollo) no conserva el volumen pgdata'
}

# --- DD-34 (RT3-01): entorno de la API separado del entorno administrativo ----------------------
# Estructura de compose SIN interpolar y SIN resolver archivos de entorno: no se leen valores del .env.
function Get-EstructuraCompose {
    Push-Location $Raiz
    try {
        $texto = docker compose --profile test --profile admin config --no-interpolate --no-env-resolution --format json | Out-String
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'docker compose config (estructura) fallo'
        return ($texto | ConvertFrom-Json)
    } finally { Pop-Location }
}

# RT3-06: TEST_DATABASE_URL ya no forma parte del entorno permanente de api (9 claves).
$script:VariablesPermitidasApi = @('DATABASE_URL', 'DATABASE_LOGIN_URL', 'AUTH_SECRET_KEY', 'CORS_ALLOWED_ORIGINS', 'APP_ENV',
    'AUTH_SESSION_MINUTES', 'AUTH_SESSION_MAX_HOURS', 'AUTH_COOKIE_SECURE', 'WATCHFILES_FORCE_POLLING')
$script:ObligatoriasApi = @('DATABASE_URL', 'DATABASE_LOGIN_URL', 'AUTH_SECRET_KEY', 'CORS_ALLOWED_ORIGINS', 'APP_ENV')
$script:OpcionalesApi = @('AUTH_SESSION_MINUTES', 'AUTH_SESSION_MAX_HOURS', 'AUTH_COOKIE_SECURE')
$script:VariablesDeAdministracion = @('DATABASE_MIGRATION_URL', 'POSTGRES_PASSWORD', 'POSTGRES_USER', 'POSTGRES_DB', 'PGPASSWORD')
# Variables que el proceso permanente de api nunca recibe, aunque esten definidas en el shell.
$script:VariablesAjenasAApi = $script:VariablesDeAdministracion + @('TEST_DATABASE_URL')

Invoke-Caso 'Entorno de la API limitado a variables permitidas' {
    $api = (Get-EstructuraCompose).services.api
    $propiedades = @($api.PSObject.Properties.Name)
    Assert-Verdadero ($propiedades -notcontains 'env_file') 'api usa env_file'
    Assert-Verdadero ($propiedades -contains 'environment') 'api no declara environment'
    $entorno = $api.environment
    $claves = @($entorno.PSObject.Properties.Name)
    $sobrantes = @($claves | Where-Object { $script:VariablesPermitidasApi -notcontains $_ })
    $faltantes = @($script:VariablesPermitidasApi | Where-Object { $claves -notcontains $_ })
    Assert-Verdadero ($sobrantes.Count -eq 0) ('api recibe variables no permitidas: ' + ($sobrantes -join ', '))
    Assert-Verdadero ($faltantes.Count -eq 0) ('api no declara: ' + ($faltantes -join ', '))
    foreach ($nombre in $script:ObligatoriasApi) {
        $valor = [string]$entorno.$nombre
        Assert-Verdadero ($valor -match ('^\$\{' + $nombre + ':\?.+\}$')) ($nombre + ' no se interpola como obligatoria (${' + $nombre + ':?...})')
    }
    foreach ($nombre in $script:OpcionalesApi) {
        $valor = [string]$entorno.$nombre
        Assert-Verdadero ($valor -eq ('${' + $nombre + ':-}')) ($nombre + ' no se interpola como opcional (${' + $nombre + ':-})')
    }
    Assert-Verdadero ([string]$entorno.WATCHFILES_FORCE_POLLING -eq 'true') 'WATCHFILES_FORCE_POLLING no es el literal true'
}

Invoke-Caso 'Servicio administrativo efimero (admin)' {
    $compose = Get-EstructuraCompose
    $servicios = @($compose.services.PSObject.Properties.Name)
    Assert-Verdadero ($servicios -contains 'admin') 'no existe el servicio admin'
    $admin = $compose.services.admin
    $propiedades = @($admin.PSObject.Properties.Name)
    Assert-Verdadero ($propiedades -contains 'profiles' -and @($admin.profiles) -contains 'admin') 'admin no esta en el perfil admin'
    Assert-Verdadero ($propiedades -contains 'restart' -and $admin.restart -eq 'no') 'admin no declara restart: "no"'
    Assert-Verdadero ($propiedades -contains 'env_file') 'admin no carga env_file'
    $archivos = @($admin.env_file | ForEach-Object { if ($_ -is [string]) { $_ } else { $_.path } })
    Assert-Verdadero (@($archivos | Where-Object { $_ -match '(^|[\\/])\.env$' }).Count -eq 1) 'admin no carga .env'
    $puertos = @()
    if ($propiedades -contains 'ports') { $puertos = @($admin.ports) }
    Assert-Verdadero ($puertos.Count -eq 0) 'admin publica puertos'
    $comando = @($admin.command) -join ' '
    Assert-Verdadero ($comando -like '*sys.exit(*') 'el comando por defecto de admin no termina con error'
    Assert-Verdadero ($comando -like '*docker compose run --rm --no-deps admin*') 'el comando por defecto de admin no indica el uso con run'
    Assert-Verdadero ($comando -notlike '*uvicorn*') 'admin arranca uvicorn'
    Assert-Verdadero (-not [string]::IsNullOrEmpty($compose.services.api.image)) 'api no declara image'
    Assert-Verdadero ($admin.image -eq $compose.services.api.image) 'admin no usa la imagen del backend de api'
    foreach ($nombre in $servicios) {
        $servicio = $compose.services.$nombre
        if (@($servicio.PSObject.Properties.Name) -contains 'depends_on') {
            Assert-Verdadero (@($servicio.depends_on.PSObject.Properties.Name) -notcontains 'admin') ($nombre + ' depende de admin')
        }
    }
}

Invoke-Caso 'db y db-test sin cambios por DD-34' {
    $compose = Get-EstructuraCompose
    $db = $compose.services.db
    $propiedades = @($db.PSObject.Properties.Name | Sort-Object)
    $esperadas = @('env_file', 'healthcheck', 'image', 'networks', 'ports', 'volumes')
    Assert-Verdadero ((@($propiedades) -join ',') -eq ($esperadas -join ',')) ('db cambio de estructura: ' + ($propiedades -join ','))
    Assert-Verdadero ($db.image -eq 'postgres:18.6-trixie') 'db no usa postgres:18.6-trixie'
    $dbTest = $compose.services.'db-test'
    Assert-Verdadero (@($dbTest.PSObject.Properties.Name) -notcontains 'env_file') 'db-test carga env_file'
}

Invoke-Caso 'Codigo de solo lectura en api y admin (DD-34, RT3-05)' {
    $compose = Get-EstructuraCompose
    foreach ($nombre in @('api', 'admin')) {
        $servicio = $compose.services.$nombre
        $propiedades = @($servicio.PSObject.Properties.Name)
        foreach ($privilegio in @('privileged', 'cap_add', 'security_opt')) {
            Assert-Verdadero ($propiedades -notcontains $privilegio) ($nombre + ' declara ' + $privilegio)
        }
        $montajes = @()
        if ($propiedades -contains 'volumes') { $montajes = @($servicio.volumes) }
        $codigo = @($montajes | Where-Object { $_.target -eq '/app' })
        Assert-Verdadero ($codigo.Count -eq 1) ($nombre + ' no monta el codigo en /app exactamente una vez')
        Assert-Verdadero ($codigo[0].type -eq 'bind' -and ([string]$codigo[0].source) -match '[\\/]backend$') ($nombre + ' no monta ./backend en /app')
        $soloLectura = (@($codigo[0].PSObject.Properties.Name) -contains 'read_only') -and ($codigo[0].read_only -eq $true)
        Assert-Verdadero $soloLectura ($nombre + ' monta /app con escritura')
        foreach ($montaje in $montajes) {
            $sobreCodigo = (([string]$montaje.target) -like '/app*') -or (([string]$montaje.source) -match '[\\/]backend([\\/]|$)')
            $esLectura = (@($montaje.PSObject.Properties.Name) -contains 'read_only') -and ($montaje.read_only -eq $true)
            Assert-Verdadero (-not $sobreCodigo -or $esLectura) ($nombre + ' tiene un montaje escribible sobre el codigo: ' + $montaje.target)
        }
    }
}

Invoke-Caso 'db-test con contrasena efimera del superusuario, sin literal (RT3-06)' {
    $entorno = @((Get-EstructuraCompose).services.'db-test'.environment)
    Assert-Verdadero ($entorno -contains 'POSTGRES_PASSWORD=${TURNOS_DB_TEST_PASSWORD:-}') 'db-test no toma POSTGRES_PASSWORD de TURNOS_DB_TEST_PASSWORD'
    $literales = @($entorno | Where-Object { $_ -like 'POSTGRES_PASSWORD=*' -and $_ -ne 'POSTGRES_PASSWORD=${TURNOS_DB_TEST_PASSWORD:-}' })
    Assert-Verdadero ($literales.Count -eq 0) 'db-test declara otra POSTGRES_PASSWORD'
    $texto = Get-Content -LiteralPath (Join-Path $Raiz 'docker-compose.yml') -Raw
    Assert-Verdadero (-not ($texto -match 'POSTGRES_PASSWORD\s*[:=]\s*app\b')) 'docker-compose.yml contiene una contrasena literal de db-test'
}

Invoke-Caso 'URL de la base de pruebas: host db-test y base _test (RT3-06)' {
    $comando = Get-Command -Name 'New-UrlBaseDePruebas' -ErrorAction SilentlyContinue
    Assert-Verdadero ($null -ne $comando) 'no existe New-UrlBaseDePruebas'
    $url = New-UrlBaseDePruebas -Contrasena 'contrasena-ficticia-autoprueba'
    Assert-Verdadero ($url -cmatch '^postgresql\+psycopg://app:contrasena-ficticia-autoprueba@db-test:5432/[a-z_]+_test$') 'la URL de pruebas no apunta a db-test con una base _test'
    $pasos = Get-Content -LiteralPath (Join-Path $Raiz 'scripts/lib/Pasos.ps1') -Raw
    # Los marcadores de formato ({1}) no son contrasenas; cualquier otro texto entre ':' y '@' si.
    Assert-Verdadero (-not ($pasos -match '://[^/@\s]+:(?!\{\d+\}@)[^@\s$]+@')) 'Pasos.ps1 contiene una URL con contrasena literal'
    Assert-Verdadero ('postgresql+psycopg://app:literal@db-test:5432/x' -match '://[^/@\s]+:(?!\{\d+\}@)[^@\s$]+@') 'la deteccion de contrasenas literales no funciona'
}

Invoke-Caso 'test.ps1: URL de pruebas efimera solo por nombre y retirada (RT3-06)' {
    $texto = Get-Content -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Raw
    Assert-Verdadero ($texto.Contains('$env:TURNOS_DB_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera')) 'test.ps1 no genera la contrasena efimera de db-test'
    Assert-Verdadero ($texto.Contains('$env:TEST_DATABASE_URL = New-UrlBaseDePruebas -Contrasena $env:TURNOS_DB_TEST_PASSWORD')) 'test.ps1 no arma TEST_DATABASE_URL con la contrasena efimera'
    $asignacion = $texto.IndexOf('$env:TEST_DATABASE_URL = ')
    Assert-Verdadero ($asignacion -ge 0 -and $asignacion -lt $texto.IndexOf('Invoke-Paso')) 'TEST_DATABASE_URL no se fija antes del primer paso (podria reutilizar un valor externo)'
    Assert-Verdadero (-not $texto.Contains('postgresql+psycopg://')) 'test.ps1 contiene una URL literal'
    $lineas = $texto -split "`r?`n"
    $conUrl = @($lineas | Where-Object { $_ -match '-e TEST_DATABASE_URL\b' })
    Assert-Verdadero ($conUrl.Count -eq 3) ('-e TEST_DATABASE_URL aparece ' + $conUrl.Count + ' veces (se esperaban 3)')
    foreach ($marca in @('alembic -x target=test', 'tests/integration', 'tests/isolation')) {
        Assert-Verdadero (@($conUrl | Where-Object { $_ -like ('*' + $marca + '*') }).Count -eq 1) ('el paso ' + $marca + ' no recibe TEST_DATABASE_URL por nombre')
    }
    Assert-Verdadero (@($lineas | Where-Object { $_ -like '*tests/unit*' -and $_ -match 'TEST_DATABASE_URL' }).Count -eq 0) 'las unitarias reciben TEST_DATABASE_URL'
    $final = $texto.Substring([Math]::Max(0, $texto.LastIndexOf('finally')))
    Assert-Verdadero ($final.Contains('Env:TURNOS_DB_TEST_PASSWORD')) 'el bloque final no retira TURNOS_DB_TEST_PASSWORD'
    Assert-Verdadero ($final.Contains('TEST_DATABASE_URL')) 'el bloque final no restaura TEST_DATABASE_URL'
}

Invoke-Caso 'db-test sin la contrasena efimera del superusuario no arranca (proyecto aislado, RT3-06)' {
    # Toma el entorno REAL de db-test (sin interpolar) y lo levanta en un proyecto aislado con las
    # contrasenas de los roles pero SIN TURNOS_DB_TEST_PASSWORD: PostgreSQL no debe inicializar.
    $entorno = @((Get-EstructuraCompose).services.'db-test'.environment)
    $nombreProyecto = 'autoprueba-sinsuperusuario'
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ($nombreProyecto + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $script = (Join-Path $Raiz 'db/test-init/10_roles_prueba.sh').Replace('\', '/')
    $archivoCompose = Join-Path $tmp 'docker-compose.yml'
    $compose = @('services:', '  db-test:', '    image: postgres:18.6-trixie', '    profiles: ["test"]', '    environment:')
    $compose += @($entorno | ForEach-Object { '      - "' + $_ + '"' })
    $compose += @('    tmpfs:', '      - /var/lib/postgresql', '    volumes:', '      - type: bind',
        ('        source: "' + $script + '"'), '        target: /docker-entrypoint-initdb.d/10_roles_prueba.sh', '        read_only: true',
        '    healthcheck:', '      test: ["CMD-SHELL", "pg_isready -U app -d turnos_test"]', '      interval: 2s', '      timeout: 5s', '      retries: 15')
    [System.IO.File]::WriteAllText($archivoCompose, (($compose -join "`n") + "`n"), (New-Object System.Text.ASCIIEncoding))
    $previos = @{}
    foreach ($nombre in @('TURNOS_DB_TEST_PASSWORD', 'TURNOS_APP_TEST_PASSWORD', 'TURNOS_LOGIN_TEST_PASSWORD')) {
        $previos[$nombre] = [Environment]::GetEnvironmentVariable($nombre, 'Process')
    }
    try {
        [Environment]::SetEnvironmentVariable('TURNOS_DB_TEST_PASSWORD', $null, 'Process')
        [Environment]::SetEnvironmentVariable('TURNOS_APP_TEST_PASSWORD', (New-ContrasenaRolPruebaEfimera), 'Process')
        [Environment]::SetEnvironmentVariable('TURNOS_LOGIN_TEST_PASSWORD', (New-ContrasenaRolPruebaEfimera), 'Process')
        docker compose -p $nombreProyecto -f $archivoCompose --profile test up -d --wait db-test | Out-Null
        Assert-Verdadero ($LASTEXITCODE -ne 0) 'db-test arranco sin la contrasena efimera del superusuario'
        $enEjecucion = @(docker compose -p $nombreProyecto -f $archivoCompose --profile test ps --status running -q)
        Assert-Verdadero ($enEjecucion.Count -eq 0) 'db-test quedo en ejecucion sin la contrasena efimera del superusuario'
    } finally {
        foreach ($nombre in $previos.Keys) { [Environment]::SetEnvironmentVariable($nombre, $previos[$nombre], 'Process') }
        docker compose -p $nombreProyecto -f $archivoCompose --profile test down --remove-orphans | Out-Null
        Remove-Item -Recurse -Force $tmp
    }
}

Invoke-Caso 'Comandos administrativos documentados con admin (DD-34)' {
    $administrativos = '(alembic\s+upgrade|python\s+-m\s+app\.(seed|credenciales|roles_postgres|mantenimiento))'
    $readme = Get-Content -LiteralPath (Join-Path $Raiz 'README.md') -Raw -Encoding UTF8
    Assert-Verdadero (-not ($readme -match ('compose\s+run[^\r\n`]*\sapi\s+' + $administrativos))) 'README indica un comando administrativo con el servicio api'
    Assert-Verdadero ($readme.Contains('docker compose run --rm --no-deps admin alembic upgrade head')) 'README no indica las migraciones con admin'
    Assert-Verdadero ($readme.Contains('docker compose run --rm --no-deps admin python -m app.seed')) 'README no indica el seed con admin'
    foreach ($modulo in @('credenciales', 'roles_postgres', 'mantenimiento')) {
        $texto = Get-Content -LiteralPath (Join-Path $Raiz ('backend/app/' + $modulo + '/__main__.py')) -Raw -Encoding UTF8
        Assert-Verdadero (-not ($texto -match ('compose\s+run[^\r\n]*\sapi\s+python\s+-m\s+app\.' + $modulo))) ('la ayuda de app.' + $modulo + ' usa el servicio api')
        Assert-Verdadero ($texto -match ('docker compose run --rm (-it )?--no-deps admin python -m app\.' + $modulo)) ('la ayuda de app.' + $modulo + ' no usa admin con --no-deps')
    }
}

Invoke-Caso 'Variables administrativas del shell no llegan a api' {
    # Se definen con valores ficticios SOLO en este proceso y se crea un contenedor efimero de api
    # sin -e: el contenedor no debe recibirlas. Solo se listan NOMBRES de variables.
    $previos = @{}
    foreach ($nombre in $script:VariablesAjenasAApi) {
        $previos[$nombre] = [Environment]::GetEnvironmentVariable($nombre, 'Process')
        [Environment]::SetEnvironmentVariable($nombre, 'valor-ficticio-autoprueba', 'Process')
    }
    Push-Location $Raiz
    try {
        $salida = docker compose run --rm --no-deps -T api sh -c 'env | cut -d= -f1'
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'no se pudo crear el contenedor efimero de api'
        $nombres = @($salida | ForEach-Object { ([string]$_).Trim() })
        Assert-Verdadero ($nombres -contains 'DATABASE_URL') 'el contenedor de api no recibio DATABASE_URL'
        $filtradas = @($script:VariablesAjenasAApi | Where-Object { $nombres -contains $_ })
        Assert-Verdadero ($filtradas.Count -eq 0) ('api recibio: ' + ($filtradas -join ', '))
    } finally {
        Pop-Location
        foreach ($nombre in $script:VariablesAjenasAApi) {
            [Environment]::SetEnvironmentVariable($nombre, $previos[$nombre], 'Process')
        }
    }
}

Invoke-Caso 'Verificacion de tipos estricta' {
    $ruta = Join-Path $Raiz 'frontend/tsconfig.json'
    Assert-Verdadero (Test-Path -LiteralPath $ruta) 'frontend/tsconfig.json no existe'
    $tsconfig = Get-Content -LiteralPath $ruta -Raw | ConvertFrom-Json
    Assert-Verdadero ($tsconfig.compilerOptions.strict -eq $true) 'tsconfig no tiene strict: true'
    Assert-Verdadero ($tsconfig.compilerOptions.noEmit -eq $true) 'tsconfig no tiene noEmit: true'
}

Invoke-Caso 'Sin any en el codigo del frontend' {
    $archivos = @(Get-ChildItem -Path (Join-Path $Raiz 'frontend/src') -Recurse -Include *.ts, *.tsx)
    Assert-Verdadero ($archivos.Count -gt 0) 'no se encontraron archivos .ts/.tsx'
    $coincidencias = @($archivos | Select-String -Pattern '\bany\b')
    Assert-Verdadero ($coincidencias.Count -eq 0) ('uso de any en: ' + (($coincidencias | ForEach-Object { $_.Path + ':' + $_.LineNumber }) -join ', '))
}

Invoke-Caso 'Pruebas existentes en verde (archivo sin cambios)' {
    Push-Location $Raiz
    try {
        git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'test_superposicion_turnos.py cambio respecto de f13f0ba'
        git diff --quiet f13f0ba -- backend/app/domain/superposicion_turnos.py
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'superposicion_turnos.py cambio respecto de f13f0ba'
    } finally { Pop-Location }
}

Invoke-Caso 'test.ps1 sin .env termina con error antes de cualquier suite' {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('autoprueba-runner-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path (Join-Path $tmp 'scripts/lib') -Force | Out-Null
    try {
        Copy-Item -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Destination (Join-Path $tmp 'scripts/test.ps1')
        Copy-Item -LiteralPath (Join-Path $Raiz 'scripts/lib/Pasos.ps1') -Destination (Join-Path $tmp 'scripts/lib/Pasos.ps1')
        $salida = (powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tmp 'scripts/test.ps1') | Out-String)
        $codigo = $LASTEXITCODE
        Assert-Verdadero ($codigo -ne 0) 'test.ps1 termino con codigo 0 sin .env'
        Assert-Verdadero ($salida -like '*copiar .env.example a .env*') 'el mensaje no indica copiar .env.example a .env'
        Assert-Verdadero ($salida -notlike '*==> *') 'se ejecuto algun paso antes de verificar .env'
    } finally {
        Remove-Item -Recurse -Force $tmp
    }
}

Invoke-Caso 'Verificacion previa: variable de administracion en PowerShell (DD-34)' {
    $comando = Get-Command -Name 'Assert-SinCredencialesDeAdministracion' -ErrorAction SilentlyContinue
    Assert-Verdadero ($null -ne $comando) 'no existe Assert-SinCredencialesDeAdministracion'
    foreach ($nombre in @('DATABASE_MIGRATION_URL', 'POSTGRES_PASSWORD', 'PGPASSWORD')) {
        $previo = [Environment]::GetEnvironmentVariable($nombre, 'Process')
        [Environment]::SetEnvironmentVariable($nombre, 'valor-ficticio-autoprueba', 'Process')
        try {
            $mensaje = $null
            try { Assert-SinCredencialesDeAdministracion } catch { $mensaje = $_.Exception.Message }
            Assert-Verdadero ($null -ne $mensaje) ('no rechazo ' + $nombre)
            Assert-Verdadero ($mensaje -like ('*' + $nombre + '*')) ('el mensaje no nombra ' + $nombre)
            Assert-Verdadero ($mensaje -notlike '*valor-ficticio-autoprueba*') 'el mensaje contiene el valor'
        } finally {
            [Environment]::SetEnvironmentVariable($nombre, $previo, 'Process')
        }
    }
}

Invoke-Caso 'test.ps1 con variable de administracion termina antes de cualquier paso' {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('autoprueba-runner-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path (Join-Path $tmp 'scripts/lib') -Force | Out-Null
    $previo = [Environment]::GetEnvironmentVariable('DATABASE_MIGRATION_URL', 'Process')
    try {
        Copy-Item -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Destination (Join-Path $tmp 'scripts/test.ps1')
        Copy-Item -LiteralPath (Join-Path $Raiz 'scripts/lib/Pasos.ps1') -Destination (Join-Path $tmp 'scripts/lib/Pasos.ps1')
        # Un .env vacio en la copia: el rechazo debe venir de la variable, no de la falta de .env.
        Set-Content -LiteralPath (Join-Path $tmp '.env') -Value '' -Encoding Ascii
        [Environment]::SetEnvironmentVariable('DATABASE_MIGRATION_URL', 'valor-ficticio-autoprueba', 'Process')
        $salida = (powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tmp 'scripts/test.ps1') | Out-String)
        $codigo = $LASTEXITCODE
        Assert-Verdadero ($codigo -ne 0) 'test.ps1 termino con codigo 0 con DATABASE_MIGRATION_URL definida'
        Assert-Verdadero ($salida -like '*DATABASE_MIGRATION_URL*') 'el mensaje no nombra DATABASE_MIGRATION_URL'
        Assert-Verdadero ($salida -notlike '*valor-ficticio-autoprueba*') 'la salida contiene el valor'
        Assert-Verdadero ($salida -notlike '*==> *') 'se ejecuto algun paso antes de la verificacion previa'
    } finally {
        [Environment]::SetEnvironmentVariable('DATABASE_MIGRATION_URL', $previo, 'Process')
        Remove-Item -Recurse -Force $tmp
    }
}

Invoke-Caso 'test.ps1: sin variables de administracion en opciones -e' {
    $texto = Get-Content -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Raw
    foreach ($nombre in @('DATABASE_MIGRATION_URL', 'POSTGRES_PASSWORD', 'POSTGRES_USER', 'POSTGRES_DB', 'PGPASSWORD')) {
        Assert-Verdadero (-not ($texto -match ('-e\s+' + $nombre + '\b'))) ('test.ps1 pasa -e ' + $nombre)
    }
    $previa = $texto.IndexOf('Assert-SinCredencialesDeAdministracion')
    $primerPaso = $texto.IndexOf('Invoke-Paso')
    Assert-Verdadero ($previa -ge 0) 'test.ps1 no ejecuta la verificacion previa de variables de administracion'
    Assert-Verdadero ($previa -lt $primerPaso) 'la verificacion previa no esta antes del primer paso'
}

Invoke-Caso 'Clave efimera de autenticacion: formato, diversidad y unicidad' {
    $primera = New-ClaveAuthEfimera
    $segunda = New-ClaveAuthEfimera
    Assert-Verdadero ($primera -cmatch '^[A-Za-z0-9_-]{64}$') 'la clave no tiene 64 caracteres base64url sin relleno'
    Assert-Verdadero (@($primera.ToCharArray() | Select-Object -Unique).Count -ge 20) 'la clave tiene menos de 20 caracteres distintos'
    Assert-Verdadero ($primera -ne $segunda) 'dos claves generadas son iguales'
    foreach ($marcador in @('cambiar', 'reemplazar', 'example', 'secret', 'password')) {
        Assert-Verdadero (-not $primera.ToLowerInvariant().Contains($marcador)) 'la clave contiene un marcador rechazado'
    }
}

Invoke-Caso 'test.ps1: clave por nombre, sin literal y retirada del entorno' {
    $texto = Get-Content -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Raw
    Assert-Verdadero (-not ($texto -match 'AUTH_SECRET_KEY\s*=\s*[''"]')) 'test.ps1 asigna AUTH_SECRET_KEY con un literal'
    Assert-Verdadero ($texto -match '\$env:AUTH_SECRET_KEY\s*=\s*New-ClaveAuthEfimera') 'la clave no proviene de New-ClaveAuthEfimera'
    Assert-Verdadero (-not ($texto -match '-e\s+AUTH_SECRET_KEY=')) 'test.ps1 pasa la clave con valor en -e'
    $porNombre = @([regex]::Matches($texto, '-e AUTH_SECRET_KEY(?![=\w])'))
    Assert-Verdadero ($porNombre.Count -eq 3) ('se esperaban 3 usos de -e AUTH_SECRET_KEY por nombre (alembic, integracion y aislamiento) y hay ' + $porNombre.Count)
    Assert-Verdadero ($texto.Contains('$env:AUTH_SECRET_KEY')) 'test.ps1 no deja la clave en el entorno del proceso'
    Assert-Verdadero ($texto -match 'Remove-Item Env:AUTH_SECRET_KEY') 'test.ps1 no retira la clave del entorno'
    Assert-Verdadero (-not ($texto -match 'Write-Host[^\r\n]*AUTH_SECRET_KEY')) 'test.ps1 muestra la clave'
}

Invoke-Caso 'Contrasena efimera de rol de prueba: formato y unicidad' {
    $primera = New-ContrasenaRolPruebaEfimera
    $segunda = New-ContrasenaRolPruebaEfimera
    Assert-Verdadero ($primera -cmatch '^[A-Za-z0-9_-]{43}$') 'la contrasena no tiene 43 caracteres base64url sin relleno'
    Assert-Verdadero ($segunda -cmatch '^[A-Za-z0-9_-]{43}$') 'la segunda contrasena no tiene 43 caracteres base64url sin relleno'
    Assert-Verdadero ($primera -ne $segunda) 'dos contrasenas generadas son iguales'
}

Invoke-Caso 'test.ps1: contrasenas de los roles por nombre, sin literal y retiradas' {
    $texto = Get-Content -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Raw
    foreach ($variable in @('TURNOS_APP_TEST_PASSWORD', 'TURNOS_LOGIN_TEST_PASSWORD')) {
        Assert-Verdadero (-not ($texto -match ($variable + '\s*=\s*[''"]'))) ('test.ps1 asigna ' + $variable + ' con un literal')
        Assert-Verdadero ($texto -match ('\$env:' + $variable + '\s*=\s*New-ContrasenaRolPruebaEfimera')) ($variable + ' no proviene de New-ContrasenaRolPruebaEfimera')
        Assert-Verdadero (-not ($texto -match ('-e\s+' + $variable + '='))) ('test.ps1 pasa ' + $variable + ' con valor en -e')
        $porNombre = @([regex]::Matches($texto, ('-e ' + $variable + '(?![=\w])')))
        Assert-Verdadero ($porNombre.Count -eq 1) ('se esperaba 1 uso de -e ' + $variable + ' por nombre y hay ' + $porNombre.Count)
        Assert-Verdadero ($texto -match ('Remove-Item Env:' + $variable)) ('test.ps1 no retira ' + $variable + ' del entorno')
        Assert-Verdadero (-not ($texto -match ('Write-Host[^\r\n]*' + $variable))) ('test.ps1 muestra ' + $variable)
    }
}

Invoke-Caso 'Paso de aislamiento despues de integracion' {
    $texto = Get-Content -LiteralPath (Join-Path $Raiz 'scripts/test.ps1') -Raw
    $integracion = $texto.IndexOf('pytest -p no:cacheprovider tests/integration')
    $aislamiento = $texto.IndexOf('pytest -p no:cacheprovider tests/isolation')
    $frontend = $texto.IndexOf('npm run typecheck')
    Assert-Verdadero ($integracion -ge 0) 'falta el paso de integracion'
    Assert-Verdadero ($aislamiento -gt $integracion) 'el paso de aislamiento no sigue al de integracion'
    Assert-Verdadero ($frontend -gt $aislamiento) 'el paso de aislamiento no precede al del frontend'
    Assert-Verdadero ($texto -match '6\. pruebas de aislamiento con los roles turnos_app y turnos_login \(db-test\)') 'el paso 6 no tiene el nombre esperado'
    Assert-Verdadero ($texto -match '7\. verificacion de tipos del frontend') 'el paso de tipos no es el 7'
    Assert-Verdadero ($texto -match '8\. pruebas del frontend') 'el paso de Vitest no es el 8'
}

Invoke-Caso 'db-test sin contrasenas no arranca (proyecto aislado)' {
    # Proyecto de Compose propio, con el mismo script de roles y SIN las contrasenas: el script
    # falla en la inicializacion y `up --wait` termina con error. No toca el Compose de desarrollo.
    $nombreProyecto = 'autoprueba-sinroles'
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ($nombreProyecto + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $script = (Join-Path $Raiz 'db/test-init/10_roles_prueba.sh').Replace('\', '/')
    $archivoCompose = Join-Path $tmp 'docker-compose.yml'
    $compose = @(
        'services:',
        '  db-test:',
        '    image: postgres:18.6-trixie',
        '    profiles: ["test"]',
        '    environment:',
        '      POSTGRES_USER: app',
        '      POSTGRES_PASSWORD: ${TURNOS_DB_TEST_PASSWORD}',
        '      POSTGRES_DB: turnos_test',
        '      TURNOS_APP_TEST_PASSWORD: ""',
        '      TURNOS_LOGIN_TEST_PASSWORD: ""',
        '    tmpfs:',
        '      - /var/lib/postgresql',
        '    volumes:',
        '      - type: bind',
        ('        source: "' + $script + '"'),
        '        target: /docker-entrypoint-initdb.d/10_roles_prueba.sh',
        '        read_only: true',
        '    healthcheck:',
        '      test: ["CMD-SHELL", "pg_isready -U app -d turnos_test"]',
        '      interval: 2s',
        '      timeout: 5s',
        '      retries: 15'
    )
    [System.IO.File]::WriteAllText($archivoCompose, (($compose -join "`n") + "`n"), (New-Object System.Text.ASCIIEncoding))
    $previoDbTest = [Environment]::GetEnvironmentVariable('TURNOS_DB_TEST_PASSWORD', 'Process')
    try {
        # RT3-06: superusuario con contrasena efimera; lo que falta son las de los roles.
        $env:TURNOS_DB_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
        docker compose -p $nombreProyecto -f $archivoCompose --profile test up -d --wait db-test | Out-Null
        Assert-Verdadero ($LASTEXITCODE -ne 0) 'db-test arranco sin las contrasenas de los roles'
        $enEjecucion = @(docker compose -p $nombreProyecto -f $archivoCompose --profile test ps --status running -q)
        Assert-Verdadero ($enEjecucion.Count -eq 0) 'db-test quedo en ejecucion sin las contrasenas de los roles'
    } finally {
        [Environment]::SetEnvironmentVariable('TURNOS_DB_TEST_PASSWORD', $previoDbTest, 'Process')
        docker compose -p $nombreProyecto -f $archivoCompose --profile test down --remove-orphans | Out-Null
        Remove-Item -Recurse -Force $tmp
    }
}

Invoke-Caso 'Compose monta solo .env.example de solo lectura en api' {
    $compose = Get-ConfiguracionCompose
    $montajes = @($compose.services.api.volumes | Where-Object { $_.target -eq '/repo/.env.example' })
    Assert-Verdadero ($montajes.Count -eq 1) 'api no monta /repo/.env.example'
    Assert-Verdadero ($montajes[0].read_only -eq $true) 'el montaje de .env.example no es de solo lectura'
    Assert-Verdadero ($montajes[0].source -like '*.env.example') 'el origen del montaje no es .env.example'
    foreach ($servicio in $compose.services.PSObject.Properties) {
        $volumenes = @()
        if ($servicio.Value.PSObject.Properties.Name -contains 'volumes') { $volumenes = @($servicio.Value.volumes) }
        $envMontado = @($volumenes | Where-Object { $_.PSObject.Properties.Name -contains 'source' -and ($_.source -like '*.env' -or $_.target -like '*/.env') })
        Assert-Verdadero ($envMontado.Count -eq 0) ('el servicio ' + $servicio.Name + ' monta .env')
    }
}

Invoke-Caso 'Scripts en ASCII y sin redireccion de stderr de comandos nativos' {
    $redireccion = '2>' + '&1'
    foreach ($archivo in @(Get-ChildItem -Path (Join-Path $Raiz 'scripts') -Recurse -Filter *.ps1)) {
        $bytes = [System.IO.File]::ReadAllBytes($archivo.FullName)
        $noAscii = @($bytes | Where-Object { $_ -gt 127 })
        Assert-Verdadero ($noAscii.Count -eq 0) ($archivo.Name + ' contiene caracteres no ASCII')
        $texto = [System.Text.Encoding]::ASCII.GetString($bytes)
        Assert-Verdadero (-not $texto.Contains($redireccion)) ($archivo.Name + ' redirige stderr')
    }
}

Invoke-Caso 'Funciona sin clave en .env (entorno aislado, db-test propia, sin tocar .env ni desarrollo)' {
    # Escenario: DADO un .env sin AUTH_SECRET_KEY, las migraciones sobre db-test y las pruebas de
    # integracion reciben la clave efimera y no fallan por su ausencia. Se prueba en un proyecto de
    # Compose AISLADO (nombre propio, archivo env ficticio sin la clave, su propia db-test en tmpfs):
    # no se lee ni modifica el .env real, no se toca el Compose de desarrollo ni sus servicios o datos.
    $nombreProyecto = 'autoprueba-sinclave'
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ($nombreProyecto + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $backend = (Join-Path $Raiz 'backend').Replace('\', '/')
    $scriptRoles = (Join-Path $Raiz 'db/test-init/10_roles_prueba.sh').Replace('\', '/')
    $archivoEnv = Join-Path $tmp 'entorno-sin-clave.env'
    $archivoCompose = Join-Path $tmp 'docker-compose.yml'
    $envFicticio = @(
        'DATABASE_URL=postgresql+psycopg://dev_ficticio:dev_ficticio@host-dev-ficticio.invalid:5432/turnos_dev_ficticio',
        'CORS_ALLOWED_ORIGINS=http://localhost:5173',
        'APP_ENV=test'
    )
    [System.IO.File]::WriteAllText($archivoEnv, (($envFicticio -join "`n") + "`n"), (New-Object System.Text.ASCIIEncoding))
    Assert-Verdadero (-not (Get-Content -LiteralPath $archivoEnv -Raw).Contains('AUTH_SECRET_KEY')) 'el env aislado contiene AUTH_SECRET_KEY'
    $compose = @(
        'services:',
        '  db-test:',
        '    image: postgres:18.6-trixie',
        '    profiles: ["test"]',
        '    environment:',
        '      POSTGRES_USER: app',
        '      POSTGRES_PASSWORD: ${TURNOS_DB_TEST_PASSWORD}',
        '      POSTGRES_DB: turnos_test',
        '      TURNOS_APP_TEST_PASSWORD: ${TURNOS_APP_TEST_PASSWORD}',
        '      TURNOS_LOGIN_TEST_PASSWORD: ${TURNOS_LOGIN_TEST_PASSWORD}',
        '    tmpfs:',
        '      - /var/lib/postgresql',
        '    volumes:',
        '      - type: bind',
        ('        source: "' + $scriptRoles + '"'),
        '        target: /docker-entrypoint-initdb.d/10_roles_prueba.sh',
        '        read_only: true',
        '    healthcheck:',
        '      test: ["CMD-SHELL", "pg_isready -U app -d turnos_test"]',
        '      interval: 2s',
        '      timeout: 5s',
        '      retries: 30',
        '  api:',
        '    build:',
        ('      context: "' + $backend + '"'),
        '    env_file: ./entorno-sin-clave.env',
        '    volumes:',
        '      - type: bind',
        ('        source: "' + $backend + '"'),
        '        target: /app',
        '        read_only: true'
    )
    [System.IO.File]::WriteAllText($archivoCompose, (($compose -join "`n") + "`n"), (New-Object System.Text.ASCIIEncoding))
    $valorPrevio = $env:AUTH_SECRET_KEY
    $previoApp = $env:TURNOS_APP_TEST_PASSWORD
    $previoLogin = $env:TURNOS_LOGIN_TEST_PASSWORD
    $previoDbTest = $env:TURNOS_DB_TEST_PASSWORD
    $previaUrl = $env:TEST_DATABASE_URL
    try {
        # RT3-06: como test.ps1, contrasena efimera de db-test y URL de pruebas solo en este proceso.
        $env:TURNOS_DB_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
        $env:TEST_DATABASE_URL = New-UrlBaseDePruebas -Contrasena $env:TURNOS_DB_TEST_PASSWORD
        Remove-Item Env:AUTH_SECRET_KEY -ErrorAction SilentlyContinue
        $env:TURNOS_APP_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
        $env:TURNOS_LOGIN_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
        docker compose -p $nombreProyecto -f $archivoCompose --profile test up -d --wait db-test | Out-Null
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'no se pudo levantar la db-test aislada'

        # Precondicion: sin la clave efimera (solo con el env aislado) la migracion SI falla por su ausencia.
        cmd /c ('docker compose -p ' + $nombreProyecto + ' -f "' + $archivoCompose + '" run --rm --no-deps -e TEST_DATABASE_URL api alembic -x target=test upgrade head >nul 2>nul')
        Assert-Verdadero ($LASTEXITCODE -ne 0) 'la migracion no fallo sin la clave: el env aislado no representa un .env sin AUTH_SECRET_KEY'

        # Como test.ps1: clave efimera solo en el entorno del proceso, pasada por NOMBRE.
        $env:AUTH_SECRET_KEY = New-ClaveAuthEfimera
        docker compose -p $nombreProyecto -f $archivoCompose run --rm --no-deps -e AUTH_SECRET_KEY -e TEST_DATABASE_URL api alembic -x target=test upgrade head | Out-Null
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'las migraciones sobre db-test fallaron con la clave efimera y un env sin clave'
        docker compose -p $nombreProyecto -f $archivoCompose run --rm --no-deps -e AUTH_SECRET_KEY -e TEST_DATABASE_URL api python -m pytest -p no:cacheprovider -q tests/integration/test_api_auth.py::test_login_exitoso_responde_200_emite_la_cookie_y_crea_una_sesion tests/integration/test_servicio_auth.py | Out-Null
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'las pruebas de integracion fallaron con la clave efimera y un env sin clave'
    } finally {
        if ($null -ne $valorPrevio) { $env:AUTH_SECRET_KEY = $valorPrevio } else { Remove-Item Env:AUTH_SECRET_KEY -ErrorAction SilentlyContinue }
        if ($null -ne $previoApp) { $env:TURNOS_APP_TEST_PASSWORD = $previoApp } else { Remove-Item Env:TURNOS_APP_TEST_PASSWORD -ErrorAction SilentlyContinue }
        if ($null -ne $previoLogin) { $env:TURNOS_LOGIN_TEST_PASSWORD = $previoLogin } else { Remove-Item Env:TURNOS_LOGIN_TEST_PASSWORD -ErrorAction SilentlyContinue }
        if ($null -ne $previoDbTest) { $env:TURNOS_DB_TEST_PASSWORD = $previoDbTest } else { Remove-Item Env:TURNOS_DB_TEST_PASSWORD -ErrorAction SilentlyContinue }
        if ($null -ne $previaUrl) { $env:TEST_DATABASE_URL = $previaUrl } else { Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue }
        # Solo el proyecto aislado (nombre propio, sin volumenes con nombre): nunca el de desarrollo.
        docker compose -p $nombreProyecto -f $archivoCompose --profile test down --remove-orphans | Out-Null
        Remove-Item -Recurse -Force $tmp
    }
}

if ($script:Fallos.Count -gt 0) {
    Write-Host ("Autoprueba: fallaron " + $script:Fallos.Count + " caso(s)")
    exit 1
}
Write-Host 'Autoprueba: todos los casos pasan'
exit 0
