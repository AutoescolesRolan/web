import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("PROVES_DB") or f"sqlite:///{_tmp}/proves.db"
os.environ["ADMIN_EMAIL"] = "admin@proves.cat"
os.environ["ADMIN_PASSWORD"] = "proves12345"
os.environ["SECRET_KEY"] = "clau-de-proves"
os.environ["PUBLIC_URL"] = "https://web.proves"
for k in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "RESEND_API_KEY", "SMTP_HOST", "MAIL_FROM"):
    os.environ.pop(k, None)
