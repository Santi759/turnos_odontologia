# Funciones del runner (ASCII, PowerShell 5.1).
# En PowerShell 5.1, $ErrorActionPreference = 'Stop' no detiene ante un codigo de
# salida distinto de cero de un comando nativo: se revisa $LASTEXITCODE a mano.

function Invoke-Paso {
    param(
        [Parameter(Mandatory = $true)][string]$Nombre,
        [Parameter(Mandatory = $true)][scriptblock]$Comando
    )
    Write-Host ("==> " + $Nombre)
    $global:LASTEXITCODE = 0
    & $Comando
    $codigo = $global:LASTEXITCODE
    if ($codigo -ne 0) {
        throw ("Paso fallido: " + $Nombre + " (codigo de salida " + $codigo + ")")
    }
}

function New-UrlBaseDePruebas {
    # RT3-06: URL de la base de pruebas efimera (db-test), armada en el proceso del runner con la
    # contrasena efimera de su superusuario. Host y base fijos: db-test y turnos_test. Sin literales
    # de contrasena; el resultado nunca se imprime ni se escribe en archivos.
    param([Parameter(Mandatory = $true)][string]$Contrasena)
    if ($Contrasena -cnotmatch '^[A-Za-z0-9_-]+$') {
        throw 'La contrasena de db-test debe ser base64url (sin caracteres que alteren la URL).'
    }
    return ('postgresql+psycopg://{0}:{1}@{2}:5432/{3}' -f 'app', $Contrasena, 'db-test', 'turnos_test')
}

function Assert-SinCredencialesDeAdministracion {
    # DD-34 (RT3-01): el runner no debe propagar credenciales de administracion de desarrollo a los
    # contenedores. Si el proceso de PowerShell las define, se detiene ANTES de cualquier paso.
    # Solo se nombran las variables; nunca se leen ni se muestran sus valores.
    $presentes = @()
    foreach ($nombre in @('DATABASE_MIGRATION_URL', 'POSTGRES_PASSWORD', 'PGPASSWORD')) {
        if (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($nombre, 'Process'))) {
            $presentes += $nombre
        }
    }
    if ($presentes.Count -gt 0) {
        throw ('El proceso de PowerShell define variables de administracion (' + ($presentes -join ', ') + '): quitarlas antes de ejecutar las pruebas.')
    }
}

function Assert-RequisitosPrevios {
    param([Parameter(Mandatory = $true)][string]$Raiz)
    if (-not (Test-Path -LiteralPath (Join-Path $Raiz '.env'))) {
        throw 'Falta el archivo .env en la raiz del repositorio: hay que copiar .env.example a .env antes de ejecutar las pruebas.'
    }
}

function New-ClaveAuthEfimera {
    # Clave efimera de pruebas: 48 bytes de un CSPRNG en base64url sin relleno (64 caracteres,
    # mismo formato que secrets.token_urlsafe(48)). Se regenera si la configuracion de la
    # aplicacion la rechazaria (menos de 20 caracteres distintos o un marcador de ejemplo).
    $marcadores = @('cambiar', 'reemplazar', 'ficticio', 'ficticia', 'example', 'ejemplo',
                    'changeme', 'secret', 'password', 'contrasena')
    $generador = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        while ($true) {
            $bytes = New-Object byte[] 48
            $generador.GetBytes($bytes)
            $clave = [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=')
            $minusculas = $clave.ToLowerInvariant()
            $contieneMarcador = $false
            foreach ($marcador in $marcadores) {
                if ($minusculas.Contains($marcador)) { $contieneMarcador = $true }
            }
            $distintos = @($clave.ToCharArray() | Select-Object -Unique).Count
            if ($distintos -ge 20 -and -not $contieneMarcador) { return $clave }
        }
    } finally {
        $generador.Dispose()
    }
}

function New-ContrasenaRolPruebaEfimera {
    # Contrasena efimera de un rol de prueba (turnos_app o turnos_login, DD-21): 32 bytes de un
    # CSPRNG en base64url sin relleno (43 caracteres). Solo vive en el entorno del proceso.
    $generador = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $bytes = New-Object byte[] 32
        $generador.GetBytes($bytes)
        return [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=')
    } finally {
        $generador.Dispose()
    }
}
