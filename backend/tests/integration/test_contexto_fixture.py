"""El evento de contexto funciona con el modo `create_savepoint` de las fixtures (4.2, DD-05).

La fixture conecta como `app` (superusuario) y RLS no filtra: aqui se verifica que el valor se
fija en la transaccion exterior; la verificacion con RLS efectiva esta en `tests/isolation/`.
"""

import uuid

from sqlalchemy import text

from app.core.contexto_bd import aplicar_contexto, crear_fabrica_de_sesiones
from app.repositories.contexto import ContextoConsultorio

LEER = text("SELECT current_setting('app.consultorio_id', true)")
ID_A = uuid.UUID("0199a000-0000-7000-8000-00000000000a")


def _fabrica(sesion):
    return crear_fabrica_de_sesiones(
        sesion.get_bind(), join_transaction_mode="create_savepoint"
    )


def test_el_contexto_se_fija_en_la_transaccion_exterior_con_savepoint(sesion):
    with _fabrica(sesion)() as db:
        aplicar_contexto(db, ContextoConsultorio(ID_A))

        assert db.execute(LEER).scalar_one() == str(ID_A)


def test_el_contexto_se_recupera_tras_el_commit_de_la_sesion_con_savepoint(sesion):
    with _fabrica(sesion)() as db:
        aplicar_contexto(db, ContextoConsultorio(ID_A))
        db.execute(LEER)
        db.commit()  # libera el savepoint; la transaccion exterior sigue abierta

        assert db.execute(LEER).scalar_one() == str(ID_A)


def test_una_sesion_nueva_sin_identidad_vuelve_a_cadena_vacia(sesion):
    fabrica = _fabrica(sesion)
    with fabrica() as con_identidad:
        aplicar_contexto(con_identidad, ContextoConsultorio(ID_A))
        con_identidad.execute(LEER)
        con_identidad.commit()

    with fabrica() as sin_identidad:
        assert sin_identidad.execute(LEER).scalar_one() == ""
