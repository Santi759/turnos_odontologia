"""Funciones de login de la base, ejecutadas con el rol `turnos_login` (DD-25, DD-27, DD-28).

Cada funcion llama a una funcion `SECURITY DEFINER` del esquema `acceso` (dueno
`turnos_acceso_login`): buscar la cuenta, registrar, contar y descartar fallos y limpiar intentos.
Importable solo desde `auth/servicio.py` y `auth/intentos.py` (prueba estatica). Ninguna funcion
escribe `usuario` (R2-01, R2-03).

Los limites de conteo (5 por cuenta, 30 por IP) y de limpieza (100) viven en la base y coinciden
con `intentos.POLITICA_CUENTA`/`POLITICA_IP` (prueba de equivalencia).
"""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.cuenta import Cuenta
from app.models.usuario import normalizar_email


def buscar_cuenta(sesion: Session, codigo: str, email: str) -> Cuenta | None:
    """Cuenta por (codigo de consultorio, email), ambos normalizados (DM-03, DD-13).

    La credencial solo viene si el usuario y el consultorio estan activos y no es nula.
    """
    fila = sesion.execute(
        text("SELECT * FROM acceso.buscar_cuenta(:codigo, :email)"),
        {"codigo": codigo.strip().lower(), "email": normalizar_email(email)},
    ).one()
    if fila.o_usuario_id is None:
        return None
    return Cuenta(
        usuario_id=fila.o_usuario_id,
        consultorio_id=fila.o_consultorio_id,
        email=fila.o_email,
        nombre=fila.o_nombre,
        rol=fila.o_rol,
        credencial=fila.o_credencial,
        usuario_activo=fila.o_usuario_activo,
        consultorio_nombre=fila.o_consultorio_nombre,
        consultorio_activo=fila.o_consultorio_activo,
    )


def registrar_fallo(
    sesion: Session, clave_cuenta: bytes, clave_ip: bytes, ocurrido_en: datetime
) -> None:
    """Un fallo evaluado: solo claves HMAC y el instante (DD-11, X1)."""
    sesion.execute(
        text("SELECT acceso.registrar_fallo(:clave_cuenta, :clave_ip, :ocurrido_en)"),
        {"clave_cuenta": clave_cuenta, "clave_ip": clave_ip, "ocurrido_en": ocurrido_en},
    )


def fallos_de_cuenta(sesion: Session, clave_cuenta: bytes, desde: datetime) -> list[datetime]:
    """Hasta 5 fallos recientes del par SIN los descartados, del mas antiguo al mas reciente."""
    return list(
        sesion.execute(
            text("SELECT acceso.fallos_de_cuenta(:clave, :desde)"),
            {"clave": clave_cuenta, "desde": desde},
        ).scalar_one()
    )


def fallos_de_ip(sesion: Session, clave_ip: bytes, desde: datetime) -> list[datetime]:
    """Hasta 30 fallos recientes de la IP, TODOS (el contador de IP nunca mira la marca, DD-10)."""
    return list(
        sesion.execute(
            text("SELECT acceso.fallos_de_ip(:clave, :desde)"),
            {"clave": clave_ip, "desde": desde},
        ).scalar_one()
    )


def descartar_fallos_de_cuenta(sesion: Session, clave_cuenta: bytes) -> int:
    """Marca los fallos del par como descartados para la cuenta; no los borra (PC-04)."""
    return sesion.execute(
        text("SELECT acceso.descartar_fallos_de_cuenta(:clave)"), {"clave": clave_cuenta}
    ).scalar_one()


def limpiar_intentos(sesion: Session, ahora: datetime) -> int:
    """Borra como maximo 100 fallos de mas de 24 horas (DD-21)."""
    return sesion.execute(
        text("SELECT acceso.limpiar_intentos(:ahora)"), {"ahora": ahora}
    ).scalar_one()
