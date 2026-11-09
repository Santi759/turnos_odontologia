"""Pruebas de `app.auth.contrasenas`: hash y verificacion (tarea 3.2; DD-15, DD-16)."""

import secrets
import unicodedata

import pytest
from argon2 import PasswordHasher, Type

from app.auth.contrasenas import PREFIJO_HASH, VerificadorContrasenas, normalizar_contrasena

CONTRASENA = "una frase ficticia larga 2026"


class HasherEspia:
    """Envuelve un PasswordHasher real y registra cada verificacion."""

    def __init__(self, hasher: PasswordHasher):
        self._hasher = hasher
        self.hashes_verificados: list[str] = []

    def hash(self, contrasena: str) -> str:
        return self._hasher.hash(contrasena)

    def verify(self, hash_: str, contrasena: str) -> bool:
        self.hashes_verificados.append(hash_)
        return self._hasher.verify(hash_, contrasena)

    def check_needs_rehash(self, hash_: str) -> bool:
        return self._hasher.check_needs_rehash(hash_)


@pytest.fixture(scope="module")
def verificador() -> VerificadorContrasenas:
    return VerificadorContrasenas()


@pytest.fixture(scope="module")
def hash_valido(verificador) -> str:
    return verificador.hashear(CONTRASENA)


def test_el_hash_usa_argon2id_con_los_parametros_fijados(hash_valido):
    assert hash_valido.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert PREFIJO_HASH == "$argon2id$v=19$m=65536,t=3,p=4$"


def test_dos_hashes_de_la_misma_contrasena_difieren_por_la_sal(verificador, hash_valido):
    assert verificador.hashear(CONTRASENA) != hash_valido


def test_verificacion_correcta_e_incorrecta(verificador, hash_valido):
    assert verificador.verificar(CONTRASENA, hash_valido) is True
    assert verificador.verificar(CONTRASENA + "x", hash_valido) is False
    assert verificador.verificar("", hash_valido) is False


def test_nfkc_compartido_entre_forma_compuesta_y_descompuesta(verificador):
    compuesta = "contraseña-ficticia-éxito-2026"
    descompuesta = unicodedata.normalize("NFD", compuesta)
    assert compuesta != descompuesta
    hash_ = verificador.hashear(compuesta)

    assert verificador.verificar(descompuesta, hash_) is True
    assert verificador.verificar(compuesta, verificador.hashear(descompuesta)) is True
    assert verificador.verificar(compuesta + "!", hash_) is False


def test_normalizar_contrasena_aplica_solo_nfkc_sin_recortar_ni_cambiar_mayusculas():
    assert normalizar_contrasena("ﬁ-2026") == "fi-2026"
    assert normalizar_contrasena("  Ab C  ") == "  Ab C  "


def test_el_hash_de_la_forma_descompuesta_es_el_de_la_normalizada(verificador):
    hash_ = verificador.hashear("é-ficticia-larga-2026")

    assert verificador.verificar("é-ficticia-larga-2026", hash_)


@pytest.mark.parametrize(
    "almacenado",
    [
        "$argon2i$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$aGFzaGhhc2hoYXNoaGFzaGhhc2hoYXNoaGFzaGhhc2g",
        "texto arbitrario",
        "",
        "$argon2id$basura",
        None,
    ],
    ids=["argon2i", "texto", "vacio", "argon2id_truncado", "none"],
)
def test_formatos_no_admitidos_nunca_verifican_y_usan_el_hash_ficticio_una_vez(almacenado):
    espia = HasherEspia(PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID))
    verificador = VerificadorContrasenas(hasher=espia)
    ficticio = verificador.hash_ficticio
    espia.hashes_verificados.clear()

    assert verificador.verificar(CONTRASENA, almacenado) is False
    assert espia.hashes_verificados == [ficticio]


def test_un_hash_admitido_se_verifica_contra_si_mismo_y_no_contra_el_ficticio():
    espia = HasherEspia(PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID))
    verificador = VerificadorContrasenas(hasher=espia)
    hash_ = verificador.hashear(CONTRASENA)
    espia.hashes_verificados.clear()

    assert verificador.verificar(CONTRASENA, hash_) is True
    assert espia.hashes_verificados == [hash_]


def test_el_hash_ficticio_usa_los_mismos_parametros_y_se_calcula_una_vez(verificador):
    ficticio = verificador.hash_ficticio

    assert ficticio.startswith(PREFIJO_HASH)
    assert verificador.hash_ficticio == ficticio
    assert VerificadorContrasenas().hash_ficticio != ficticio


