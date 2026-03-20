# Despliegue y hardening

## Recomendaciones minimas

- Ejecutar la app detras de un servidor TLS real.
- Mantener el sistema operativo actualizado.
- No ejecutar el proceso como `root`.
- Restringir puertos al frontal HTTPS.
- Rotar `SECRET_KEY` y respaldar la base de datos.

## Configuracion sugerida

- `ENFORCE_HTTPS=true`
- Cookies seguras habilitadas
- Logs centralizados
- Backups programados
- Monitoreo de errores y uso

## Checks antes de publicar

1. Validar que `.env` no se suba al repositorio.
2. Ejecutar pruebas unitarias.
3. Ejecutar `pip-audit`.
4. Confirmar HTTPS extremo a extremo.
5. Revisar permisos del proceso y de la base de datos.
