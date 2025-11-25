from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env files."""

    app_name: str = Field(default="PrecisionControlBackend")
    log_level: str = Field(default="INFO")
    prometheus_enabled: bool = Field(default=True)
    metrics_host: str = Field(default="0.0.0.0")
    metrics_port: int = Field(default=9000)
    coordinator_max_workers: int = Field(default=8)
    worker_heartbeat_timeout_ms: int = Field(default=500)
    worker_restart_backoff_sec: float = Field(default=2.5)
    kinesis_dll_path: str = Field(default="", description="Path to Thorlabs Kinesis DLLs")
    libximc_path: str = Field(default="", description="Path to Standa libximc binaries")
    meca500_address: str = Field(default="192.168.0.100", description="IP address of Meca500 robot")
    meca500_port: int = Field(default=10000, description="TCP port for Meca500")
    pdxc2_serial: str = Field(default="112498387", description="Serial number of PDXC2 device")
    pdxc2_usb_port: str = Field(default="", description="USB port identifier from Device Manager (e.g., Port_#0007.Hub_#0001)")
    pdxc2_default_mode: str = Field(default="open_loop", description="Default control mode: open_loop or closed_loop")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