def test_el_hash_ficticio_no_verifica_ninguna_contrasena_conocida(verificador):
    assert verificador.verificar(CONTRASENA, None) is False
    assert verificador.verificar(secrets.token_urlsafe(16), verificador.hash_ficticio) is False


def test_necesita_rehash_verdadero_para_parametros_viejos_y_falso_para_los_vigentes(
    verificador, hash_valido
):
    viejo = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=4, type=Type.ID).hash(CONTRASENA)
    menos_memoria = PasswordHasher(time_cost=3, memory_cost=19456, parallelism=4, type=Type.ID).hash(
        CONTRASENA
    )

    assert verificador.necesita_rehash(viejo) is True
    assert verificador.necesita_rehash(menos_memoria) is True
    assert verificador.necesita_rehash(hash_valido) is False


@pytest.mark.parametrize("almacenado", [None, "", "texto", "$argon2i$v=19$m=65536,t=3,p=4$YQ$YQ"])
def test_necesita_rehash_es_falso_para_formatos_no_admitidos(verificador, almacenado):
    assert verificador.necesita_rehash(almacenado) is False


# ===========================================================================
# 3.3 Politica de contrasenas nuevas (DD-16, PD-09)
# ===========================================================================

import hashlib  # noqa: E402
import itertools  # noqa: E402
import re  # noqa: E402

from app.auth.contrasenas import (  # noqa: E402
    RUTA_RECURSOS,
    TERMINOS_FIJOS,
    ContrasenaRechazada,
    ReglaContrasena,
    forma_compacta,
    terminos_de_contexto,
    validar_contrasena_nueva,
)


def _de_longitud(n: int) -> str:
    return ("Xy9." * n)[:n]


def _regla(contrasena: str, terminos=()) -> ReglaContrasena | None:
    try:
        validar_contrasena_nueva(contrasena, terminos)
    except ContrasenaRechazada as error:
        return error.regla
    return None


@pytest.mark.parametrize(
    ("longitud", "esperada"),
    [
        (0, ReglaContrasena.LONGITUD),
        (14, ReglaContrasena.LONGITUD),
        (15, None),
        (16, None),
        (128, None),
        (129, ReglaContrasena.LONGITUD),
        (500, ReglaContrasena.LONGITUD),
    ],
)
def test_limites_de_longitud(longitud, esperada):
    assert _regla(_de_longitud(longitud)) == esperada


def test_la_longitud_se_mide_en_puntos_de_codigo_tras_nfkc():
    # 8 ligaduras + "-2026" son 13 puntos sin normalizar y 21 tras NFKC.
    assert _regla("ﬁ" * 8 + "-2026") is None
    # 64 ligaduras valen 128 tras NFKC; 65 valen 130.
    assert _regla("ﬁ" * 64) is None
    assert _regla("ﬁ" * 65) == ReglaContrasena.LONGITUD
    # 7 ligaduras = 14 tras NFKC: corta.
    assert _regla("ﬁ" * 7) == ReglaContrasena.LONGITUD
    # Un acento descompuesto cuenta como un punto tras NFKC (que compone).
    assert _regla("é" * 14) == ReglaContrasena.LONGITUD
    assert _regla("é" * 15) is None


@pytest.mark.parametrize("texto", [" " * 20, "\t" * 20, " " * 20, " \t " * 7])
def test_solo_espacios_en_blanco_se_rechaza(texto):
    assert _regla(texto) == ReglaContrasena.SOLO_ESPACIOS


def test_espacios_y_unicode_se_admiten():
    assert _regla("mi contraseña con ñ y 日本語 ok 2026") is None
    assert _regla("  espacios en los extremos 2026  ") is None
    assert _regla("emoji \U0001f600 en la frase larga 2026") is None


@pytest.mark.parametrize(
    "contrasena",
    [
        "qwertyuiopasdfgh",
        "QwertyUiopAsdfgH",
        "Qwerty-Uiop Asdfgh",
        "CONTRASEÑA123456",
        "contrasena123456",
        "Contraseña 123456",
        "contraseña123456",
    ],
)
def test_entradas_comunes_se_rechazan_aunque_cambien_mayusculas_o_separadores(contrasena):
    assert _regla(contrasena) == ReglaContrasena.COMUN


