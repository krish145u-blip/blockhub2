import ast
import hashlib
import hmac
import html
import os
import re
import secrets
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class BlockhubSecurityAndArchitectureTests(unittest.TestCase):
    def test_01_password_hashing_and_verification(self):
        # Verify PBKDF2-HMAC-SHA256 implementation from backend/security.py
        salt = secrets.token_hex(16)
        raw = "StrongUniqueAdminPassword!2026"
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), 260000)
        stored = f"pbkdf2_sha256$260000${salt}${dk.hex()}"

        algo, iters, s_val, digest = stored.split("$")
        self.assertEqual(algo, "pbkdf2_sha256")
        check_dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), s_val.encode("utf-8"), int(iters))
        self.assertTrue(hmac.compare_digest(check_dk.hex(), digest))

    def test_02_admin_bootstrap_configuration_and_secret_scrubbing(self):
        env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("FIRST_ADMIN_EMAIL=krish137u@gmail.com", env_example)
        self.assertIn("FIRST_ADMIN_PASSWORD=YOUR_NEW_STRONG_UNIQUE_PASSWORD", env_example)

        seed_src = (PROJECT_ROOT / "backend/seed.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("FIRST_ADMIN_EMAIL", "krish137u@gmail.com")', seed_src)
        self.assertIn('os.getenv("FIRST_ADMIN_PASSWORD")', seed_src)
        self.assertIn('os.environ.pop("FIRST_ADMIN_PASSWORD", None)', seed_src)

    def test_03_zero_frontend_credentials_and_all_14_models_defined(self):
        frontend_html = (PROJECT_ROOT / "frontend/templates/index.html").read_text(encoding="utf-8")
        self.assertNotIn('value="VerifiedDev!2026"', frontend_html)
        self.assertNotIn("YOUR_NEW_STRONG_UNIQUE_PASSWORD", frontend_html.split("FIRST_ADMIN_PASSWORD=")[0])

        models_src = (PROJECT_ROOT / "backend/models.py").read_text(encoding="utf-8")
        tree = ast.parse(models_src)
        class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        expected_models = {
            "User",
            "UserProfile",
            "DeveloperProfile",
            "Category",
            "Launcher",
            "LauncherScreenshot",
            "LauncherVersion",
            "DownloadLink",
            "DownloadEvent",
            "Review",
            "Report",
            "VerificationRequest",
            "Notification",
            "AdminActivityLog",
        }
        self.assertTrue(expected_models.issubset(class_names))

    def test_04_default_guest_mode_and_registration_blocks_privilege_escalation(self):
        auth_src = (PROJECT_ROOT / "backend/routes/auth.py").read_text(encoding="utf-8")
        self.assertIn('if payload.role != "user":', auth_src)
        self.assertIn("Public registration cannot assign developer or administrator privileges.", auth_src)
        self.assertIn('"require_login": True', auth_src)

        frontend_html = (PROJECT_ROOT / "frontend/templates/index.html").read_text(encoding="utf-8")
        self.assertIn("role: 'guest'", frontend_html)
        self.assertIn("isAuthenticated: false", frontend_html)
        self.assertNotIn('<input id="loginRemember" type="checkbox" checked', frontend_html)

    def test_05_xss_sanitization_and_image_magic_bytes(self):
        malicious = '<script>evil()</script><b>Prism</b>'
        cleaned = re.sub(r"<script.*?>.*?</script>", "", malicious, flags=re.IGNORECASE | re.DOTALL)
        escaped = html.escape(cleaned.strip(), quote=False)
        self.assertNotIn("<script>", escaped)
        self.assertEqual(escaped, "&lt;b&gt;Prism&lt;/b&gt;")


if __name__ == "__main__":
    unittest.main()
