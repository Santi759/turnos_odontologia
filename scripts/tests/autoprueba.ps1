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
    $requeridas = @('DATABASE_URL', 'TEST_DATABASE_URL', 'CORS_ALLOWED_ORIGINS', 'APP_ENV',
                    'AUTH_SECRET_KEY', 'AUTH_SESSION_MINUTES', 'AUTH_SESSION_MAX_HOURS', 'AUTH_COOKIE_SECURE',
                    'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'VITE_API_BASE_URL')
    foreach ($nombre in $requeridas) {
        Assert-Verdadero ($valores.ContainsKey($nombre)) ('falta la variable ' + $nombre)
    }
    Assert-Verdadero ($valores['POSTGRES_PASSWORD'] -eq 'app') 'POSTGRES_PASSWORD no es el valor ficticio app'
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
    Assert-Verdadero ($volumenes.Count -eq 0) 'db-test declara volumenes (debe usar solo tmpfs)'
    Assert-Verdadero ($servicio.image -eq 'postgres:18.6-trixie') 'db-test no usa postgres:18.6-trixie'
    $dev = $compose.services.db
    $montajes = @($dev.volumes | Where-Object { $_.source -eq 'pgdata' })
    Assert-Verdadero ($montajes.Count -eq 1) 'db (desarrollo) no conserva el volumen pgdata'
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
    Assert-Verdadero ($porNombre.Count -eq 2) ('se esperaban 2 usos de -e AUTH_SECRET_KEY por nombre (alembic e integracion) y hay ' + $porNombre.Count)
    Assert-Verdadero ($texto.Contains('$env:AUTH_SECRET_KEY')) 'test.ps1 no deja la clave en el entorno del proceso'
    Assert-Verdadero ($texto -match 'Remove-Item Env:AUTH_SECRET_KEY') 'test.ps1 no retira la clave del entorno'
    Assert-Verdadero (-not ($texto -match 'Write-Host[^\r\n]*AUTH_SECRET_KEY')) 'test.ps1 muestra la clave'
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
    $archivoEnv = Join-Path $tmp 'entorno-sin-clave.env'
    $archivoCompose = Join-Path $tmp 'docker-compose.yml'
    $envFicticio = @(
        'DATABASE_URL=postgresql+psycopg://dev_ficticio:dev_ficticio@host-dev-ficticio.invalid:5432/turnos_dev_ficticio',
        'TEST_DATABASE_URL=postgresql+psycopg://app:app@db-test:5432/turnos_test',
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
        '      POSTGRES_PASSWORD: app',
        '      POSTGRES_DB: turnos_test',
        '    tmpfs:',
        '      - /var/lib/postgresql',
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
        '        target: /app'
    )
    [System.IO.File]::WriteAllText($archivoCompose, (($compose -join "`n") + "`n"), (New-Object System.Text.ASCIIEncoding))
    $valorPrevio = $env:AUTH_SECRET_KEY
    try {
        Remove-Item Env:AUTH_SECRET_KEY -ErrorAction SilentlyContinue
        docker compose -p $nombreProyecto -f $archivoCompose --profile test up -d --wait db-test | Out-Null
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'no se pudo levantar la db-test aislada'

        # Precondicion: sin la clave efimera (solo con el env aislado) la migracion SI falla por su ausencia.
        cmd /c ('docker compose -p ' + $nombreProyecto + ' -f "' + $archivoCompose + '" run --rm --no-deps api alembic -x target=test upgrade head >nul 2>nul')
        Assert-Verdadero ($LASTEXITCODE -ne 0) 'la migracion no fallo sin la clave: el env aislado no representa un .env sin AUTH_SECRET_KEY'

        # Como test.ps1: clave efimera solo en el entorno del proceso, pasada por NOMBRE.
        $env:AUTH_SECRET_KEY = New-ClaveAuthEfimera
        docker compose -p $nombreProyecto -f $archivoCompose run --rm --no-deps -e AUTH_SECRET_KEY api alembic -x target=test upgrade head | Out-Null
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'las migraciones sobre db-test fallaron con la clave efimera y un env sin clave'
        docker compose -p $nombreProyecto -f $archivoCompose run --rm --no-deps -e AUTH_SECRET_KEY api python -m pytest -p no:cacheprovider -q tests/integration/test_api_auth.py::test_login_exitoso_responde_200_emite_la_cookie_y_crea_una_sesion tests/integration/test_servicio_auth.py | Out-Null
        Assert-Verdadero ($LASTEXITCODE -eq 0) 'las pruebas de integracion fallaron con la clave efimera y un env sin clave'
    } finally {
        if ($null -ne $valorPrevio) { $env:AUTH_SECRET_KEY = $valorPrevio } else { Remove-Item Env:AUTH_SECRET_KEY -ErrorAction SilentlyContinue }
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
