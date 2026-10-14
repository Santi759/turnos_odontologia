"""Pruebas unitarias de la validacion de superposicion de turnos (RN-AG-02, RN-AG-04).

Datos ficticios: profesionales PROF-A / PROF-B, 2026-11-02, UTC-03:00.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.superposicion_turnos import (
    MENSAJE_SUPERPOSICION,
    IntervaloDeTurno,
    IntervaloInvalidoError,
    SuperposicionError,
    validar_sin_superposicion,
)

ZONA = timezone(timedelta(hours=-3))


def _instante(hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 11, 2, hora, minuto, tzinfo=ZONA)


def test_exitoso_sin_turnos_existentes() -> None:
    candidato = IntervaloDeTurno("PROF-A", _instante(10, 0), _instante(10, 30))

    assert validar_sin_superposicion(candidato, []) is None


def test_exitoso_con_un_turno_existente_que_no_se_cruza() -> None:
    existente = IntervaloDeTurno("PROF-A", _instante(10, 0), _instante(10, 30))
    candidato = IntervaloDeTurno("PROF-A", _instante(11, 0), _instante(11, 30))

    assert validar_sin_superposicion(candidato, [existente]) is None


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        pytest.param(_instante(9, 45), _instante(10, 15), id="parcial_izquierda"),
        pytest.param(_instante(10, 15), _instante(10, 45), id="parcial_derecha"),
        pytest.param(_instante(10, 10), _instante(10, 20), id="contenido"),
        pytest.param(_instante(9, 30), _instante(10, 45), id="contenedor"),
        pytest.param(_instante(10, 0), _instante(10, 30), id="identico"),
    ],
)
def test_rechazo_por_superposicion_con_el_mismo_profesional(
    inicio: datetime, fin: datetime
) -> None:
    existente = IntervaloDeTurno("PROF-A", _instante(10, 0), _instante(10, 30))
    candidato = IntervaloDeTurno("PROF-A", inicio, fin)

    with pytest.raises(SuperposicionError) as info:
        validar_sin_superposicion(candidato, [existente])

    assert str(info.value) == MENSAJE_SUPERPOSICION
    assert str(info.value) == (
        "El horario se superpone con otro turno del mismo profesional."
    )


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        pytest.param(_instante(10, 30), _instante(11, 0), id="consecutivo_posterior"),
        pytest.param(_instante(9, 30), _instante(10, 0), id="consecutivo_anterior"),
    ],
)
def test_turnos_consecutivos_se_aceptan(inicio: datetime, fin: datetime) -> None:
    existente = IntervaloDeTurno("PROF-A", _instante(10, 0), _instante(10, 30))
    candidato = IntervaloDeTurno("PROF-A", inicio, fin)

    assert validar_sin_superposicion(candidato, [existente]) is None


def test_turnos_simultaneos_de_profesionales_distintos_se_aceptan() -> None:
    existente = IntervaloDeTurno("PROF-B", _instante(10, 0), _instante(10, 30))
    candidato = IntervaloDeTurno("PROF-A", _instante(10, 0), _instante(10, 30))

    assert validar_sin_superposicion(candidato, [existente]) is None


def test_rechazo_con_turno_de_otro_profesional_en_la_entrada() -> None:
    de_otro_profesional = IntervaloDeTurno(
        "PROF-B", _instante(10, 0), _instante(10, 30)
    )
    del_mismo_profesional = IntervaloDeTurno(
        "PROF-A", _instante(10, 0), _instante(10, 30)
    )
    candidato = IntervaloDeTurno("PROF-A", _instante(10, 15), _instante(10, 45))

    with pytest.raises(SuperposicionError):
        validar_sin_superposicion(
            candidato, [de_otro_profesional, del_mismo_profesional]
        )


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        pytest.param(_instante(10, 0), _instante(10, 0), id="duracion_cero"),
        pytest.param(
            _instante(10, 30), _instante(10, 0), id="fin_anterior_al_inicio"
        ),
    ],
)
def test_candidato_con_intervalo_no_positivo_es_invalido(
    inicio: datetime, fin: datetime
) -> None:
    candidato = IntervaloDeTurno("PROF-A", inicio, fin)

    with pytest.raises(IntervaloInvalidoError) as info:
        validar_sin_superposicion(candidato, [])

    assert not isinstance(info.value, SuperposicionError)


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        pytest.param(
            datetime(2026, 11, 2, 10, 0),
            datetime(2026, 11, 2, 10, 30),
            id="instantes_sin_zona_horaria",
        ),
        pytest.param(
            _instante(10, 0),
            datetime(2026, 11, 2, 10, 30),
            id="mezcla_con_y_sin_zona_horaria",
        ),
    ],
)
def test_candidato_sin_zona_horaria_es_invalido(
    inicio: datetime, fin: datetime
) -> None:
    candidato = IntervaloDeTurno("PROF-A", inicio, fin)

    with pytest.raises(IntervaloInvalidoError):
        validar_sin_superposicion(candidato, [])


def test_turno_existente_sin_zona_horaria_es_invalido() -> None:
    existente = IntervaloDeTurno(
        "PROF-A", datetime(2026, 11, 2, 8, 0), datetime(2026, 11, 2, 8, 30)
    )
    candidato = IntervaloDeTurno("PROF-A", _instante(11, 0), _instante(11, 30))

    with pytest.raises(IntervaloInvalidoError):
        validar_sin_superposicion(candidato, [existente])


def test_turno_existente_con_intervalo_invalido_es_invalido() -> None:
    existente = IntervaloDeTurno("PROF-A", _instante(10, 30), _instante(10, 0))
    candidato = IntervaloDeTurno("PROF-A", _instante(11, 0), _instante(11, 30))

    with pytest.raises(IntervaloInvalidoError):
        validar_sin_superposicion(candidato, [existente])


def test_turno_existente_invalido_de_otro_profesional_es_invalido() -> None:
    de_otro_profesional = IntervaloDeTurno(
        "PROF-B", _instante(10, 30), _instante(10, 0)
    )
    candidato = IntervaloDeTurno("PROF-A", _instante(11, 0), _instante(11, 30))

    with pytest.raises(IntervaloInvalidoError) as info:
        validar_sin_superposicion(candidato, [de_otro_profesional])

    assert not isinstance(info.value, SuperposicionError)


def test_candidato_invalido_tiene_precedencia_sobre_la_superposicion() -> None:
    existente = IntervaloDeTurno("PROF-A", _instante(10, 0), _instante(10, 30))
    # Invalido (fin anterior al inicio) y ademas se solaparia con el existente.
    candidato = IntervaloDeTurno("PROF-A", _instante(10, 20), _instante(10, 10))

    with pytest.raises(IntervaloInvalidoError) as info:
        validar_sin_superposicion(candidato, [existente])

    assert not isinstance(info.value, SuperposicionError)
