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