@pytest.mark.parametrize(
    "contrasena",
    ["qwertyuiopasdfgh1", "xqwertyuiopasdfgh", "qwertyuiop asdfgx", "contrasena1234567x"],
)
def test_una_variante_que_no_coincide_exactamente_con_una_entrada_se_acepta(contrasena):
    assert _regla(contrasena) is None


def test_los_mensajes_nombran_la_regla_sin_repetir_la_contrasena():
    contrasena = "qwertyuiopasdfgh"
    with pytest.raises(ContrasenaRechazada) as excinfo:
        validar_contrasena_nueva(contrasena)

    assert contrasena not in str(excinfo.value)
    assert str(excinfo.value)


def _leer_recurso(nombre: str) -> tuple[list[str], list[str]]:
    lineas = (RUTA_RECURSOS / nombre).read_text(encoding="utf-8").splitlines()
    return [x for x in lineas if x.startswith("#")], [x for x in lineas if x and not x.startswith("#")]


@pytest.mark.parametrize("nombre", ["contrasenas_comunes.txt", "terminos_genericos.txt"])
def test_cabecera_de_las_listas_documenta_fuente_licencia_criterios_y_sha256(nombre):
    cabecera, entradas = _leer_recurso(nombre)
    texto = "\n".join(cabecera)

    assert "elaboración propia del proyecto" in texto
    assert "Licencia" in texto
    assert re.search(r"[Cc]riterios", texto)
    declarado = re.search(r"# SHA-256: ([0-9a-f]{64})$", texto, re.MULTILINE)
    assert declarado is not None
    contenido = "".join(e + "\n" for e in entradas)
    assert hashlib.sha256(contenido.encode("utf-8")).hexdigest() == declarado.group(1)


def test_las_contrasenas_comunes_tienen_al_menos_15_puntos_de_codigo_y_no_se_repiten():
    _, entradas = _leer_recurso("contrasenas_comunes.txt")

    assert len(entradas) >= 30
    assert all(len(unicodedata.normalize("NFKC", e)) >= 15 for e in entradas)
    assert len({forma_compacta(e) for e in entradas}) == len(entradas)


def test_el_sha256_de_las_listas_detecta_un_cambio_de_contenido():
    _, entradas = _leer_recurso("contrasenas_comunes.txt")
    original = hashlib.sha256("".join(e + "\n" for e in entradas).encode()).hexdigest()
    alterado = hashlib.sha256("".join(e + "\n" for e in [*entradas, "extra"]).encode()).hexdigest()

    assert original != alterado


# ===========================================================================
# 3.4 Terminos del contexto deterministas (DD-16, PC-06)
# ===========================================================================


@pytest.mark.parametrize(
    ("texto", "esperada"),
    [
        ("Odontología-del Barrio", "odontologiadelbarrio"),
        ("ficticio-a", "ficticioa"),
        ("PÉRSONA", "persona"),
        ("PERSONA", "persona"),
        ("ﬁcticio", "ficticio"),
        ("Straße", "strasse"),
        ("a.b_c d", "abcd"),
        ("é", "e"),
        ("---", ""),
        ("", ""),
        ("A1-b2", "a1b2"),
    ],
)
def test_forma_compacta(texto, esperada):
    assert forma_compacta(texto) == esperada


def _terminos(**cambios) -> frozenset[str]:
    datos = {
        "codigo": "ficticio-a",
        "email": "persona.ficticia@example.test",
        "nombre_consultorio": "Consultorio Ficticio A",
        "nombre_usuario": "Persona Ficticia",
    }
    datos.update(cambios)
    return terminos_de_contexto(**datos)


FIJOS = {"turnos", "odontologia", "consultorio", "turnosodontologia"}


def test_terminos_por_origen_para_el_caso_ficticio():
    terminos = _terminos()

    assert "ficticioa" in terminos  # (a) codigo completo
    assert {"personaficticia", "persona", "ficticia"} <= terminos  # (b) parte local y tokens
    assert "ficticio" in terminos  # (d) token del nombre del consultorio
    assert FIJOS <= terminos  # (e) fijos, aunque "consultorio" figure en la lista generica
    assert not {"example", "test", "a"} & terminos  # (c) genericas fuera; tokens cortos fuera


def test_las_etiquetas_del_dominio_de_4_o_mas_caracteres_no_genericas_son_terminos():
    terminos = _terminos(email="x@clinica-norte.example.com")

    assert "clinicanorte" in terminos
    assert not {"example", "com", "clinica"} & terminos


