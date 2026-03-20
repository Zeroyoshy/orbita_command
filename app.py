import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect, FlaskForm
from sqlalchemy import func, inspect, text
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, Regexp, ValidationError

try:
    from google import genai
except ModuleNotFoundError:
    genai = None


ROLE_ADMIN = "ADMIN"
ROLE_OPERATOR = "OPERADOR"
VALID_MISSION_ACTIONS = {"start", "complete", "delete"}
PASSWORD_POLICY = (
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,128}$"
)
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def load_environment():
    load_dotenv(".env")


def configure_logging():
    logging.basicConfig(
        filename="mission_logs.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def validate_no_html(_form, field):
    if field.data and any(char in field.data for char in "<>"):
        raise ValidationError("No se permite HTML en este campo.")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_OPERATOR)
    missions = db.relationship("Mission", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN


class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), default="PENDIENTE", nullable=False)
    priority = db.Column(db.String(10), default="MEDIA", nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="missions")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    flash("Debes iniciar sesión para acceder a este recurso.", "danger")
    return redirect(url_for("login"))


class LoginForm(FlaskForm):
    username = StringField(
        "Operador",
        validators=[DataRequired(), Length(min=4, max=32)],
        filters=[lambda value: value.strip() if value else value],
    )
    password = PasswordField("Clave", validators=[DataRequired()])
    submit = SubmitField("ACCEDER SISTEMA")


class RegisterForm(FlaskForm):
    username = StringField(
        "Operador",
        validators=[
            DataRequired(),
            Length(min=4, max=32),
            Regexp(
                r"^[A-Za-z0-9_]+$",
                message="Solo se permiten letras, numeros y guion bajo.",
            ),
        ],
        filters=[lambda value: value.strip() if value else value],
    )
    password = PasswordField(
        "Clave",
        validators=[
            DataRequired(),
            Length(min=12, max=128),
            Regexp(
                PASSWORD_POLICY,
                message=(
                    "La clave debe tener 12 caracteres minimo, mayusculas, "
                    "minusculas, numeros y simbolos."
                ),
            ),
        ],
    )
    confirm = PasswordField(
        "Confirmar",
        validators=[DataRequired(), EqualTo("password", message="Las claves no coinciden.")],
    )
    submit = SubmitField("REGISTRAR CREDENCIALES")


