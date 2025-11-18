import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class BaseConfig:
    """Base configuration for Brain Jelly."""

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    TESTING = False
    DEBUG = False
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # Database configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://brainjelly:brainjelly@localhost:5432/brainjelly_dev",
    )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis / Celery configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env_name: str | None) -> type[BaseConfig]:
    """Return the config class associated with the given environment."""
    if env_name is None:
        return CONFIG_MAP["default"]
    return CONFIG_MAP.get(env_name, CONFIG_MAP["default"])

