# ORBITA COMMAND

## Memoria tecnica del proyecto

Fecha de elaboracion: 2026-03-20

## 1. Resumen ejecutivo

ORBITA COMMAND es una aplicacion web desarrollada con Flask para la gestion de misiones operativas. El sistema permite registrar usuarios, autenticar operadores, crear y administrar misiones, controlar su prioridad y estado, mantener bitacoras de auditoria y consultar un asistente de inteligencia artificial integrado con Gemini.

El proyecto fue evolucionado para cubrir dos objetivos al mismo tiempo:

- servir como una herramienta funcional de organizacion operativa;
- demostrar la aplicacion de practicas de seguridad solicitadas en la actividad academica.

El resultado es un sistema pequeno pero completo, con enfoque en autenticacion, autorizacion, validacion backend, proteccion de sesiones, control de errores, separacion de responsabilidades y documentacion de soporte.

## 2. Objetivo del sistema

El objetivo principal de ORBITA COMMAND es centralizar la administracion de tareas tipo mision dentro de una interfaz web clara, segura y facil de demostrar. Cada mision puede capturar:

- titulo;
- descripcion;
- prioridad;
- estado operativo;
- usuario responsable.

Adicionalmente, el sistema incorpora un asistente IA para apoyar al operador en tareas de analisis como:

- resumen de una mision;
- deteccion de riesgos;
- sugerencia de pasos siguientes;
- identificacion de informacion faltante.

## 3. Alcance funcional

La version actual del proyecto incluye las siguientes funciones:

- registro de usuarios;
- inicio y cierre de sesion;
- roles basicos `ADMIN` y `OPERADOR`;
- creacion de misiones;
- cambio de estado de misiones;
- eliminacion de misiones;
- visualizacion consolidada de operaciones;
- consulta contextual al asistente Gemini;
- registro de eventos importantes en archivo de log.

## 4. Arquitectura general

La arquitectura del sistema esta organizada en tres capas principales.

### 4.1 Capa de presentacion

La interfaz web esta construida con plantillas Jinja2 y estilos CSS personalizados. Esta capa contiene:

- pantallas de login y registro;
- dashboard principal;
- vista de errores controlados;
- formularios para operaciones y consultas IA.

La interfaz fue redisenada para ofrecer una presentacion mas moderna y clara, con prioridad visual en paneles, metricas, formularios y tarjetas de mision.

### 4.2 Capa de aplicacion

La logica del sistema vive en `app.py`. Esta capa gestiona:

- configuracion de Flask;
- conexion a base de datos;
- modelos de datos;
- formularios con validacion;
- rutas protegidas;
- manejo de sesiones;
- auditoria de eventos;
- integracion con Gemini.

### 4.3 Capa de persistencia

La persistencia se realiza con SQLite mediante SQLAlchemy. Esto permite:

- almacenamiento de usuarios;
- almacenamiento de misiones;
- consultas ORM;
- reduccion del riesgo de inyeccion SQL al evitar concatenacion manual de consultas.

## 5. Tecnologias utilizadas

El proyecto utiliza un stack ligero y apropiado para una aplicacion academica funcional:

- Python 3;
- Flask;
- Flask-SQLAlchemy;
- Flask-Login;
- Flask-WTF;
- WTForms;
- Werkzeug;
- python-dotenv;
- Google GenAI SDK para Gemini;
- SQLite;
- HTML, CSS y Jinja2.

## 6. Estructura del proyecto y contenido del repositorio

La organizacion del repositorio esta pensada para separar logica, vistas, estilos, pruebas y documentacion.

### 6.1 Archivos principales

- `app.py`: archivo central con configuracion, modelos, formularios, rutas, seguridad e integracion IA.
- `requirements.txt`: dependencias del proyecto.
- `.env`: variables de entorno locales y secretas.
- `.env.example`: plantilla publica de variables de entorno.
- `.gitignore`: exclusion de secretos, logs y artefactos locales.

### 6.2 Plantillas

En `Templates/` se encuentran las vistas del sistema:

- `base.html`: estructura general de la aplicacion;
- `login.html`: acceso al sistema;
- `register.html`: alta de operadores;
- `dashboard.html`: panel principal de operaciones;
- `error.html`: respuestas controladas ante errores.

### 6.3 Recursos estaticos

- `static/style.css`: estilos visuales de toda la interfaz.

### 6.4 Persistencia y auditoria

- `instance/orbita.db`: base de datos SQLite local.
- `mission_logs.log`: bitacora de eventos relevantes.

### 6.5 Pruebas y documentacion

- `tests/test_security.py`: pruebas automatizadas de seguridad y flujo principal.
- `docs/`: carpeta con documentos tecnicos y de soporte.

## 7. Modelo de datos

El sistema utiliza dos entidades principales.

### 7.1 Usuario

Representa a un operador del sistema. Sus atributos clave son:

- identificador unico;
- nombre de usuario;
- hash de contrasena;
- rol.

Los roles actuales son:

- `ADMIN`: puede ver y administrar todas las misiones;
- `OPERADOR`: solo puede trabajar con sus propios registros.

### 7.2 Mision

Representa una operacion a gestionar. Sus atributos son:

- identificador;
- titulo;
- descripcion;
- estado;
- prioridad;
- usuario responsable.

Estados contemplados:

- `PENDIENTE`;
- `EN PROGRESO`;
- `COMPLETADA`.