def test_tokens_de_la_parte_local_de_4_o_mas_caracteres():
    terminos = _terminos(email="Ana.Pérez-Gómez+x@example.test")

    assert {"anaperezgomezx", "perez", "gomez"} <= terminos
    assert "ana" not in terminos and "x" not in terminos


def test_nombres_con_diacriticos_y_palabras_genericas():
    terminos = _terminos(nombre_consultorio="Clínica Centro Norte", nombre_usuario="María López")

    assert {"norte", "maria", "lopez"} <= terminos
    assert not {"clinica", "centro"} & terminos


def test_email_sin_arroba_usa_todo_como_parte_local():
    terminos = _terminos(email="persona.sola")

    assert {"personasola", "persona", "sola"} <= terminos


def test_la_contrasena_de_ejemplo_con_genericos_del_dominio_se_acepta():
    terminos = _terminos()

    assert _regla("mi example de test largo 2026", terminos) is None


@pytest.mark.parametrize(
    ("contrasena", "motivo"),
    [
        ("mi clave FICTICIO-A 2026 ok", "codigo"),
        ("Mi Persona Ficticia 2026 ok", "parte local"),
        ("la ficticia es larga 2026 ok", "token de la parte local"),
        ("clave Ficticio larga 2026 ok", "token del consultorio"),
        ("TURNOS en la nube 2026 ok", "fijo"),
        ("Odontología es larga 2026", "fijo con diacriticos"),
        ("el consultorio es largo 2026", "fijo que tambien es generico"),
        ("turnos_odontologia largo 2026", "nombre del sistema"),
    ],
)
def test_contrasenas_que_contienen_un_termino_del_contexto_se_rechazan(contrasena, motivo):
    assert _regla(contrasena, _terminos()) == ReglaContrasena.CONTEXTO, motivo


def test_un_termino_generico_del_nombre_no_rechaza_por_si_solo():
    terminos = _terminos(nombre_consultorio="Clínica Centro Norte")

    assert _regla("la clinica del centro es linda 2026", terminos) is None
    assert _regla("al norte de la ciudad 2026 ok", terminos) == ReglaContrasena.CONTEXTO


def test_el_resultado_no_depende_del_orden_de_los_terminos():
    terminos = sorted(_terminos())
    casos = ["mi clave FICTICIO-A 2026 ok", "mi example de test largo 2026", "frase completamente ajena 2026"]

    for contrasena in casos:
        permutaciones = itertools.islice(itertools.permutations(terminos[:6]), 30)
        assert len({_regla(contrasena, perm) for perm in permutaciones}) == 1
    assert _regla(casos[0], reversed(terminos)) == _regla(casos[0], terminos)


def test_la_lista_generica_esta_ordenada_sin_duplicados_y_en_forma_compacta():
    _, entradas = _leer_recurso("terminos_genericos.txt")

    assert entradas == sorted(set(entradas))
    assert all(e == forma_compacta(e) for e in entradas)
    assert {"example", "test", "invalid", "localhost", "local", "gmail", "com", "clinica"} <= set(entradas)


def test_un_termino_vacio_se_descarta_y_no_rechaza_todo():
    assert _regla("frase completamente ajena 2026", ["", "---"]) is None


def test_la_lista_generica_incluye_los_terminos_de_la_spec_y_excluye_turnos_y_odontologia():
    cabecera, entradas = _leer_recurso("terminos_genericos.txt")
    texto = "\n".join(cabecera)

    # Cabecera (escenario "Lista de terminos genericos documentada"): fuente, licencia, criterios, SHA-256.
    assert "Fuente: elaboración propia del proyecto" in texto
    assert re.search(r"Licencia: \S", texto)
    assert re.search(r"Criterios de inclusión: \S", texto)
    assert re.search(r"# SHA-256: [0-9a-f]{64}$", texto, re.MULTILINE)
    # Contenido.
    assert {"example", "test", "invalid", "localhost", "gmail", "dental"} <= set(entradas)
    assert "turnos" not in entradas
    assert "odontologia" not in entradas
    assert not {"turnosodontologia", "turnos_odontologia"} & set(entradas)
    # `turnos` y `odontologia` se rechazan igual: son terminos fijos del sistema, no de la lista.
    assert {"turnos", "odontologia"} <= TERMINOS_FIJOS
