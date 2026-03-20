# Pruebas de seguridad

## Pruebas automatizadas incluidas

Comando:

```bash
./venv/bin/python -m unittest discover -s tests -v
```

Cobertura actual:

- primer usuario queda como `ADMIN`;
- hash de contraseñas;
- `dashboard` requiere autenticacion;
- un operador no puede modificar recursos ajenos;
- cabeceras de seguridad presentes;
- flujo basico del asistente IA con cliente simulado.

## SAST recomendado

```bash
./venv/bin/python -m py_compile app.py
./venv/bin/python -m pip install pip-audit
./venv/bin/pip-audit
```

## DAST recomendado

- Ejecutar la app localmente en HTTPS.
- Escanear con OWASP ZAP o Burp Suite Community.
- Validar:
  - acceso sin autenticacion;
  - intento de cambiar IDs ajenos;
  - CSRF en acciones de mision;
  - mensajes genericos ante errores.

## Pruebas manuales sugeridas

1. Intentar abrir `/dashboard` sin login.
2. Intentar borrar una mision ajena cambiando el ID.
3. Probar contraseñas debiles en registro.
4. Intentar enviar HTML en titulo o descripcion.
5. Verificar que las cookies tengan `HttpOnly`, `Secure` y `SameSite=Lax`.
