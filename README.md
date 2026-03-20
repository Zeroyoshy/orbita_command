# ORBITA COMMAND

Aplicacion web Flask para gestionar misiones con controles basicos de seguridad, auditoria y documentacion alineada al PDF de clase.

## Requisitos

- Python 3.13 o compatible
- Entorno virtual con dependencias instaladas

## Configuracion

1. Copia `.env.example` a `.env`.
2. Define un `SECRET_KEY` largo y aleatorio.
3. Ajusta `DATABASE_URL` si no quieres usar SQLite local.

Variables soportadas:

- `SECRET_KEY`: secreto para sesiones y CSRF.
- `DATABASE_URL`: cadena de conexion de SQLAlchemy.
- `SESSION_TIMEOUT_MINUTES`: expiracion de sesion por inactividad.
- `ENFORCE_HTTPS`: `true` o `false`.
- `GEMINI_API_KEY`: clave para activar el asistente IA.
- `GEMINI_MODEL`: modelo de Gemini a usar.

## Ejecucion

```bash
./venv/bin/python app.py
```

La app arranca con TLS local (`ssl_context='adhoc'`). Abre la URL `https://127.0.0.1:5000`.

## Pruebas

```bash
./venv/bin/python -m unittest discover -s tests -v
```

## Asistente IA

1. Instala la nueva dependencia:
```bash
./venv/bin/pip install -r requirements.txt
```
2. Agrega tu `GEMINI_API_KEY` en `.env`.
3. Reinicia la aplicacion.
4. En el dashboard aparecera el panel `ASISTENTE IA`.

El asistente puede resumir una mision, sugerir riesgos, proponer pasos siguientes y detectar informacion faltante.

## Controles de seguridad implementados

- Contraseñas con hash seguro mediante Werkzeug.
- Politica de contraseñas robusta.
- Validacion backend con WTForms.
- Roles basicos: `ADMIN` y `OPERADOR`.
- Autorizacion por rol y propietario.
- Acciones criticas por `POST` con CSRF.
- Sesiones con `HttpOnly`, `Secure`, `SameSite` y expiracion.
- Cabeceras seguras (`CSP`, `HSTS`, `X-Frame-Options`, `nosniff`).
- Logs de auditoria para login, logout, registro y cambios de misiones.
- Errores controlados 400, 403, 404 y 500.

## Documentacion

- [docs/SECURITY_REQUIREMENTS.md](/Users/zeroyoshy/Downloads/orbita_command/docs/SECURITY_REQUIREMENTS.md)
- [docs/ARCHITECTURE.md](/Users/zeroyoshy/Downloads/orbita_command/docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](/Users/zeroyoshy/Downloads/orbita_command/docs/DEPLOYMENT.md)
- [docs/SECURITY_TESTING.md](/Users/zeroyoshy/Downloads/orbita_command/docs/SECURITY_TESTING.md)
- [docs/PDF_CHECKLIST.md](/Users/zeroyoshy/Downloads/orbita_command/docs/PDF_CHECKLIST.md)