## 8. Flujo funcional del sistema

El flujo principal de uso es el siguiente:

1. El usuario crea una cuenta o inicia sesion.
2. El sistema valida credenciales y crea una sesion segura.
3. El operador accede al dashboard.
4. El operador crea una nueva mision.
5. La mision puede avanzar de `PENDIENTE` a `EN PROGRESO` y posteriormente a `COMPLETADA`.
6. El operador puede consultar el asistente IA usando o no una mision como contexto.
7. Cada evento importante queda registrado en logs.

## 9. Controles de seguridad implementados

La seguridad del proyecto se definio e implemento de forma transversal.

### 9.1 Validacion de entradas

Se realiza validacion backend mediante WTForms, incluyendo:

- longitud minima y maxima;
- expresiones regulares;
- rechazo de contenido HTML en entradas relevantes;
- validacion de formato de datos.

### 9.2 Manejo seguro de contraseñas

Las contrasenas no se guardan en texto plano. El sistema usa hashing con Werkzeug y aplica una politica minima de complejidad:

- 12 caracteres o mas;
- mayusculas;
- minusculas;
- numeros;
- simbolos.

### 9.3 Autenticacion y autorizacion

El sistema protege recursos mediante:

- login obligatorio para rutas sensibles;
- roles de usuario;
- control por propietario del recurso;
- acciones criticas realizadas por `POST`.

### 9.4 Sesiones y cookies

La sesion fue configurada con:

- `HttpOnly`;
- `Secure`;
- `SameSite=Lax`;
- expiracion por tiempo.

### 9.5 Manejo de errores

Se definieron respuestas controladas para:

- error 400;
- error 403;
- error 404;
- error 500.

Con esto se evita exponer detalles internos al usuario final y se conserva trazabilidad operativa.

### 9.6 Auditoria

La aplicacion registra eventos como:

- registros de usuario;
- logins exitosos y fallidos;
- cierres de sesion;
- creacion de misiones;
- actualizaciones de estado;
- fallos y aciertos del asistente IA.

## 10. Integracion con inteligencia artificial

Una caracteristica distintiva del proyecto es la integracion con Gemini.

### 10.1 Proposito

El asistente no reemplaza decisiones humanas. Su funcion es apoyar al operador con recomendaciones y resúmenes de contexto.

### 10.2 Entradas consideradas

Cuando el operador selecciona una mision, el sistema construye un contexto con:

- identificador de mision;
- titulo;
- descripcion;
- estado;
- prioridad;
- responsable.

### 10.3 Casos de uso del asistente

- resumir una mision;
- detectar riesgos y dependencias;
- sugerir siguientes pasos;
- identificar huecos de informacion.

### 10.4 Configuracion

La integracion depende de:

- `GEMINI_API_KEY`;
- `GEMINI_MODEL`.

Modelo configurado actualmente:

- `gemini-2.5-flash`.

## 11. Interfaz de usuario

La interfaz fue redisenada para presentar el sistema con un aspecto mas moderno y profesional. El dashboard incluye:

- encabezado con informacion del operador;
- resumen numerico de misiones;
- panel de creacion de misiones;
- panel del asistente IA;
- registro visual de operaciones.

El diseno busca equilibrio entre claridad operativa y apariencia de producto final, sin comprometer compatibilidad con dispositivos de escritorio y moviles.

## 12. Pruebas realizadas

### 12.1 Pruebas automatizadas

Se implementaron pruebas con `unittest` para validar:

- alta del primer usuario como administrador;
- hash correcto de contrasenas;
- proteccion de rutas autenticadas;
- bloqueo de acceso a recursos ajenos;
- presencia de cabeceras de seguridad;
- flujo basico del asistente IA con cliente simulado.

### 12.2 Pruebas manuales

Durante el desarrollo se validaron:

- registro e inicio de sesion;
- creacion de misiones;
- transicion de estados;
- uso del dashboard;
- funcionamiento del asistente Gemini;
- generacion de logs;
- carga de interfaz en HTTPS local.

## 13. Despliegue y operacion

Aunque el proyecto esta orientado a demostracion academica, incorpora practicas utiles para un despliegue mas serio:

- configuracion mediante variables de entorno;
- separacion de secretos del codigo;
- documentacion de hardening;
- uso recomendado de HTTPS extremo a extremo;
- exclusiones adecuadas en `.gitignore`.

## 14. Valor academico y tecnico del proyecto

El proyecto no solo cumple una funcion operativa basica, sino que demuestra conceptos tecnicos importantes:

- desarrollo web con Flask;
- uso de ORM;
- formularios y validacion;
- autenticacion y autorizacion;
- seguridad aplicada;
- integracion con servicios de IA;
- pruebas automatizadas;
- documentacion tecnica.

## 15. Conclusiones

ORBITA COMMAND es un proyecto compacto, pero suficientemente completo para servir como evidencia de desarrollo funcional y de buenas practicas. El sistema combina gestion de operaciones, seguridad aplicada, interfaz moderna y soporte de inteligencia artificial en una sola aplicacion.

Su contenido actual permite explicar claramente:

- que hace el sistema;
- como esta organizado;
- que tecnologias utiliza;
- que medidas de seguridad implementa;
- como se prueba;
- que valor agrega la integracion con Gemini.

En conjunto, el proyecto queda listo para presentacion, entrega y demostracion tecnica.
