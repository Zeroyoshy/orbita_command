# Despliegue y hardening

## Recomendaciones minimas

- Ejecutar la app detras de un servidor TLS real.
- Mantener el sistema operativo actualizado.
- No ejecutar el proceso como `root`.
- Restringir puertos al frontal HTTPS.
- Rotar `SECRET_KEY` y respaldar la base de datos.
- Usar Postgres en lugar de SQLite para produccion.

## Configuracion sugerida

- `ENFORCE_HTTPS=true`
- Cookies seguras habilitadas
- Logs centralizados a stdout
- Backups programados
- Monitoreo de errores y uso

## Checks antes de publicar

1. Validar que `.env` no se suba al repositorio.
2. Ejecutar pruebas unitarias.
3. Ejecutar `pip-audit`.
4. Confirmar HTTPS extremo a extremo.
5. Revisar permisos del proceso y de la base de datos.

## Despliegue recomendado: Render

El proyecto ya esta preparado para Render con [render.yaml](/Users/zeroyoshy/Downloads/orbita_command/render.yaml).

### Variables requeridas

- `SECRET_KEY`
- `DATABASE_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `SESSION_TIMEOUT_MINUTES`
- `ENFORCE_HTTPS`
- `LOG_TO_FILE`

### Build y arranque

- Build command:
  - `pip install -r requirements.txt`
- Start command:
  - `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4`

### Base de datos

Para produccion se debe usar Postgres.

Razones:

- SQLite no es adecuada para despliegue multiinstancia.
- El filesystem de muchos hostings es efimero.
- Postgres da persistencia y mejor soporte operativo.

### Health check

La aplicacion expone la ruta:

- `/healthz`

### Notas tecnicas

- `app.py` normaliza `postgres://` a `postgresql://`.
- La app usa `ProxyFix` para trabajar correctamente detras de proxy.
- Los logs pueden enviarse a stdout con `LOG_TO_FILE=false`.
