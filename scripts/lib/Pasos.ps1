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
