"""Configuration read from environment variables (never hard-coded)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection settings for the MySQL securities master."""

    user: str
    password: str
    host: str = "localhost"
    port: int = 3306
    database: str = "securities_master"

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Build the config from ``MYSQL_*`` variables (a ``.env`` file is loaded if present)."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        missing = [v for v in ("MYSQL_USER", "MYSQL_PASSWORD") if not os.getenv(v)]
        if missing:
            raise RuntimeError(
                f"Missing environment variables: {', '.join(missing)}. Copy .env.example to .env and fill it in."
            )
        return cls(
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE", "securities_master"),
        )

    @property
    def sqlalchemy_url(self) -> str:
        return f"mysql+mysqlconnector://{self.user}:{quote_plus(self.password)}@{self.host}:{self.port}/{self.database}"

    def connector_kwargs(self) -> dict:
        """Arguments for ``mysql.connector.connect``."""
        return {
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "database": self.database,
        }
