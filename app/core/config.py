from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi aplikasi dari .env (environtment fleksibel, default aman untuk dev)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Aplikasi ----------
    app_name: str = "DSS Klinik Bersalin (BidanCare)"
    app_env: Literal["dev", "prod"] = "dev"
    timezone: str = "Asia/Jakarta"  # "hari ini" untuk aplikasi dan PostgreSQL

    # ---------- Database ----------
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dss_klinik"
    db_echo: bool = False

    # ---------- Keamanan / JWT ----------
    # Tanpa refresh token; cukup taat masa berlaku (keputusan arsitektur)
    jwt_secret: str = "dev-secret-ganti-di-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # kontrak: expires_in 3600

    # ---------- CORS (frontend Vue) ----------
    cors_origins: str | list[str] = []

    # ---------- Keputusan sementara (lihat percakapan: admin via bidan) ----------
    admin_endpoints_allow_bidan: bool = True

    # ---------- Seed akun default bidan (dipakai CLI seed-bidan) ----------
    seed_bidan_username: str = "bidan1"
    seed_bidan_password: str = "bidan12345"
    seed_bidan_nama_lengkap: str = "Bidan Default"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str]) -> list[str]:
        # Format env: dipisah koma, mis. http://localhost:5173,http://localhost:8080
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return self.cors_origins


@lru_cache
def get_settings() -> Settings:
    """Dipakai sebagai dependency FastAPI; hasil di-cache per proses."""
    return Settings()
