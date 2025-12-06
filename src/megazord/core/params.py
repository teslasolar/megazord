"""
Megazord Configuration Parameters
ISA-88/95/101 Compliant Parameter Structure
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _env(key: str, default: Any) -> Any:
    """Get environment variable with type coercion."""
    val = os.environ.get(key)
    if val is None:
        return default
    if isinstance(default, bool):
        return val.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        return int(val)
    if isinstance(default, float):
        return float(val)
    return val


@dataclass
class SysParams:
    """System-level parameters."""

    name: str = field(default_factory=lambda: _env("SYS_NAME", "Megazord"))
    gpu_count_max: int = field(default_factory=lambda: _env("GPU_MAX", 16))
    api_port: int = field(default_factory=lambda: _env("API_PORT", 8420))
    ws_port: int = field(default_factory=lambda: _env("WS_PORT", 8421))
    db_path: str = field(default_factory=lambda: _env("DB_PATH", "~/.megazord/state.db"))
    health_interval_sec: int = field(default_factory=lambda: _env("HEALTH_INT", 30))
    queue_max: int = field(default_factory=lambda: _env("QUEUE_MAX", 100))
    log_level: int = field(default_factory=lambda: _env("LOG_LVL", 2))  # 0=ERR,1=WARN,2=INFO,3=DEBUG

    @property
    def db_path_resolved(self) -> Path:
        """Get resolved database path."""
        return Path(self.db_path).expanduser()


@dataclass
class ThermParams:
    """Thermal management parameters."""

    warn: int = field(default_factory=lambda: _env("TEMP_WARN", 75))
    throttle: int = field(default_factory=lambda: _env("TEMP_THROT", 83))
    shutdown: int = field(default_factory=lambda: _env("TEMP_SHUT", 90))
    hysteresis: int = field(default_factory=lambda: _env("TEMP_HYST", 5))


@dataclass
class RouterParams:
    """Router configuration parameters."""

    timeout_sec: int = field(default_factory=lambda: _env("RTR_TIMEOUT", 300))
    retry_max: int = field(default_factory=lambda: _env("RTR_RETRY", 3))
    prefer_loaded: bool = field(default_factory=lambda: _env("RTR_PREFER", True))
    balance_mode: int = field(default_factory=lambda: _env("RTR_BAL", 0))  # 0=Speed,1=VRAM,2=RoundRobin


@dataclass
class ModelParams:
    """Model management parameters."""

    unload_idle_min: int = field(default_factory=lambda: _env("MDL_IDLE", 30))
    cache_max: int = field(default_factory=lambda: _env("MDL_CACHE", 3))
    shard_min_gpus: int = field(default_factory=lambda: _env("MDL_SHARD_MIN", 2))


@dataclass
class RecipeParams:
    """Recipe default parameters."""

    max_tokens: int = field(default_factory=lambda: _env("RCP_TOKENS", 4096))
    temperature: float = field(default_factory=lambda: _env("RCP_TEMP", 0.7))
    top_p: float = field(default_factory=lambda: _env("RCP_TOP_P", 0.9))
    context_len: int = field(default_factory=lambda: _env("RCP_CTX", 8192))


@dataclass
class PhysicalModel:
    """ISA-95 Physical Model hierarchy."""

    enterprise: str = field(default_factory=lambda: _env("ENTERPRISE", "LocalCompute"))
    site: str = field(default_factory=lambda: _env("SITE", "HomeLab"))
    area: str = field(default_factory=lambda: _env("AREA", "GPUCluster"))

    @property
    def process_cell(self) -> str:
        """Get process cell name from system params."""
        return _env("SYS_NAME", "Megazord")


@dataclass
class Params:
    """
    Master configuration container.
    All parameters are environment-configurable with sensible defaults.
    """

    sys: SysParams = field(default_factory=SysParams)
    therm: ThermParams = field(default_factory=ThermParams)
    router: RouterParams = field(default_factory=RouterParams)
    model: ModelParams = field(default_factory=ModelParams)
    recipe: RecipeParams = field(default_factory=RecipeParams)
    physical: PhysicalModel = field(default_factory=PhysicalModel)

    def to_dict(self) -> dict[str, Any]:
        """Export all parameters as a dictionary."""
        return {
            "sys": {
                "name": self.sys.name,
                "gpu_count_max": self.sys.gpu_count_max,
                "api_port": self.sys.api_port,
                "ws_port": self.sys.ws_port,
                "db_path": self.sys.db_path,
                "health_interval_sec": self.sys.health_interval_sec,
                "queue_max": self.sys.queue_max,
                "log_level": self.sys.log_level,
            },
            "therm": {
                "warn": self.therm.warn,
                "throttle": self.therm.throttle,
                "shutdown": self.therm.shutdown,
                "hysteresis": self.therm.hysteresis,
            },
            "router": {
                "timeout_sec": self.router.timeout_sec,
                "retry_max": self.router.retry_max,
                "prefer_loaded": self.router.prefer_loaded,
                "balance_mode": self.router.balance_mode,
            },
            "model": {
                "unload_idle_min": self.model.unload_idle_min,
                "cache_max": self.model.cache_max,
                "shard_min_gpus": self.model.shard_min_gpus,
            },
            "recipe": {
                "max_tokens": self.recipe.max_tokens,
                "temperature": self.recipe.temperature,
                "top_p": self.recipe.top_p,
                "context_len": self.recipe.context_len,
            },
            "physical": {
                "enterprise": self.physical.enterprise,
                "site": self.physical.site,
                "area": self.physical.area,
                "process_cell": self.physical.process_cell,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Params:
        """Create Params from dictionary."""
        params = cls()
        if "sys" in data:
            for k, v in data["sys"].items():
                if hasattr(params.sys, k):
                    setattr(params.sys, k, v)
        if "therm" in data:
            for k, v in data["therm"].items():
                if hasattr(params.therm, k):
                    setattr(params.therm, k, v)
        if "router" in data:
            for k, v in data["router"].items():
                if hasattr(params.router, k):
                    setattr(params.router, k, v)
        if "model" in data:
            for k, v in data["model"].items():
                if hasattr(params.model, k):
                    setattr(params.model, k, v)
        if "recipe" in data:
            for k, v in data["recipe"].items():
                if hasattr(params.recipe, k):
                    setattr(params.recipe, k, v)
        return params
