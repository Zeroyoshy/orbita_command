import base64
import logging
import os
import secrets
import smtplib
import sys
from datetime import timedelta
from email.message import EmailMessage
from io import BytesIO

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
from flask_wtf.csrf import CSRFError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import qrcode
from sqlalchemy import func, inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
import pyotp
from wtforms import PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

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
DEFAULT_MFA_ISSUER = "ORBITA COMMAND"
DEFAULT_PASSWORD_RESET_MAX_AGE = 3600

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def load_environment():
    load_dotenv(".env")


def configure_logging():
    handlers = [logging.StreamHandler(sys.stdout)]
    if os.getenv("LOG_TO_FILE", "true").lower() == "true":
        handlers.append(logging.FileHandler("mission_logs.log"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )


def validate_no_html(_form, field):
    if field.data and any(char in field.data for char in "<>"):
        raise ValidationError("No se permite HTML en este campo.")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_OPERATOR)
    mfa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    missions = db.relationship("Mission", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    def ensure_mfa_secret(self):
        if not self.mfa_secret:
            self.mfa_secret = pyotp.random_base32()

    def get_totp_uri(self, issuer_name):
        self.ensure_mfa_secret()
        label = self.email or self.username
        return pyotp.TOTP(self.mfa_secret).provisioning_uri(name=label, issuer_name=issuer_name)

    def verify_totp(self, code):
        if not self.mfa_secret or not code:
            return False
        return pyotp.TOTP(self.mfa_secret).verify(code, valid_window=1)


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
    totp_code = StringField(
        "Codigo MFA",
        validators=[Optional(), Length(min=6, max=6), Regexp(r"^\d{6}$", message="El codigo MFA debe tener 6 digitos.")],
        filters=[lambda value: value.strip() if value else value],
    )
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
    email = StringField(
        "Correo",
        validators=[DataRequired(), Email(), Length(max=120)],
        filters=[lambda value: value.strip().lower() if value else value],
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


class PasswordResetRequestForm(FlaskForm):
    email = StringField(
        "Correo registrado",
        validators=[DataRequired(), Email(), Length(max=120)],
        filters=[lambda value: value.strip().lower() if value else value],
    )
    submit = SubmitField("ENVIAR ENLACE")


class PasswordResetForm(FlaskForm):
    password = PasswordField(
        "Nueva clave",
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
        "Confirmar nueva clave",
        validators=[DataRequired(), EqualTo("password", message="Las claves no coinciden.")],
    )
    submit = SubmitField("ACTUALIZAR CLAVE")


class EnableMFAForm(FlaskForm):
    totp_code = StringField(
        "Codigo de verificacion",
        validators=[DataRequired(), Length(min=6, max=6), Regexp(r"^\d{6}$", message="Ingresa un codigo TOTP valido.")],
        filters=[lambda value: value.strip() if value else value],
    )
    submit = SubmitField("ACTIVAR MFA")


class DisableMFAForm(FlaskForm):
    password = PasswordField("Clave actual", validators=[DataRequired()])
    totp_code = StringField(
        "Codigo MFA",
        validators=[DataRequired(), Length(min=6, max=6), Regexp(r"^\d{6}$", message="Ingresa un codigo TOTP valido.")],
        filters=[lambda value: value.strip() if value else value],
    )
    submit = SubmitField("DESACTIVAR MFA")


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


def generate_qr_code_data_uri(content):
    image = qrcode.make(content)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def get_reset_serializer(app):
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="password-reset")


def generate_password_reset_token(app, user):
    return get_reset_serializer(app).dumps({"user_id": user.id, "purpose": "password-reset"})


def load_password_reset_user(app, token):
    try:
        data = get_reset_serializer(app).loads(
            token,
            max_age=app.config["PASSWORD_RESET_TOKEN_MAX_AGE"],
        )
    except (BadSignature, SignatureExpired):
        return None
    if data.get("purpose") != "password-reset":
        return None
    return db.session.get(User, int(data["user_id"]))


def build_external_url(path):
    base_url = os.getenv("APP_BASE_URL")
    if base_url:
        return f"{base_url.rstrip('/')}{path}"
    return f"{request.url_root.rstrip('/')}{path}"


def smtp_enabled(app):
    required = ["MAIL_SERVER", "MAIL_PORT", "MAIL_FROM"]
    return all(app.config.get(key) for key in required)


def send_password_reset_email(app, user, reset_url):
    if app.config.get("MAIL_SUPPRESS_SEND"):
        app.config["LAST_PASSWORD_RESET_LINK"] = reset_url
        log_event("info", "password_reset_link_generated", email=user.email, reset_url=reset_url)
        return

    if not smtp_enabled(app):
        log_event("warning", "password_reset_smtp_missing", email=user.email, reset_url=reset_url)
        return

    message = EmailMessage()
    message["Subject"] = "ORBITA COMMAND - Recuperacion de contraseña"
    message["From"] = app.config["MAIL_FROM"]
    message["To"] = user.email
    message.set_content(
        "Recibimos una solicitud para restablecer tu clave.\n\n"
        f"Abre este enlace para continuar:\n{reset_url}\n\n"
        "Si no solicitaste el cambio, puedes ignorar este correo."
    )

    with smtplib.SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]) as server:
        if app.config["MAIL_USE_TLS"]:
            server.starttls()
        if app.config.get("MAIL_USERNAME"):
            server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        server.send_message(message)


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


