import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _get_bool(env_var: str, default: bool = False) -> bool:
    val = os.getenv(env_var)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Base configuration shared across environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = False
    TESTING = False

    # MySQL / Aiven database settings
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "stock_db")
    DB_CHARSET = "utf8mb4"
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "15"))

    # Supply chain / inventory defaults
    DEFAULT_SERVICE_LEVEL = float(os.getenv("DEFAULT_SERVICE_LEVEL", "0.95"))
    HISTORICAL_YEARS = int(os.getenv("HISTORICAL_YEARS", "5"))
    ABC_A_THRESHOLD = 80.0
    ABC_B_THRESHOLD = 95.0


class DevelopmentConfig(Config):
    """Local/development configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    DB_NAME = os.getenv("TEST_DB_NAME", os.getenv("DB_NAME", "stock_db"))


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "test": TestingConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config() -> type[Config]:
    env_name = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "default")).strip().lower()
    return CONFIG_BY_NAME.get(env_name, DevelopmentConfig)