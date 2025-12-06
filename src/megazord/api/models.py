"""
Megazord API Models
OpenAI-compatible request/response schemas
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


# --- OpenAI Compatible Models ---

class Message(BaseModel):
    """Chat message."""
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Choice(BaseModel):
    """Completion choice."""
    index: int = 0
    text: str = ""
    message: Message | None = None
    finish_reason: str = "stop"


class CompletionRequest(BaseModel):
    """OpenAI /v1/completions compatible request."""
    model: str
    prompt: str | list[str]
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    n: int = Field(default=1, ge=1, le=10)
    stream: bool = False
    stop: str | list[str] | None = None
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    user: str | None = None


class CompletionResponse(BaseModel):
    """OpenAI /v1/completions compatible response."""
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


class ChatCompletionRequest(BaseModel):
    """OpenAI /v1/chat/completions compatible request."""
    model: str
    messages: list[Message]
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    n: int = Field(default=1, ge=1, le=10)
    stream: bool = False
    stop: str | list[str] | None = None
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    user: str | None = None


class ChatCompletionResponse(BaseModel):
    """OpenAI /v1/chat/completions compatible response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


# --- Megazord-specific Models ---

class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool
    name: str
    version: str
    uptime_sec: int
    gpu_count: int
    gpu_ready: int
    model_count: int
    model_loaded: int
    queue_depth: int
    active_requests: int


class GPUResponse(BaseModel):
    """GPU status response."""
    h: str
    idx: int
    name: str
    vram_total: int
    vram_avail: int
    vram_pct: float
    speed: float
    temp: int
    load: float
    status: int
    status_label: str
    ok: bool


class ModelResponse(BaseModel):
    """Model status response."""
    h: str
    name: str
    vram: int
    shard: bool
    on: list[str]
    refs: int
    loaded: bool


class ModelLoadRequest(BaseModel):
    """Model load request."""
    name: str
    gpus: list[int] | None = None


class ModelUnloadRequest(BaseModel):
    """Model unload request."""
    name: str


class ModelAddRequest(BaseModel):
    """Model registration request."""
    name: str
    vram: int
    shard: bool = True
    backend: str = ""
    context_len: int = 8192


class QueueResponse(BaseModel):
    """Queue status response."""
    h: str
    model_h: str
    gpu_h: str
    tok_in: int
    tok_out: int
    status: int
    status_label: str
    t_start: int
    priority: int
    latency_ms: int


class ParamUpdateRequest(BaseModel):
    """Parameter update request."""
    params: dict[str, Any]


class AlarmResponse(BaseModel):
    """Alarm response."""
    h: str
    tag: str
    priority: int
    message: str
    t_raised: int
    t_ack: int
    active: bool
    acknowledged: bool
    value: float


class StatsResponse(BaseModel):
    """Statistics response."""
    state: str
    uptime_sec: int
    gpu_count: int
    gpu_ready: int
    model_count: int
    model_loaded: int
    queue_depth: int
    active_requests: int
    total_requests: int
    completed_requests: int
    failed_requests: int
    requests_per_sec: float
    total_tokens_in: int
    total_tokens_out: int
    vram_total_mb: int
    vram_available_mb: int
    temp_max: float
    temp_avg: float


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    code: int = 400
