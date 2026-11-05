# Comando unico de pruebas (Windows PowerShell 5.1, ASCII).
# Uso, desde la raiz del repositorio:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
# Se detiene en el primer paso que falla y termina con codigo distinto de cero.
# Las pruebas de integracion usan SOLO la base efimera db-test (perfil "test");
# nunca tocan la base de desarrollo (db) ni el volumen pgdata.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Raiz = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib/Pasos.ps1')

$codigoSalida = 0
$usoDbTest = $false
try {
    Assert-RequisitosPrevios -Raiz $Raiz
    Set-Location -LiteralPath $Raiz

    Invoke-Paso -Nombre '0. autoprueba del runner y de la higiene del repositorio' -Comando {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tests/autoprueba.ps1
    }
    Invoke-Paso -Nombre '1. construir imagenes (api, frontend)' -Comando {
        docker compose build api frontend
    }
    Invoke-Paso -Nombre '2. pruebas unitarias del backend (incluye las 19 de superposicion)' -Comando {
        docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -v
    }
    $usoDbTest = $true
    Invoke-Paso -Nombre '3. levantar la base de pruebas efimera (db-test)' -Comando {
        docker compose up -d --wait db-test
    }
    Invoke-Paso -Nombre '4. migraciones sobre la base de pruebas (alembic upgrade head)' -Comando {
        docker compose run --rm --no-deps api alembic -x target=test upgrade head
    }
    Invoke-Paso -Nombre '5. pruebas de integracion contra PostgreSQL real (db-test)' -Comando {
        docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/integration -v
    }
    Invoke-Paso -Nombre '6. verificacion de tipos del frontend (tsc --noEmit)' -Comando {
        docker compose run --rm --no-deps frontend npm run typecheck
    }
    Invoke-Paso -Nombre '7. pruebas del frontend (Vitest)' -Comando {
        docker compose run --rm --no-deps frontend npm test
    }
    Write-Host 'Todas las suites pasaron.'
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message)
    $codigoSalida = 1
} finally {
    if ($usoDbTest) {
        # La base de pruebas es efimera (tmpfs): se elimina siempre, incluso tras un fallo.
        try { docker compose --profile test rm -sf db-test | Out-Null } catch { Write-Host 'Aviso: no se pudo eliminar db-test' }
    }
}
exit $codigoSalida
