"""
Megazord FastAPI Server
OpenAI-compatible API with extensions
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from megazord.api.models import (
    CompletionRequest,
    CompletionResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    HealthResponse,
    GPUResponse,
    ModelResponse,
    ModelLoadRequest,
    ModelUnloadRequest,
    ModelAddRequest,
    QueueResponse,
    ParamUpdateRequest,
    AlarmResponse,
    StatsResponse,
    ErrorResponse,
    Choice,
    Message,
    Usage,
)
from megazord.core.hash import M

if TYPE_CHECKING:
    from megazord.megazord import Megazord

logger = logging.getLogger(__name__)

# Global reference to Megazord instance
_megazord: "Megazord | None" = None


def set_megazord(z: "Megazord") -> None:
    """Set the global Megazord instance."""
    global _megazord
    _megazord = z


def get_megazord() -> "Megazord":
    """Get the global Megazord instance."""
    if _megazord is None:
        raise RuntimeError("Megazord not initialized")
    return _megazord


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler."""
    logger.info("API server starting...")
    yield
    logger.info("API server shutting down...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Megazord API",
        description="Generic Local LLM Cluster - ISA-88/95/101 Compliant",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- OpenAI Compatible Endpoints ---

    @app.post("/v1/completions", response_model=CompletionResponse)
    async def create_completion(request: CompletionRequest) -> CompletionResponse:
        """OpenAI-compatible text completion endpoint."""
        z = get_megazord()

        # Handle prompt as string or list
        prompt = request.prompt if isinstance(request.prompt, str) else request.prompt[0]

        # Get model hash
        model = z.router.get_model_by_name(request.model)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {request.model}")

        # Route request
        result = await z.router.route(
            model.h,
            prompt,
            params={
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stop": request.stop,
            },
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        return CompletionResponse(
            id=f"cmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    text=result.text,
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=result.tokens_in,
                completion_tokens=result.tokens_out,
                total_tokens=result.tokens_in + result.tokens_out,
            ),
        )

    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def create_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
        """OpenAI-compatible chat completion endpoint."""
        z = get_megazord()

        # Build prompt from messages
        prompt = "\n".join(
            f"{m.role}: {m.content}" for m in request.messages
        )

        # Get model hash
        model = z.router.get_model_by_name(request.model)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {request.model}")

        # Route request
        result = await z.router.route(
            model.h,
            prompt,
            params={
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stop": request.stop,
            },
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content=result.text),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=result.tokens_in,
                completion_tokens=result.tokens_out,
                total_tokens=result.tokens_in + result.tokens_out,
            ),
        )

    # --- Megazord Endpoints ---

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint."""
        z = get_megazord()
        stats = z.router.stats

        return HealthResponse(
            ok=True,
            name=z.params.sys.name,
            version="0.1.0",
            uptime_sec=stats["uptime_sec"],
            gpu_count=stats["gpu_count"],
            gpu_ready=stats["gpu_ready"],
            model_count=stats["model_count"],
            model_loaded=stats["model_loaded"],
            queue_depth=stats["queue_depth"],
            active_requests=stats["active_requests"],
        )

    @app.get("/gpus", response_model=list[GPUResponse])
    async def list_gpus() -> list[GPUResponse]:
        """List all GPUs."""
        z = get_megazord()
        return [
            GPUResponse(**gpu.to_dict())
            for gpu in z.router.gpus
        ]

    @app.get("/gpus/{gpu_hash}", response_model=GPUResponse)
    async def get_gpu(gpu_hash: str) -> GPUResponse:
        """Get GPU by hash."""
        z = get_megazord()
        gpu = z.router.get_gpu(gpu_hash)
        if not gpu:
            raise HTTPException(status_code=404, detail=f"GPU not found: {gpu_hash}")
        return GPUResponse(**gpu.to_dict())

    @app.get("/models", response_model=list[ModelResponse])
    async def list_models() -> list[ModelResponse]:
        """List all models."""
        z = get_megazord()
        return [
            ModelResponse(**model.to_dict())
            for model in z.router.models
        ]

    @app.get("/models/{model_hash}", response_model=ModelResponse)
    async def get_model(model_hash: str) -> ModelResponse:
        """Get model by hash."""
        z = get_megazord()
        model = z.router.get_model(model_hash)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_hash}")
        return ModelResponse(**model.to_dict())

    @app.post("/model/add", response_model=ModelResponse)
    async def add_model(request: ModelAddRequest) -> ModelResponse:
        """Register a new model."""
        z = get_megazord()
        model = await z.add_model(
            name=request.name,
            vram=request.vram,
            shard=request.shard,
            backend=request.backend,
            context_len=request.context_len,
        )
        return ModelResponse(**model.to_dict())

    @app.post("/model/load", response_model=ModelResponse)
    async def load_model(request: ModelLoadRequest) -> ModelResponse:
        """Load a model onto GPU(s)."""
        z = get_megazord()
        model = z.router.get_model_by_name(request.name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {request.name}")

        success = await z.load_model(model.h, request.gpus)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to load model")

        model = z.router.get_model(model.h)
        return ModelResponse(**model.to_dict())

    @app.post("/model/unload", response_model=ModelResponse)
    async def unload_model(request: ModelUnloadRequest) -> ModelResponse:
        """Unload a model from GPU(s)."""
        z = get_megazord()
        model = z.router.get_model_by_name(request.name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {request.name}")

        success = await z.unload_model(model.h)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to unload model")

        model = z.router.get_model(model.h)
        return ModelResponse(**model.to_dict())

    @app.get("/queue", response_model=list[QueueResponse])
    async def get_queue() -> list[QueueResponse]:
        """Get request queue."""
        z = get_megazord()
        queue = await z.db.get_queue() if z.db else []
        return [
            QueueResponse(**req.to_dict())
            for req in queue
        ]

    @app.get("/stats", response_model=StatsResponse)
    async def get_stats() -> StatsResponse:
        """Get detailed statistics."""
        z = get_megazord()
        stats = z.router.stats
        vram = z.router.get_vram_summary()
        temp = z.router.get_temp_summary()

        return StatsResponse(
            **stats,
            vram_total_mb=vram["total_mb"],
            vram_available_mb=vram["available_mb"],
            temp_max=temp["max"],
            temp_avg=temp["avg"],
        )

    @app.get("/params")
    async def get_params() -> dict[str, Any]:
        """Get current configuration parameters."""
        z = get_megazord()
        return z.params.to_dict()

    @app.post("/params")
    async def update_params(request: ParamUpdateRequest) -> dict[str, Any]:
        """Update configuration parameters."""
        z = get_megazord()
        for key, value in request.params.items():
            if z.db:
                await z.db.set_param(key, value)
        return z.params.to_dict()

    @app.get("/alarms", response_model=list[AlarmResponse])
    async def get_alarms() -> list[AlarmResponse]:
        """Get active alarms."""
        z = get_megazord()
        alarms = await z.db.get_active_alarms() if z.db else []
        return [
            AlarmResponse(**alarm.to_dict())
            for alarm in alarms
        ]

    @app.post("/alarms/{alarm_hash}/ack")
    async def ack_alarm(alarm_hash: str) -> dict[str, str]:
        """Acknowledge an alarm."""
        z = get_megazord()
        if z.db:
            await z.db.ack_alarm(alarm_hash)
        return {"status": "acknowledged"}

    @app.post("/alarms/{alarm_hash}/clear")
    async def clear_alarm(alarm_hash: str) -> dict[str, str]:
        """Clear an alarm."""
        z = get_megazord()
        if z.db:
            await z.db.clear_alarm(alarm_hash)
        return {"status": "cleared"}

    # --- Control Endpoints ---

    @app.post("/control/start")
    async def control_start() -> dict[str, str]:
        """Start the router."""
        z = get_megazord()
        z.router.start()
        return {"status": "started"}

    @app.post("/control/stop")
    async def control_stop() -> dict[str, str]:
        """Stop the router."""
        z = get_megazord()
        z.router.stop()
        return {"status": "stopped"}

    @app.post("/control/hold")
    async def control_hold() -> dict[str, str]:
        """Hold the router."""
        z = get_megazord()
        z.router.hold()
        return {"status": "held"}

    @app.post("/control/resume")
    async def control_resume() -> dict[str, str]:
        """Resume the router."""
        z = get_megazord()
        z.router.resume()
        return {"status": "resumed"}

    # --- WebSocket for Real-time Updates ---

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates."""
        await websocket.accept()
        z = get_megazord()

        try:
            while True:
                # Send stats every second
                stats = z.router.stats
                vram = z.router.get_vram_summary()
                temp = z.router.get_temp_summary()

                await websocket.send_json({
                    "type": "stats",
                    "data": {
                        **stats,
                        "vram_total_mb": vram["total_mb"],
                        "vram_available_mb": vram["available_mb"],
                        "temp_max": temp["max"],
                        "temp_avg": temp["avg"],
                        "gpus": [g.to_dict() for g in z.router.gpus],
                    },
                })

                await asyncio.sleep(1)
        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")

    return app


async def run_server(z: "Megazord", host: str = "0.0.0.0", port: int = 8420):
    """Run the API server."""
    import uvicorn

    set_megazord(z)
    app = create_app()

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()
