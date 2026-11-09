"""Casos de uso de autenticacion: iniciar sesion, resolver identidad y cerrar sesion (DD-01)."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth import acceso_previo, intentos
from app.auth.claves import clave_de_cuenta, clave_de_ip, generar_token, hmac_de_token, token_valido
from app.auth.concurrencia import LimitadorArgon2
from app.auth.contrasenas import VerificadorContrasenas
from app.auth.reloj import Reloj
from app.core.config import Settings
from app.models.usuario import normalizar_email


class LoginRechazado(Exception):
    """Credenciales que no autentican (401 generico): no revela cual dato fallo."""


class LoginBloqueado(Exception):
    """Bloqueo vigente por cuenta o por IP (429)."""

    def __init__(self, retry_after: int) -> None:
        super().__init__("bloqueado")
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class ConfigAuth:
    clave_hmac: bytes
    minutos_inactividad: int
    horas_maximas: int

    @classmethod
    def desde_settings(cls, settings: Settings) -> "ConfigAuth":
        return cls(
            clave_hmac=settings.auth_hmac_key,
            minutos_inactividad=settings.auth_session_minutes,
            horas_maximas=settings.auth_session_max_hours,
        )


@dataclass(frozen=True, slots=True)
class SesionIniciada:
    token: str
    sesion_id: uuid.UUID
    nombre: str
    email: str
    rol: str
    consultorio_nombre: str


@dataclass(frozen=True, slots=True)
class Identidad:
    """Datos de una sesion valida; el contexto de consultorio NO se construye aqui (DD-01)."""

    sesion_id: uuid.UUID
    usuario_id: uuid.UUID
    consultorio_id: uuid.UUID
    nombre: str
    email: str
    rol: str
    consultorio_nombre: str


class ServicioAuth:
    def __init__(
        self,
        config: ConfigAuth,
        reloj: Reloj,
        verificador: VerificadorContrasenas,
        limitador: LimitadorArgon2,
    ) -> None:
        self.config = config
        self.reloj = reloj
        self.verificador = verificador
        self.limitador = limitador

    def iniciar_sesion(
        self,
        db: Session,
        *,
        codigo: str,
        email: str,
        contrasena: str,
        ip_normalizada: str,
        token_entrante: str | None = None,
    ) -> SesionIniciada:
        codigo_n = codigo.strip().lower()
        email_n = normalizar_email(email)
        clave = self.config.clave_hmac
        clave_c = clave_de_cuenta(clave, codigo_n, email_n)
        clave_i = clave_de_ip(clave, ip_normalizada)
        ahora = self.reloj.ahora()
        try:
            intentos.tomar_locks(db, clave_c, clave_i)
            retry_after = intentos.bloqueo_vigente(db, clave_c, clave_i, ahora)
            if retry_after is not None:
                db.commit()  # sin escrituras: el bloqueo no se registra ni se prolonga
                raise LoginBloqueado(retry_after)
            cuenta = acceso_previo.buscar_cuenta(db, codigo_n, email_n)
            autenticada, rehash = self._verificar(cuenta, contrasena)
            if cuenta is None or not autenticada:
                acceso_previo.registrar_fallo(db, clave_c, clave_i, ahora)
                acceso_previo.limpiar_intentos(db, ahora)
                db.commit()
                raise LoginRechazado
            if rehash is not None:
                acceso_previo.escribir_credencial(
                    db, cuenta.consultorio_id, cuenta.usuario_id, rehash, cuenta.credencial
                )
            # La limpieza va ANTES de revocar la sesion entrante: asi esa sesion queda
            # revocada y visible tras este login, y se borra en uno posterior.
            acceso_previo.limpiar_sesiones(db, ahora, self.config.minutos_inactividad)
            self._revocar_sesion_entrante(db, token_entrante, ahora)
            acceso_previo.descartar_fallos_de_cuenta(db, clave_c)  # reinicia la cuenta, no la IP
            acceso_previo.limpiar_intentos(db, ahora)
            token, sesion_id = self._crear_sesion(db, cuenta, ahora)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        return SesionIniciada(
            token=token,
            sesion_id=sesion_id,
            nombre=cuenta.nombre,
            email=cuenta.email,
            rol=cuenta.rol,
            consultorio_nombre=cuenta.consultorio_nombre,
        )

    def _verificar(
        self, cuenta: acceso_previo.Cuenta | None, contrasena: str
    ) -> tuple[bool, str | None]:
        """Una sola verificacion Argon2 (real o ficticia) bajo un cupo (DD-29, PC-02).

        Devuelve si autentica y, si corresponde, el hash nuevo por cambio de parametros. El
        cupo cubre tambien el rehash eventual.
        """
        credencial = cuenta.credencial if cuenta is not None else None
        with self.limitador.cupo():
            correcta = self.verificador.verificar(contrasena, credencial)
            autenticada = (
                correcta
                and cuenta is not None
                and cuenta.usuario_activo
                and cuenta.consultorio_activo
            )
            rehash = (
                self.verificador.hashear(contrasena)
                if autenticada and self.verificador.necesita_rehash(credencial)
                else None
            )
        return autenticada, rehash

    def _crear_sesion(
        self, db: Session, cuenta: acceso_previo.Cuenta, ahora: datetime
    ) -> tuple[str, uuid.UUID]:
        token = generar_token()
        vence = ahora + timedelta(hours=self.config.horas_maximas)
        sesion_id = acceso_previo.crear_sesion(
            db,
            cuenta.consultorio_id,
            cuenta.usuario_id,
            hmac_de_token(self.config.clave_hmac, token),
            ahora,
            vence,
        )
        return token, sesion_id

    def _es_valida(self, sesion: acceso_previo.SesionResuelta, ahora: datetime) -> bool:
        """Sesion valida (DD-04): sin revocar, antes del absoluto y de la inactividad vigente."""
        inactividad = timedelta(minutes=self.config.minutos_inactividad)
        return (
            sesion.revocada_en is None
            and ahora < sesion.vence_absoluto_en
            and ahora < sesion.ultimo_uso_en + inactividad
            and sesion.usuario_activo
            and sesion.consultorio_activo
        )

    def _resolver(self, db: Session, token: object) -> acceso_previo.SesionResuelta | None:
        if not token_valido(token):
            return None
        assert isinstance(token, str)
        return acceso_previo.resolver_sesion(db, hmac_de_token(self.config.clave_hmac, token))

    def _revocar_sesion_entrante(self, db: Session, token: str | None, ahora: datetime) -> None:
        """DD-06: un login exitoso revoca la sesion valida que acompana la peticion."""
        entrante = self._resolver(db, token)
        if entrante is not None and self._es_valida(entrante, ahora):
            acceso_previo.revocar_sesion(db, entrante.sesion_id, ahora)

    def resolver_identidad(self, db: Session, token: object) -> Identidad | None:
        ahora = self.reloj.ahora()
        try:
            sesion = self._resolver(db, token)
            if sesion is None or not self._es_valida(sesion, ahora):
                return None
            acceso_previo.renovar_sesion(db, sesion.sesion_id, ahora)
        finally:
            db.commit()
        return Identidad(
            sesion_id=sesion.sesion_id,
            usuario_id=sesion.usuario_id,
            consultorio_id=sesion.consultorio_id,
            nombre=sesion.nombre,
            email=sesion.email,
            rol=sesion.rol,
            consultorio_nombre=sesion.consultorio_nombre,
        )

    def cerrar_sesion(self, db: Session, sesion_id: uuid.UUID) -> bool:
        try:
            return acceso_previo.revocar_sesion(db, sesion_id, self.reloj.ahora())
        finally:
            db.commit()
