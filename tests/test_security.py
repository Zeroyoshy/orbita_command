import os
import tempfile
import unittest

from app import Mission, User, create_app, db


class FakeModelsClient:
    def generate_content(self, model, contents):
        class FakeResponse:
            text = (
                f"Modelo {model}: sugerencia generada para "
                f"{'Orbita' if 'Orbita' in contents else 'consulta'}"
            )

        return FakeResponse()


class FakeGeminiClient:
    def __init__(self):
        self.models = FakeModelsClient()


class SecurityTestCase(unittest.TestCase):
    def setUp(self):
        db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_file.close()
        self.db_path = db_file.name
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.db_path}",
                "WTF_CSRF_ENABLED": False,
                "ENFORCE_HTTPS": False,
                "SESSION_COOKIE_SECURE": False,
                "REMEMBER_COOKIE_SECURE": False,
                "GEMINI_API_KEY": "test-gemini-key",
                "GEMINI_MODEL": "gemini-2.5-flash",
                "GEMINI_CLIENT_FACTORY": lambda _api_key: FakeGeminiClient(),
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        os.unlink(self.db_path)

    def register(self, username, password):
        return self.client.post(
            "/register",
            data={
                "username": username,
                "password": password,
                "confirm": password,
            },
            follow_redirects=True,
        )

    def login(self, username, password):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_first_registered_user_becomes_admin_and_password_is_hashed(self):
        password = "ClaveSegura#2026"
        response = self.register("admin_user", password)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(username="admin_user")
            ).scalar_one()
            self.assertEqual(user.role, "ADMIN")
            self.assertNotEqual(user.password_hash, password)
            self.assertTrue(user.check_password(password))

    def test_dashboard_requires_authentication(self):
        response = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ACCEDER SISTEMA", response.data)

    def test_operator_cannot_modify_another_users_mission(self):
        admin_password = "AdminSegura#2026"
        operator_password = "OperadorSegura#2026"
        self.register("admin_user", admin_password)
        self.register("operator_user", operator_password)

        with self.app.app_context():
            admin = db.session.execute(
                db.select(User).filter_by(username="admin_user")
            ).scalar_one()
            operator = db.session.execute(
                db.select(User).filter_by(username="operator_user")
            ).scalar_one()
            mission = Mission(
                title="Orbita 1",
                description="Mision administrada",
                priority="ALTA",
                user_id=admin.id,
            )
            db.session.add(mission)
            db.session.commit()
            mission_id = mission.id
            self.assertEqual(operator.role, "OPERADOR")

        self.login("operator_user", operator_password)
        response = self.client.post(
            f"/mission/{mission_id}/delete",
            data={},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 403)

    def test_security_headers_are_present(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_assistant_route_returns_model_output(self):
        password = "ClaveSegura#2026"
        self.register("admin_user", password)
        self.login("admin_user", password)

        with self.app.app_context():
            admin = db.session.execute(
                db.select(User).filter_by(username="admin_user")
            ).scalar_one()
            mission = Mission(
                title="Orbita 7",
                description="Monitoreo de satelite",
                priority="MEDIA",
                user_id=admin.id,
            )
            db.session.add(mission)
            db.session.commit()
            mission_id = mission.id

        response = self.client.post(
            "/assistant",
            data={
                "assistant-mission_id": str(mission_id),
                "assistant-prompt": "Resume riesgos y siguientes pasos.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"sugerencia generada", response.data)


if __name__ == "__main__":
    unittest.main()
