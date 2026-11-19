"""Settings, read once from environment variables. Nothing secret has a default."""
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # postgresql://... (Neon in production). Required.
    database_url: str = ""
    # The single sign-in password. The app stays locked until it is set.
    app_password: str = ""
    # Public address of the app, e.g. https://personal-chef.onrender.com. Passkeys are bound to it.
    app_origin: str = "http://localhost:8000"
    # Cookies are Secure (HTTPS only) unless this is switched off for local http testing.
    cookie_secure: bool = True
    session_days: int = 30
    # Where the built PWA lives. Empty = API only.
    frontend_dir: str = ""

    @property
    def rp_id(self) -> str:
        return urlparse(self.app_origin).hostname or "localhost"

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        # Neon needs TLS. Add it if the pasted string leaves it out (never for a local socket/host).
        host = urlparse(url).hostname or ""
        if host.endswith("neon.tech") and "sslmode=" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
