# Requisitos de seguridad

## Datos manejados

- Identificadores de usuario.
- Credenciales de acceso.
- Datos operativos de misiones: titulo, descripcion, prioridad y estado.

## Sensibilidad

- `username`: dato personal interno.
- `password`: dato sensible, solo almacenado como hash.
- `Mission`: dato operativo con impacto de integridad.

## Actores

- `ADMIN`: ve y administra todas las misiones.
- `OPERADOR`: administra solo sus propias misiones.
- Usuario no autenticado: solo puede acceder a login y registro.

## Objetivos CIA

- Confidencialidad:
  - sesiones seguras;
  - contraseñas hasheadas;
  - paginas protegidas con autenticacion.
- Integridad:
  - CSRF en formularios;
  - cambios criticos solo por `POST`;
  - autorizacion por propietario o rol.
- Disponibilidad:
  - manejo controlado de errores;
  - limites de tamano de peticion;
  - bitacora para diagnostico.

## Controles minimos definidos

- Autenticacion con usuario y clave.
- Autorizacion con roles y dueños de recurso.
- Cifrado en transito con HTTPS local.
- Logs de auditoria en `mission_logs.log`.
- Errores genericos para usuario y detalle operativo en logs.
- Politica de contraseñas:
  - minimo 12 caracteres;
  - mayusculas;
  - minusculas;
  - numeros;
  - simbolos.

## Secretos

- `SECRET_KEY` se carga desde `.env`.
- `GEMINI_API_KEY` se carga desde `.env`.
- `.env.example` solo contiene placeholders.
- `.gitignore` excluye `.env`.
