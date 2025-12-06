"""
Megazord User Defined Types (UDTs)
ISA-88 Compliant Data Structures
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from megazord.core.states import ST, RS


@dataclass
class UDT_GPU:
    """
    GPU Equipment Module Data Structure

    Represents a single GPU in the cluster with all relevant
    monitoring and control attributes.
    """

    h: str                          # Hash (8 char)
    idx: int                        # Device index
    vram_total: int                 # MB
    vram_avail: int                 # MB
    speed: float = 0.0              # tok/s (benchmarked)
    temp: int = 0                   # Celsius
    load: float = 0.0               # 0.0-1.0
    status: int = ST.OFF            # State enum
    t: int = field(default_factory=lambda: int(time.time()))  # Last seen
    name: str = ""                  # GPU name (e.g., "RTX 4090")
    uuid: str = ""                  # NVIDIA UUID

    @property
    def ok(self) -> bool:
        """Check if GPU is ready and not overheating."""
        return self.status == ST.READY and self.temp < 83  # Default throttle

    def ok_with_threshold(self, throttle_temp: int) -> bool:
        """Check if GPU is ready with custom thermal threshold."""
        return self.status == ST.READY and self.temp < throttle_temp

    @property
    def vram_used(self) -> int:
        """Calculate used VRAM in MB."""
        return self.vram_total - self.vram_avail

    @property
    def vram_pct(self) -> float:
        """Calculate VRAM usage percentage."""
        if self.vram_total == 0:
            return 0.0
        return (self.vram_used / self.vram_total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "h": self.h,
            "idx": self.idx,
            "name": self.name,
            "uuid": self.uuid,
            "vram_total": self.vram_total,
            "vram_avail": self.vram_avail,
            "vram_used": self.vram_used,
            "vram_pct": round(self.vram_pct, 1),
            "speed": round(self.speed, 2),
            "temp": self.temp,
            "load": round(self.load, 2),
            "status": self.status,
            "status_label": ST(self.status).label,
            "ok": self.ok,
            "t": self.t,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UDT_GPU:
        """Deserialize from dictionary."""
        return cls(
            h=data["h"],
            idx=data["idx"],
            vram_total=data["vram_total"],
            vram_avail=data["vram_avail"],
            speed=data.get("speed", 0.0),
            temp=data.get("temp", 0),
            load=data.get("load", 0.0),
            status=data.get("status", ST.OFF),
            t=data.get("t", int(time.time())),
            name=data.get("name", ""),
            uuid=data.get("uuid", ""),
        )


@dataclass
class UDT_Model:
    """
    Model Data Structure

    Represents an LLM model that can be loaded onto GPU(s).
    """

    h: str              # Hash
    name: str           # Model name/path
    vram: int           # MB required
    shard: bool = True  # Can split across GPUs?
    on: list[str] = field(default_factory=list)  # GPU hashes where loaded
    refs: int = 0       # Active request count
    backend: str = ""   # Inference backend (e.g., "vllm", "llamacpp")
    context_len: int = 8192  # Max context length

    @property
    def loaded(self) -> bool:
        """Check if model is currently loaded."""
        return len(self.on) > 0

    def fits(self, gpu: UDT_GPU) -> bool:
        """Check if model fits on a single GPU."""
        return gpu.vram_avail >= self.vram

    def fits_sharded(self, gpus: list[UDT_GPU]) -> bool:
        """Check if model fits across multiple GPUs."""
        if not self.shard:
            return False
        total_vram = sum(g.vram_avail for g in gpus)
        return total_vram >= self.vram

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "h": self.h,
            "name": self.name,
            "vram": self.vram,
            "shard": self.shard,
            "on": self.on,
            "refs": self.refs,
            "loaded": self.loaded,
            "backend": self.backend,
            "context_len": self.context_len,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UDT_Model:
        """Deserialize from dictionary."""
        return cls(
            h=data["h"],
            name=data["name"],
            vram=data["vram"],
            shard=data.get("shard", True),
            on=data.get("on", []),
            refs=data.get("refs", 0),
            backend=data.get("backend", ""),
            context_len=data.get("context_len", 8192),
        )


@dataclass
class UDT_Request:
    """
    Inference Request Data Structure

    Represents a single inference request through the system.
    """

    h: str              # Hash
    model_h: str        # Model hash
    gpu_h: str = ""     # Assigned GPU(s) - CSV for sharded
    tok_in: int = 0     # Input tokens
    tok_out: int = 0    # Output tokens
    status: int = RS.QUEUED  # Request status
    t_start: int = field(default_factory=lambda: int(time.time()))
    t_end: int = 0      # Completion timestamp
    priority: int = 1   # 0=Low, 1=Normal, 2=High
    prompt: str = ""    # Request prompt (for queue)
    result: str = ""    # Response text
    error: str = ""     # Error message if failed

    @property
    def latency_ms(self) -> int:
        """Calculate request latency in milliseconds."""
        if self.t_end == 0:
            return int((time.time() - self.t_start) * 1000)
        return (self.t_end - self.t_start) * 1000

    @property
    def tok_per_sec(self) -> float:
        """Calculate tokens per second."""
        latency_sec = self.latency_ms / 1000
        if latency_sec == 0:
            return 0.0
        return self.tok_out / latency_sec

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "h": self.h,
            "model_h": self.model_h,
            "gpu_h": self.gpu_h,
            "tok_in": self.tok_in,
            "tok_out": self.tok_out,
            "status": self.status,
            "status_label": RS(self.status).label,
            "t_start": self.t_start,
            "t_end": self.t_end,
            "priority": self.priority,
            "latency_ms": self.latency_ms,
            "tok_per_sec": round(self.tok_per_sec, 2),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UDT_Request:
        """Deserialize from dictionary."""
        return cls(
            h=data["h"],
            model_h=data["model_h"],
            gpu_h=data.get("gpu_h", ""),
            tok_in=data.get("tok_in", 0),
            tok_out=data.get("tok_out", 0),
            status=data.get("status", RS.QUEUED),
            t_start=data.get("t_start", int(time.time())),
            t_end=data.get("t_end", 0),
            priority=data.get("priority", 1),
            prompt=data.get("prompt", ""),
            result=data.get("result", ""),
            error=data.get("error", ""),
        )


@dataclass
class UDT_Alarm:
    """
    Alarm Instance Data Structure
    """

    h: str              # Instance hash
    tag: str            # Alarm tag name
    priority: int       # AlarmClass value
    message: str        # Alarm message
    t_raised: int       # Raised timestamp
    t_ack: int = 0      # Acknowledged timestamp
    t_cleared: int = 0  # Cleared timestamp
    ack_by: str = ""    # Who acknowledged
    value: float = 0.0  # Value that triggered alarm

    @property
    def active(self) -> bool:
        """Check if alarm is still active."""
        return self.t_cleared == 0

    @property
    def acknowledged(self) -> bool:
        """Check if alarm has been acknowledged."""
        return self.t_ack > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "h": self.h,
            "tag": self.tag,
            "priority": self.priority,
            "message": self.message,
            "t_raised": self.t_raised,
            "t_ack": self.t_ack,
            "t_cleared": self.t_cleared,
            "ack_by": self.ack_by,
            "value": self.value,
            "active": self.active,
            "acknowledged": self.acknowledged,
        }
