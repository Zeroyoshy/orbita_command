# Checklist contra el PDF

## Estado general

La aplicacion queda alineada con los 13 puntos del resumen del PDF, con estas notas:

- HTTPS y hardening de servidor quedan implementados a nivel aplicacion/documentacion, pero el servidor final depende del despliegue real.
- SAST/DAST quedan documentados y con pruebas automatizadas locales; el escaneo externo debe ejecutarse en el entorno del equipo.

## Mapeo

1. Requisitos de seguridad definidos:
   - `docs/SECURITY_REQUIREMENTS.md`
2. Validacion de entradas:
   - `app.py`, formularios WTForms.
3. Proteccion contra inyeccion:
   - SQLAlchemy ORM sin SQL concatenado.
4. Contraseñas con hash seguro:
   - `generate_password_hash`.
5. Autenticacion y autorizacion:
   - login, roles `ADMIN`/`OPERADOR`, propiedad de recurso.
6. Sesiones bien gestionadas:
   - expiracion, `HttpOnly`, `Secure`, `SameSite`.
7. Errores controlados:
   - handlers 400/403/404/500.
8. Logs y auditoria:
   - login, logout, registro, autorizacion y cambios de mision.
9. Dependencias actualizadas y escaneadas:
   - dependencias declaradas y guia de `pip-audit`.
10. Secretos fuera del codigo:
   - `.env`, `.env.example`, `.gitignore`.
11. Uso de HTTPS:
   - redireccion a HTTPS y arranque TLS local.
12. Pruebas de seguridad:
   - `tests/test_security.py` y `docs/SECURITY_TESTING.md`.
13. Hardening:
   - cabeceras seguras, CSP, HSTS y guia de despliegue.