def normalize_database_url(database_url):
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def initialize_database():
    db.create_all()
    inspector = inspect(db.engine)
    if inspector.has_table("user"):
        user_columns = {column["name"] for column in inspector.get_columns("user")}
        preparer = db.engine.dialect.identifier_preparer
        quoted_user_table = preparer.quote(User.__table__.name)
        with db.engine.begin() as connection:
            if "role" not in user_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {quoted_user_table} "
                        "ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'OPERADOR'"
                    )
                )
                connection.execute(
                    text(
                        f"UPDATE {quoted_user_table} "
                        "SET role = 'OPERADOR' WHERE role IS NULL"
                    )
                )
            if "email" not in user_columns:
                connection.execute(
                    text(f"ALTER TABLE {quoted_user_table} ADD COLUMN email VARCHAR(120)")
                )
            if "mfa_enabled" not in user_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {quoted_user_table} "
                        "ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
            if "mfa_secret" not in user_columns:
                connection.execute(
                    text(f"ALTER TABLE {quoted_user_table} ADD COLUMN mfa_secret VARCHAR(32)")
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
        SQLALCHEMY_DATABASE_URI=normalize_database_url(
            os.getenv("DATABASE_URL", "sqlite:///orbita.db")
        ),
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
        MFA_ISSUER=os.getenv("MFA_ISSUER", DEFAULT_MFA_ISSUER),
        PASSWORD_RESET_TOKEN_MAX_AGE=int(
            os.getenv("PASSWORD_RESET_TOKEN_MAX_AGE", str(DEFAULT_PASSWORD_RESET_MAX_AGE))
        ),
        MAIL_SERVER=os.getenv("MAIL_SERVER"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_FROM=os.getenv("MAIL_FROM"),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
        MAIL_SUPPRESS_SEND=os.getenv("MAIL_SUPPRESS_SEND", "false").lower() == "true",
        LAST_PASSWORD_RESET_LINK=None,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
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

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        log_event(
            "warning",
            "csrf_validation_failed",
            ip=client_ip(),
            path=request.path,
            reason=getattr(error, "description", "unknown"),
        )
        return (
            render_template(
                "error.html",
                status_code=400,
                message="La sesion del formulario vencio o el token CSRF no coincide. Recarga la pagina e intenta de nuevo.",
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

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = RegisterForm()
        if form.validate_on_submit():
            existing_user = db.session.execute(
                db.select(User).filter_by(username=form.username.data)
            ).scalar_one_or_none()
            existing_email = db.session.execute(
                db.select(User).filter_by(email=form.email.data)
            ).scalar_one_or_none()
            if existing_user:
                log_event(
                    "warning",
                    "registration_duplicate",
                    ip=client_ip(),
                    username=form.username.data,
                )
                flash("ERROR: Identidad duplicada en sistema.", "danger")
            elif existing_email:
                log_event(
                    "warning",
                    "registration_duplicate_email",
                    email=form.email.data,
                    ip=client_ip(),
                )
                flash("ERROR: El correo ya esta registrado.", "danger")
            else:
                total_users = db.session.execute(
                    db.select(func.count(User.id))
                ).scalar_one()
                role = ROLE_ADMIN if total_users == 0 else ROLE_OPERATOR
                user = User(username=form.username.data, email=form.email.data, role=role)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                log_event(
                    "info",
                    "registration_success",
                    email=user.email,
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
                if user.mfa_enabled:
                    if not user.verify_totp(form.totp_code.data):
                        log_event(
                            "warning",
                            "login_mfa_failure",
                            ip=client_ip(),
                            username=user.username,
                        )
                        flash("Codigo MFA invalido.", "danger")
                        return render_template("login.html", form=form)
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

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = PasswordResetRequestForm()
        if form.validate_on_submit():
            user = db.session.execute(
                db.select(User).filter_by(email=form.email.data)
            ).scalar_one_or_none()
            if user:
                token = generate_password_reset_token(app, user)
                reset_url = build_external_url(url_for("reset_password", token=token))
                send_password_reset_email(app, user, reset_url)
                log_event(
                    "info",
                    "password_reset_requested",
                    email=user.email,
                    username=user.username,
                )
            flash(
                "Si existe una cuenta asociada a ese correo, se genero un enlace de recuperacion.",
                "success",
            )
            return redirect(url_for("login"))
        elif form.is_submitted():
            flash_form_errors(form)

        return render_template("forgot_password.html", form=form)

    @app.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        user = load_password_reset_user(app, token)
        if not user:
            flash("El enlace de recuperacion es invalido o ya vencio.", "danger")
            return redirect(url_for("forgot_password"))

        form = PasswordResetForm()
        if form.validate_on_submit():
            user.set_password(form.password.data)
            db.session.commit()
            log_event(
                "info",
                "password_reset_completed",
                email=user.email,
                username=user.username,
            )
            flash("Clave actualizada correctamente. Ya puedes iniciar sesion.", "success")
            return redirect(url_for("login"))
        elif form.is_submitted():
            flash_form_errors(form)

        return render_template("reset_password.html", form=form)

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
            mfa_enabled=current_user.mfa_enabled,
            missions=missions,
            stats=stats,
        )

    @app.route("/security", methods=["GET", "POST"])
    @login_required
    def security():
        enable_form = EnableMFAForm(prefix="enable")
        disable_form = DisableMFAForm(prefix="disable")

        if enable_form.submit.data and enable_form.validate_on_submit():
            current_user.ensure_mfa_secret()
            if current_user.verify_totp(enable_form.totp_code.data):
                current_user.mfa_enabled = True
                db.session.commit()
                log_event("info", "mfa_enabled", username=current_user.username)
                flash("MFA activado correctamente.", "success")
                return redirect(url_for("security"))
            flash("No se pudo validar el codigo TOTP.", "danger")

        if disable_form.submit.data and disable_form.validate_on_submit():
            if not current_user.check_password(disable_form.password.data):
                flash("La clave actual no coincide.", "danger")
            elif not current_user.verify_totp(disable_form.totp_code.data):
                flash("El codigo MFA es invalido.", "danger")
            else:
                current_user.mfa_enabled = False
                current_user.mfa_secret = None
                db.session.commit()
                log_event("info", "mfa_disabled", username=current_user.username)
                flash("MFA desactivado correctamente.", "success")
                return redirect(url_for("security"))

        qr_code_data = None
        manual_secret = None
        if not current_user.mfa_enabled:
            current_user.ensure_mfa_secret()
            db.session.commit()
            manual_secret = current_user.mfa_secret
            qr_code_data = generate_qr_code_data_uri(
                current_user.get_totp_uri(app.config["MFA_ISSUER"])
            )

        return render_template(
            "security.html",
            enable_form=enable_form,
            disable_form=disable_form,
            mfa_enabled=current_user.mfa_enabled,
            qr_code_data=qr_code_data,
            manual_secret=manual_secret,
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
            log_event(
                "warning",
                "mission_action_invalid_form",
                actor=current_user.username,
                mission_id=mission_id,
                action=action,
                errors=form.errors,
            )
            flash("No se pudo aplicar el cambio. Recarga el panel e intenta de nuevo.", "danger")
            return redirect(url_for("dashboard"))

        if action not in VALID_MISSION_ACTIONS:
            log_event(
                "warning",
                "mission_action_invalid_action",
                actor=current_user.username,
                mission_id=mission_id,
                action=action,
            )
            flash("La accion solicitada no es valida.", "danger")
            return redirect(url_for("dashboard"))

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
            if mission.status != "PENDIENTE":
                log_event(
                    "warning",
                    "mission_action_invalid_state",
                    actor=current_user.username,
                    mission_id=mission_id,
                    action=action,
                    current_status=mission.status,
                )
                flash("Solo puedes iniciar misiones pendientes.", "warning")
                return redirect(url_for("dashboard"))
            mission.status = "EN PROGRESO"
            event_name = "mission_started"
        elif action == "complete":
            if mission.status != "EN PROGRESO":
                log_event(
                    "warning",
                    "mission_action_invalid_state",
                    actor=current_user.username,
                    mission_id=mission_id,
                    action=action,
                    current_status=mission.status,
                )
                flash("Solo puedes completar misiones en progreso.", "warning")
                return redirect(url_for("dashboard"))
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
