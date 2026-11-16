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
# RT3-06: valor previo de TEST_DATABASE_URL en este proceso, para restaurarlo al terminar; el runner
# nunca lo usa: arma su propia URL de pruebas antes del primer paso.
$previaTestDatabaseUrl = $env:TEST_DATABASE_URL
$usoDbTest = $false
try {
    # DD-34: ninguna credencial de administracion en el proceso (se verifica antes de cualquier paso).
    Assert-SinCredencialesDeAdministracion
    Assert-RequisitosPrevios -Raiz $Raiz
    Set-Location -LiteralPath $Raiz
    # Clave efimera de autenticacion para las pruebas (no depende del .env del autor):
    # solo vive en el entorno de este proceso y se pasa a los contenedores por NOMBRE
    # (opcion -e con el nombre de la variable, sin valor); nunca se imprime ni se escribe en un archivo.
    $env:AUTH_SECRET_KEY = New-ClaveAuthEfimera
    # Contrasenas efimeras de los roles turnos_app y turnos_login (distintas entre si, DD-21):
    # mismo tratamiento. db-test las recibe por nombre (`environment`) y el paso de aislamiento por -e.
    $env:TURNOS_APP_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
    $env:TURNOS_LOGIN_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
    # RT3-06: contrasena efimera del superusuario de db-test y URL de pruebas armada en este proceso.
    # Se pasan por NOMBRE (db-test por interpolacion; los contenedores de prueba con -e) y se retiran
    # al terminar. El servicio api permanente nunca recibe TEST_DATABASE_URL.
    $env:TURNOS_DB_TEST_PASSWORD = New-ContrasenaRolPruebaEfimera
    $env:TEST_DATABASE_URL = New-UrlBaseDePruebas -Contrasena $env:TURNOS_DB_TEST_PASSWORD

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
        docker compose run --rm --no-deps -e AUTH_SECRET_KEY -e TEST_DATABASE_URL api alembic -x target=test upgrade head
    }
    Invoke-Paso -Nombre '5. pruebas de integracion contra PostgreSQL real (db-test)' -Comando {
        docker compose run --rm --no-deps -e AUTH_SECRET_KEY -e TEST_DATABASE_URL api python -m pytest -p no:cacheprovider tests/integration -v
    }
    Invoke-Paso -Nombre '6. pruebas de aislamiento con los roles turnos_app y turnos_login (db-test)' -Comando {
        docker compose run --rm --no-deps -e AUTH_SECRET_KEY -e TURNOS_APP_TEST_PASSWORD -e TURNOS_LOGIN_TEST_PASSWORD -e TEST_DATABASE_URL api python -m pytest -p no:cacheprovider tests/isolation -v
    }
    Invoke-Paso -Nombre '7. verificacion de tipos del frontend (tsc --noEmit)' -Comando {
        docker compose run --rm --no-deps frontend npm run typecheck
    }
    Invoke-Paso -Nombre '8. pruebas del frontend (Vitest)' -Comando {
        docker compose run --rm --no-deps frontend npm test
    }
    Write-Host 'Todas las suites pasaron.'
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message)
    $codigoSalida = 1
} finally {
    Remove-Item Env:AUTH_SECRET_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:TURNOS_APP_TEST_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:TURNOS_LOGIN_TEST_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:TURNOS_DB_TEST_PASSWORD -ErrorAction SilentlyContinue
    if ($null -ne $previaTestDatabaseUrl) { $env:TEST_DATABASE_URL = $previaTestDatabaseUrl } else { Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue }
    if ($usoDbTest) {
        # La base de pruebas es efimera (tmpfs): se elimina siempre, incluso tras un fallo.
        try { docker compose --profile test rm -sf db-test | Out-Null } catch { Write-Host 'Aviso: no se pudo eliminar db-test' }
    }
}
exit $codigoSalida
