from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config("SECRET_KEY", default="dev-only-key")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = ["*"] if DEBUG else config("ALLOWED_HOSTS", default="").split(",")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "store",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "store.context_processors.cart_and_categories",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME", default="mauli_hardware"),
        "USER": config("DB_USER", default="root"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
    }
}

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default="")

# Delivery rules (edit as per shop)
LOCAL_PINCODE_PREFIXES = ("411", "412")   # Pune area
LOCAL_DELIVERY_CHARGE = 40
OUTSIDE_DELIVERY_CHARGE = 120
FREE_DELIVERY_ABOVE = 2000
RAZORPAY_WEBHOOK_SECRET = config("RAZORPAY_WEBHOOK_SECRET", default="")
