# Plantilla de ficha de competidor

Cada sistema investigado produce **dos archivos**:

1. `discovery/sources/<slug>.md` — ficha legible (para sistemas ya existentes, se **agrega** al final una sección `## Ficha ampliada (2026-10-12)` sin borrar el contenido previo).
2. `discovery/sources/fichas/<slug>.json` — ítems de puntuación que consume `docs/discovery/metodologia/puntuar.js`.

## Reglas de evidencia (obligatorias)

- Todo dato lleva **URL exacta y fecha de consulta** (AAAA-MM-DD). Nunca inventar ni reconstruir una URL: solo URLs efectivamente abiertas.
- Clasificar cada dato como:
  - `comprobado-oficial` — descripto en una página oficial del fabricante.
  - `terceros` — solo en fuente no oficial (comparador, prensa, reseña).
  - `afirmacion-comercial` — marketing sin descripción funcional verificable (porcentajes, "líder", cifras de clientes del propio fabricante).
  - `no-evidenciado` — sin respaldo público. Escribir literalmente **No evidenciado**.
- Separar funciones comprobadas de afirmaciones comerciales.
- No inferir: si la página no lo dice, es `no-evidenciado`.
- Precios: solo los publicados, con moneda, período, impuestos si se indican, URL y fecha.

## Secciones de la ficha `.md`

```markdown
# <Nombre del sistema>

- **Empresa**: <razón social o marca responsable> [estado] <URL>
- **País de origen**: <país> [estado] <URL>
- **URL oficial**: <URL>
- **Nivel de relevancia para Argentina**: 1 | 2 | 3 — <justificación con evidencia>
- **Fecha de consulta**: AAAA-MM-DD

## 1. Segmento objetivo y modalidad de implementación
## 2. Agenda y gestión de turnos
## 3. Reserva digital, confirmación, cancelación y reprogramación
## 4. Automatizaciones y recordatorios
## 5. Funcionalidades clínicas odontológicas
## 6. Administración, cobros y facturación
## 7. Integraciones (WhatsApp, Mercado Pago, ARCA y otras)
## 8. Sucursales, roles, permisos, auditoría y exportación
## 9. Seguridad y cumplimiento normativo declarado
## 10. Modelo comercial, precios y costos adicionales
## 11. Fortalezas, limitaciones y diferenciadores (interpretación del investigador, marcada como tal)
## 12. Evidencia verificable de adopción (separar fuentes independientes de cifras del fabricante)

## Fuentes
- <URL> — <tipo: sitio oficial | precios | documentación | tienda de apps | comparador | prensa> — consultada AAAA-MM-DD — <qué se verificó / limitación>
```

En cada sección, cada afirmación termina con `[estado] <URL>`. Si no hay información: `No evidenciado.`

## Niveles de relevancia para Argentina

- **1**: presencia comercial en Argentina comprobada (precio en ARS, sitio `/ar`, integración local o clientes argentinos verificables).
- **2**: Latinoamérica, en español, sin presencia argentina comprobada.
- **3**: internacional.

## Esquema del `.json`

```json
{
  "slug": "ejemplo",
  "nombre": "Ejemplo",
  "empresa": "Ejemplo S.A. | No evidenciado",
  "pais_origen": "Chile | No evidenciado",
  "url_oficial": "https://...",
  "nivel": 2,
  "nivel_justificacion": "texto breve con la evidencia",
  "fecha_consulta": "2026-10-12",
  "ficha_md": "discovery/sources/ejemplo.md",
  "items": {
    "C1.1": { "estado": "comprobado-oficial", "url": "https://...", "nota": "qué dice la fuente" },
    "C1.2": { "estado": "no-evidenciado" }
  }
}
```

`items` debe contener **los 35 ítems** `C1.1`–`C7.5` definidos en `docs/discovery/metodologia/criterios-puntuacion.md`. Todo estado distinto de `no-evidenciado` requiere `url`. Validar con:

```bash
node docs/discovery/metodologia/puntuar.js discovery/sources/fichas
```
