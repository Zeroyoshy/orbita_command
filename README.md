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
- `LOG_TO_FILE`: escribe logs en `mission_logs.log` cuando vale `true`.
- `MFA_ISSUER`: nombre mostrado en apps TOTP.
- `PASSWORD_RESET_TOKEN_MAX_AGE`: duracion del enlace de recuperacion en segundos.
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_USE_TLS`: configuracion SMTP.
- `MAIL_SUPPRESS_SEND`: si vale `true`, no envia correos y registra el enlace en logs.

## Ejecucion

```bash
./venv/bin/python app.py
```

La app arranca con TLS local (`ssl_context='adhoc'`). Abre la URL `https://127.0.0.1:5000`.

## Pruebas

```bash
./venv/bin/python -m unittest discover -s tests -v
```

## Despliegue en Render

El proyecto ya incluye [render.yaml](/Users/zeroyoshy/Downloads/orbita_command/render.yaml), `gunicorn` y soporte para Postgres.

Flujo recomendado:

1. Sube el proyecto a GitHub.
2. Crea una base de datos Postgres en Render o Neon.
3. En Render crea un `Web Service` conectado a tu repo.
4. Configura estas variables:
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL`
   - `SESSION_TIMEOUT_MINUTES`
   - `ENFORCE_HTTPS=true`
   - `LOG_TO_FILE=false`
5. Usa como health check ` /healthz `.

Comando de arranque esperado:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
```

No uses SQLite para produccion. Para hosting real utiliza Postgres con `DATABASE_URL`.

## Asistente IA

1. Instala la nueva dependencia:
```bash
./venv/bin/pip install -r requirements.txt
```
2. Agrega tu `GEMINI_API_KEY` en `.env`.
3. Reinicia la aplicacion.
4. En el dashboard aparecera el panel `ASISTENTE IA`.

El asistente puede resumir una mision, sugerir riesgos, proponer pasos siguientes y detectar informacion faltante.

## MFA y recuperacion de clave

El proyecto incluye:

- MFA opcional con TOTP desde `/security`
- recuperacion de contrasena desde `/forgot-password`

Si no configuras SMTP pero activas `MAIL_SUPPRESS_SEND=true`, el enlace de recuperacion se deja en logs para pruebas.

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