class MissionForm(FlaskForm):
    title = StringField(
        "Objetivo",
        validators=[
            DataRequired(),
            Length(min=3, max=50),
            Regexp(
                r"^[A-Za-z0-9_\-\s\.,:]+$",
                message="Usa solo texto plano para el titulo.",
            ),
            validate_no_html,
        ],
        filters=[lambda value: value.strip() if value else value],
    )
    description = TextAreaField(
        "Detalles Tacticos",
        validators=[Optional(), Length(max=500), validate_no_html],
        filters=[lambda value: value.strip() if value else value],
    )
    priority = SelectField(
        "Nivel de Alerta",
        choices=[
            ("ALTA", "CRITICA"),
            ("MEDIA", "ESTANDAR"),
            ("BAJA", "RUTINA"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("INICIAR MISION")


class ActionForm(FlaskForm):
    submit = SubmitField("Confirmar")


class AssistantForm(FlaskForm):
    mission_id = SelectField(
        "Mision de contexto",
        choices=[],
        validators=[Optional()],
    )
    prompt = TextAreaField(
        "Pregunta para la IA",
        validators=[DataRequired(), Length(min=10, max=600), validate_no_html],
        filters=[lambda value: value.strip() if value else value],
    )
    submit = SubmitField("CONSULTAR IA")


def flash_form_errors(form):
    for field_name, errors in form.errors.items():
        field = getattr(form, field_name, None)
        label = field.label.text if field is not None else field_name
        for error in errors:
            flash(f"{label}: {error}", "danger")


def client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def log_event(level, event, **details):
    logger = logging.getLogger("orbita.security")
    serialized = " ".join(f"{key}={value}" for key, value in sorted(details.items()))
    getattr(logger, level)(f"{event} {serialized}".strip())


def can_manage_mission(user, mission):
    return user.is_authenticated and (user.is_admin or mission.user_id == user.id)


def assistant_available(app):
    has_factory = app.config.get("GEMINI_CLIENT_FACTORY") is not None
    has_sdk = genai is not None
    has_key = bool(app.config.get("GEMINI_API_KEY"))
    return has_factory or (has_sdk and has_key)


def get_gemini_client(app):
    factory = app.config.get("GEMINI_CLIENT_FACTORY")
    if factory is not None:
        return factory(app.config.get("GEMINI_API_KEY"))
    if genai is None:
        raise RuntimeError("El SDK de Gemini no esta instalado.")
    api_key = app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY.")
    return genai.Client(api_key=api_key)


def mission_choices_for_user(user):
    query = db.select(Mission).order_by(Mission.id.desc())
    if not user.is_admin:
        query = query.filter_by(user_id=user.id)
    missions = db.session.execute(query).scalars().all()
    choices = [("", "Sin contexto adicional")]
    for mission in missions:
        choices.append((str(mission.id), f"OP-{mission.id} | {mission.title}"))
    return choices, missions


def build_assistant_input(user_prompt, mission=None):
    mission_context = "Sin contexto de mision."
    if mission is not None:
        mission_context = (
            f"Mision ID: {mission.id}\n"
            f"Titulo: {mission.title}\n"
            f"Descripcion: {mission.description or 'Sin descripcion'}\n"
            f"Estado: {mission.status}\n"
            f"Prioridad: {mission.priority}\n"
            f"Responsable: {mission.user.username}\n"
        )

    return (
        "Actua como un analista de operaciones para ORBITA COMMAND. "
        "Da respuestas breves, concretas y utiles. "
        "No inventes datos faltantes; si falta contexto, dilo. "
        "No pidas ni expongas secretos, contrasenas o tokens.\n\n"
        f"Contexto:\n{mission_context}\n"
        f"Solicitud del operador:\n{user_prompt}"
    )


def extract_response_text(response):
    response_text = getattr(response, "text", "")
    if response_text:
        return response_text.strip()
    return "No se recibio texto en la respuesta del modelo."


def initialize_database():
    db.create_all()
    inspector = inspect(db.engine)
    if inspector.has_table("user"):
        user_columns = {column["name"] for column in inspector.get_columns("user")}
        if "role" not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE user "
                        "ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'OPERADOR'"
                    )
                )
                connection.execute(
                    text("UPDATE user SET role = 'OPERADOR' WHERE role IS NULL")
                )

    first_user = db.session.execute(
        db.select(User).order_by(User.id.asc())
    ).scalars().first()
    admin_exists = db.session.execute(
        db.select(User).filter_by(role=ROLE_ADMIN)
    ).scalars().first()
    if first_user and not admin_exists:
        first_user.role = ROLE_ADMIN
        db.session.commit()


def create_app(test_config=None):
    load_environment()
    configure_logging()

    secret_key = None
    if test_config:
        secret_key = test_config.get("SECRET_KEY")
    if not secret_key:
        secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "Falta SECRET_KEY. Copia .env.example a .env y define secretos fuertes."
        )

    app = Flask(__name__, template_folder="Templates", static_folder="static")
    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///orbita.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(
            minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        ),
        ENFORCE_HTTPS=os.getenv("ENFORCE_HTTPS", "true").lower() == "true",
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY"),
        GEMINI_MODEL=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        GEMINI_CLIENT_FACTORY=None,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "login"

    @app.before_request
    def enforce_security_controls():
        if current_user.is_authenticated:
            session.permanent = True
        if app.config["ENFORCE_HTTPS"] and not app.config["TESTING"]:
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            if not request.is_secure and forwarded_proto != "https":
                return redirect(request.url.replace("http://", "https://", 1), code=301)
        return None

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.errorhandler(400)
    def handle_bad_request(_error):
        return (
            render_template(
                "error.html",
                status_code=400,
                message="La solicitud no es valida o el token CSRF no coincide.",
            ),
            400,
        )

    @app.errorhandler(403)
    def handle_forbidden(_error):
        return (
            render_template(
                "error.html",
                status_code=403,
                message="No tienes permisos para acceder a este recurso.",
            ),
            403,
        )

    @app.errorhandler(404)
    def handle_not_found(_error):
        return (
            render_template(
                "error.html",
                status_code=404,
                message="El recurso solicitado no existe.",
            ),
            404,
        )

    @app.errorhandler(500)
    def handle_server_error(error):
        log_event(
            "error",
            "server_error",
            ip=client_ip(),
            path=request.path,
            error=type(error).__name__,
        )
        return (
            render_template(
                "error.html",
                status_code=500,
                message="Ocurrio un error interno. El evento ya fue registrado.",
            ),
            500,
        )

    @app.route("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = RegisterForm()
        if form.validate_on_submit():
            existing_user = db.session.execute(
                db.select(User).filter_by(username=form.username.data)
            ).scalar_one_or_none()
            if existing_user:
                log_event(
                    "warning",
                    "registration_duplicate",
                    ip=client_ip(),
                    username=form.username.data,
                )
                flash("ERROR: Identidad duplicada en sistema.", "danger")
            else:
                total_users = db.session.execute(
                    db.select(func.count(User.id))
                ).scalar_one()
                role = ROLE_ADMIN if total_users == 0 else ROLE_OPERATOR
                user = User(username=form.username.data, role=role)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                log_event(
                    "info",
                    "registration_success",
                    ip=client_ip(),
                    role=role,
                    username=user.username,
                )
                flash("Operador registrado correctamente.", "success")
                return redirect(url_for("login"))
        elif form.is_submitted():
            flash_form_errors(form)

        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = LoginForm()
        if form.validate_on_submit():
            user = db.session.execute(
                db.select(User).filter_by(username=form.username.data)
            ).scalar_one_or_none()
            if user and user.check_password(form.password.data):
                session.permanent = True
                login_user(user, remember=False)
                log_event(
                    "info",
                    "login_success",
                    ip=client_ip(),
                    role=user.role,
                    username=user.username,
                )
                flash("Acceso concedido.", "success")
                return redirect(url_for("dashboard"))

            log_event(
                "warning",
                "login_failure",
                ip=client_ip(),
                username=form.username.data,
            )
            flash("ACCESO DENEGADO.", "danger")
        elif form.is_submitted():
            flash_form_errors(form)

        return render_template("login.html", form=form)

    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        form = MissionForm()
        action_form = ActionForm()
        assistant_form = AssistantForm(prefix="assistant")
        if form.validate_on_submit():
            mission = Mission(
                title=form.title.data,
                description=form.description.data,
                priority=form.priority.data,
                user_id=current_user.id,
            )
            db.session.add(mission)
            db.session.commit()
            log_event(
                "info",
                "mission_created",
                actor=current_user.username,
                mission_id=mission.id,
                owner=current_user.username,
                priority=mission.priority,
            )
            flash("Mision registrada correctamente.", "success")
            return redirect(url_for("dashboard"))
        elif form.is_submitted():
            flash_form_errors(form)

        assistant_form.mission_id.choices, missions = mission_choices_for_user(current_user)
        assistant_result = session.pop("assistant_result", None)
        assistant_error = session.pop("assistant_error", None)
        stats = {
            "total": len(missions),
            "active": sum(1 for mission in missions if mission.status == "EN PROGRESO"),
            "done": sum(1 for mission in missions if mission.status == "COMPLETADA"),
        }
        return render_template(
            "dashboard.html",
            form=form,
            action_form=action_form,
            assistant_form=assistant_form,
            assistant_result=assistant_result,
            assistant_error=assistant_error,
            assistant_enabled=assistant_available(app),
            assistant_model=app.config["GEMINI_MODEL"],
            missions=missions,
            stats=stats,
        )

    @app.route("/assistant", methods=["POST"])
    @login_required
    def assistant():
        assistant_form = AssistantForm(prefix="assistant")
        assistant_form.mission_id.choices, _missions = mission_choices_for_user(current_user)

        if not assistant_available(app):
            session["assistant_error"] = (
                "El asistente IA no esta disponible. Configura GEMINI_API_KEY "
                "e instala la dependencia google-genai."
            )
            return redirect(url_for("dashboard"))

        if not assistant_form.validate_on_submit():
            session["assistant_error"] = "No se pudo procesar la consulta."
            session["assistant_result"] = None
            if assistant_form.errors:
                first_errors = []
                for errors in assistant_form.errors.values():
                    first_errors.extend(errors)
                if first_errors:
                    session["assistant_error"] = first_errors[0]
            return redirect(url_for("dashboard"))

        mission = None
        mission_id = assistant_form.mission_id.data
        if mission_id:
            mission = db.session.get(Mission, int(mission_id))
            if not mission:
                abort(404)
            if not can_manage_mission(current_user, mission):
                log_event(
                    "warning",
                    "assistant_authorization_denied",
                    actor=current_user.username,
                    mission_id=mission_id,
                )
                abort(403)

        try:
            client = get_gemini_client(app)
            response = client.models.generate_content(
                model=app.config["GEMINI_MODEL"],
                contents=build_assistant_input(assistant_form.prompt.data, mission),
            )
            session["assistant_result"] = extract_response_text(response)
            session["assistant_error"] = None
            log_event(
                "info",
                "assistant_success",
                actor=current_user.username,
                mission_id=mission.id if mission else "none",
                model=app.config["GEMINI_MODEL"],
            )
        except Exception as error:
            session["assistant_result"] = None
            session["assistant_error"] = (
                "La consulta con IA fallo. Revisa configuracion y logs."
            )
            log_event(
                "error",
                "assistant_failure",
                actor=current_user.username,
                error=type(error).__name__,
                mission_id=mission.id if mission else "none",
            )

        return redirect(url_for("dashboard"))

    @app.route("/mission/<int:mission_id>/<action>", methods=["POST"])
    @login_required
    def update_mission(mission_id, action):
        form = ActionForm()
        if not form.validate_on_submit():
            abort(400)

        if action not in VALID_MISSION_ACTIONS:
            abort(400)

        mission = db.session.get(Mission, mission_id)
        if not mission:
            abort(404)
        if not can_manage_mission(current_user, mission):
            log_event(
                "warning",
                "authorization_denied",
                actor=current_user.username,
                mission_id=mission_id,
                owner_id=mission.user_id,
            )
            abort(403)

        if action == "start":
            mission.status = "EN PROGRESO"
            event_name = "mission_started"
        elif action == "complete":
            mission.status = "COMPLETADA"
            event_name = "mission_completed"
        else:
            db.session.delete(mission)
            event_name = "mission_deleted"

        db.session.commit()
        log_event(
            "info",
            event_name,
            actor=current_user.username,
            mission_id=mission_id,
        )
        flash("Cambio aplicado correctamente.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        username = current_user.username
        log_event("info", "logout", ip=client_ip(), username=username)
        logout_user()
        session.clear()
        flash("Sesion finalizada.", "success")
        return redirect(url_for("login"))

    with app.app_context():
        initialize_database()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, ssl_context="adhoc")
