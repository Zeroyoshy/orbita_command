# Arquitectura segura

## Capas

- Cliente web:
  - formularios HTML;
  - validacion de apoyo en el navegador;
  - CSRF por formulario.
- Aplicacion Flask:
  - autenticacion con Flask-Login;
  - validacion de entradas con WTForms;
  - autorizacion por rol y propiedad;
  - integracion opcional con Gemini Developer API;
  - auditoria y manejo de errores.
- Base de datos SQLite:
  - acceso mediante SQLAlchemy;
  - consultas ORM parametrizadas;
  - contrasenas almacenadas como hash.

## Flujo principal

1. El usuario se registra.
2. La contraseña se hashea antes de persistirse.
3. El usuario inicia sesion.
4. La sesion se marca como permanente con expiracion.
5. El usuario crea y modifica misiones segun su rol.
6. Cada evento relevante se registra en logs.

## Principios aplicados

- Minimo privilegio: el operador solo toca sus datos.
- Defensa en profundidad: validacion, CSRF, sesion segura, cabeceras y logs.
- Segregacion de responsabilidades: rutas, modelos, plantillas y documentos separados.
