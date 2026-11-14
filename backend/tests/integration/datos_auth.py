"""Datos ficticios compartidos por las pruebas de autenticacion con base (D1).

Todo se inserta dentro de la transaccion revertible de la fixture `sesion`
(o con conexiones propias que limpian lo que crean). Nunca datos reales.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher, Type
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.claves import normalizar_ip
from app.auth.concurrencia import LimitadorArgon2
from app.auth.contrasenas import VerificadorContrasenas, normalizar_contrasena
from app.auth.servicio import ConfigAuth, ServicioAuth

# Clave HMAC ficticia generada al ejecutar (nunca un literal).
CLAVE_HMAC = secrets.token_bytes(48)
AHORA = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)
EMAIL = "persona.ficticia@example.test"


def crear_consultorio(
    sesion: Session, codigo: str, nombre: str = "Consultorio Ficticio", activo: bool = True
) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO consultorio (nombre, codigo, activo) VALUES (:nombre, :codigo, :activo) "
            "RETURNING id"
        ),
        {"nombre": nombre, "codigo": codigo, "activo": activo},
    ).scalar_one()


def crear_usuario(
    sesion: Session,
    consultorio_id: uuid.UUID,
    email: str = EMAIL,
    nombre: str = "Persona Ficticia",
    rol: str = "secretaria",
    credencial: str | None = None,
    activo: bool = True,
) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol, credencial, activo) "
            "VALUES (:c, :email, :nombre, :rol, :credencial, :activo) RETURNING id"
        ),
        {
            "c": consultorio_id,
            "email": email,
            "nombre": nombre,
            "rol": rol,
            "credencial": credencial,
            "activo": activo,
        },
    ).scalar_one()


def insertar_sesion(
    sesion: Session,
    consultorio_id: uuid.UUID,
    usuario_id: uuid.UUID,
    *,
    creada_en: datetime = AHORA,
    ultimo_uso_en: datetime | None = None,
    vence_absoluto_en: datetime | None = None,
    revocada_en: datetime | None = None,
    token_hmac: bytes | None = None,
) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
            "ultimo_uso_en, vence_absoluto_en, revocada_en) "
            "VALUES (:c, :u, :h, :creada, :uso, :vence, :rev) RETURNING id"
        ),
        {
            "c": consultorio_id,
            "u": usuario_id,
            "h": token_hmac if token_hmac is not None else secrets.token_bytes(32),
            "creada": creada_en,
            "uso": ultimo_uso_en or creada_en,
            "vence": vence_absoluto_en or creada_en + timedelta(hours=12),
            "rev": revocada_en,
        },
    ).scalar_one()


def insertar_fallo(
    sesion: Session,
    clave_cuenta: bytes,
    clave_ip: bytes,
    ocurrido_en: datetime,
    descartado: bool = False,
) -> None:
    sesion.execute(
        text(
            "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en, descartado_para_cuenta) "
            "VALUES (:cc, :ci, :t, :d)"
        ),
        {"cc": clave_cuenta, "ci": clave_ip, "t": ocurrido_en, "d": descartado},
    )


# --- reloj, verificador rapido y servicio ---------------------------------------------------

class RelojFijo:
    """Reloj inyectable que solo avanza cuando la prueba lo indica."""

    def __init__(self, ahora: datetime = AHORA) -> None:
        self._ahora = ahora

    def ahora(self) -> datetime:
        return self._ahora

    def avanzar(self, delta: timedelta) -> None:
        self._ahora += delta


def hasher_rapido(time_cost: int = 2) -> PasswordHasher:
    """Argon2id con costo minimo para pruebas con base (el costo real se prueba aparte)."""
    return PasswordHasher(
        time_cost=time_cost, memory_cost=1024, parallelism=2, hash_len=32, salt_len=16, type=Type.ID
    )


class VerificadorEspia(VerificadorContrasenas):
    """Cuenta cuantas veces se ejecuta la verificacion (Argon2)."""

    def __init__(self) -> None:
        super().__init__(hasher_rapido())
        self.llamadas = 0

    def verificar(self, contrasena: str, almacenado: str | None) -> bool:
        self.llamadas += 1
        return super().verificar(contrasena, almacenado)


def hash_rapido(contrasena: str, time_cost: int = 2) -> str:
    return hasher_rapido(time_cost).hash(normalizar_contrasena(contrasena))


CONTRASENA_A = "contrasena-ficticia-a1"
CONTRASENA_B = "contrasena-ficticia-b1"
IP = normalizar_ip("203.0.113.7")


class Entorno:
    """Dos consultorios ficticios con el mismo email y un servicio con reloj y verificador espia."""

    def __init__(self, sesion: Session, **opciones) -> None:
        self.db = sesion
        self.reloj = RelojFijo()
        self.verificador = VerificadorEspia()
        self.limitador = LimitadorArgon2(espera_segundos=opciones.pop("espera", 0.2))
        self.config = ConfigAuth(
            clave_hmac=CLAVE_HMAC,
            minutos_inactividad=opciones.pop("minutos", 30),
            horas_maximas=opciones.pop("horas", 12),
        )
        self.servicio = ServicioAuth(self.config, self.reloj, self.verificador, self.limitador)
        self.a = crear_consultorio(sesion, "ficticio-a", "Consultorio Ficticio A")
        self.b = crear_consultorio(sesion, "ficticio-b", "Consultorio Ficticio B")
        self.ua = crear_usuario(
            sesion, self.a, nombre="Persona A", credencial=hash_rapido(CONTRASENA_A)
        )
        self.ub = crear_usuario(
            sesion, self.b, nombre="Persona B", credencial=hash_rapido(CONTRASENA_B)
        )
        sesion.commit()

    def login(self, codigo="ficticio-a", email=EMAIL, contrasena=CONTRASENA_A, ip=IP, token=None):
        return self.servicio.iniciar_sesion(
            self.db,
            self.db,
            codigo=codigo,
            email=email,
            contrasena=contrasena,
            ip_normalizada=ip,
            token_entrante=token,
        )

    def sesiones(self):
        return self.db.execute(text("SELECT * FROM sesion ORDER BY creada_en, id")).all()

    def intentos(self) -> int:
        return self.db.execute(text("SELECT count(*) FROM intento_login")).scalar_one()
