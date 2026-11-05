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
                    'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'VITE_API_BASE_URL')
    foreach ($nombre in $requeridas) {
        Assert-Verdadero ($valores.ContainsKey($nombre)) ('falta la variable ' + $nombre)
    }
    Assert-Verdadero ($valores['POSTGRES_PASSWORD'] -eq 'app') 'POSTGRES_PASSWORD no es el valor ficticio app'
    Assert-Verdadero ($valores['TEST_DATABASE_URL'] -like '*@db-test:*/*_test') 'TEST_DATABASE_URL no apunta a db-test / base *_test'
    $prohibidas = @($valores.Keys | Where-Object { $_ -like 'AUTH_*' -or $_ -like 'EMAIL_*' })
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

if ($script:Fallos.Count -gt 0) {
    Write-Host ("Autoprueba: fallaron " + $script:Fallos.Count + " caso(s)")
    exit 1
}
Write-Host 'Autoprueba: todos los casos pasan'
exit 0
