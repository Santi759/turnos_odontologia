"""Reloj de la aplicacion (DD-03): siempre UTC con zona horaria."""

from datetime import UTC, datetime, timedelta

from app.auth.reloj import RelojSistema


def test_el_reloj_del_sistema_devuelve_un_instante_utc_con_zona():
    antes = datetime.now(UTC)

    ahora = RelojSistema().ahora()

    despues = datetime.now(UTC)
    assert ahora.tzinfo is not None and ahora.utcoffset() == timedelta(0)
    assert antes <= ahora <= despues
