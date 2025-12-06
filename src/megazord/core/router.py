"""
Megazord Router - THE UNLOCK
Core inference routing logic

KEY INSIGHT: Cards ADD capacity, don't bottleneck on slowest
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from megazord.core.hash import R
from megazord.core.params import Params, RouterParams
from megazord.core.states import ST, RS, RM, RTR_ST
from megazord.core.udts import UDT_GPU, UDT_Model, UDT_Request

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Result from inference operation."""

    success: bool
    text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    gpu_hashes: list[str] = field(default_factory=list)
    error: str = ""


# Type alias for inference backend
InferenceBackend = Callable[[UDT_Model, list[str], str, dict[str, Any]], Awaitable[InferenceResult]]


class Router:
    """
    Megazord Router - The core routing engine.

    Handles:
    - Request routing to optimal GPU(s)
    - Model loading/unloading
    - Request queueing
    - Load balancing

    KEY INSIGHT: Cards ADD capacity, don't bottleneck on slowest.
    When sharding, total throughput is additive across GPUs.
    """

    def __init__(
        self,
        params: RouterParams | None = None,
        max_queue: int = 100,
    ):
        self.params = params or RouterParams()

        # State
        self.state: RTR_ST = RTR_ST.IDLE
        self._gpus: dict[str, UDT_GPU] = {}
        self._models: dict[str, UDT_Model] = {}
        self._queue: deque[UDT_Request] = deque(maxlen=max_queue)
        self._active: dict[str, UDT_Request] = {}
        self._rr_index: int = 0  # Round-robin counter

        # Stats
        self._stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "start_time": 0,
        }

        # Callbacks
        self._on_load: Callable[[UDT_Model, list[str]], Awaitable[bool]] | None = None
        self._on_unload: Callable[[UDT_Model], Awaitable[bool]] | None = None
        self._on_infer: InferenceBackend | None = None

        # Lock for thread safety
        self._lock = asyncio.Lock()

    # --- State Management ---

    def start(self) -> None:
        """Start the router."""
        if self.state == RTR_ST.IDLE:
            self.state = RTR_ST.STARTING
            self._stats["start_time"] = int(time.time())
            self.state = RTR_ST.EXECUTE
            logger.info("Router started")

    def stop(self) -> None:
        """Stop the router."""
        if self.state in (RTR_ST.EXECUTE, RTR_ST.HELD):
            self.state = RTR_ST.STOPPING
            # TODO: Wait for active requests to complete
            self.state = RTR_ST.IDLE
            logger.info("Router stopped")

    def hold(self) -> None:
        """Hold the router (pause accepting new requests)."""
        if self.state == RTR_ST.EXECUTE:
            self.state = RTR_ST.HELD
            logger.info("Router held")

    def resume(self) -> None:
        """Resume the router."""
        if self.state == RTR_ST.HELD:
            self.state = RTR_ST.EXECUTE
            logger.info("Router resumed")

    # --- GPU Management ---

    def register_gpu(self, gpu: UDT_GPU) -> None:
        """Register a GPU with the router."""
        self._gpus[gpu.h] = gpu
        logger.debug(f"GPU registered: {gpu.h} ({gpu.name})")

    def unregister_gpu(self, gpu_h: str) -> None:
        """Unregister a GPU."""
        if gpu_h in self._gpus:
            del self._gpus[gpu_h]
            logger.debug(f"GPU unregistered: {gpu_h}")

    def update_gpu(self, gpu: UDT_GPU) -> None:
        """Update GPU metrics."""
        if gpu.h in self._gpus:
            self._gpus[gpu.h] = gpu

    def get_gpu(self, h: str) -> UDT_GPU | None:
        """Get GPU by hash."""
        return self._gpus.get(h)

    @property
    def gpus(self) -> list[UDT_GPU]:
        """Get all registered GPUs."""
        return list(self._gpus.values())

    @property
    def available_gpus(self) -> list[UDT_GPU]:
        """Get GPUs that are ready for work."""
        return [g for g in self._gpus.values() if g.ok]

    # --- Model Management ---

    def register_model(self, model: UDT_Model) -> None:
        """Register a model."""
        self._models[model.h] = model
        logger.debug(f"Model registered: {model.h} ({model.name})")

    def unregister_model(self, model_h: str) -> None:
        """Unregister a model."""
        if model_h in self._models:
            del self._models[model_h]
            logger.debug(f"Model unregistered: {model_h}")

    def get_model(self, h: str) -> UDT_Model | None:
        """Get model by hash."""
        return self._models.get(h)

    def get_model_by_name(self, name: str) -> UDT_Model | None:
        """Get model by name."""
        for m in self._models.values():
            if m.name == name:
                return m
        return None

    @property
    def models(self) -> list[UDT_Model]:
        """Get all registered models."""
        return list(self._models.values())

    @property
    def loaded_models(self) -> list[UDT_Model]:
        """Get currently loaded models."""
        return [m for m in self._models.values() if m.loaded]

    # --- Callbacks ---

    def set_load_callback(
        self, callback: Callable[[UDT_Model, list[str]], Awaitable[bool]]
    ) -> None:
        """Set model load callback."""
        self._on_load = callback

    def set_unload_callback(
        self, callback: Callable[[UDT_Model], Awaitable[bool]]
    ) -> None:
        """Set model unload callback."""
        self._on_unload = callback

    def set_infer_callback(self, callback: InferenceBackend) -> None:
        """Set inference callback."""
        self._on_infer = callback

    # --- Core Routing Logic ---

    def _sort_gpus_by_mode(self, gpus: list[UDT_GPU]) -> list[UDT_GPU]:
        """Sort GPUs based on balance mode."""
        mode = RM(self.params.balance_mode)

        if mode == RM.SPEED:
            # Prefer fastest GPU
            return sorted(gpus, key=lambda g: -g.speed)
        elif mode == RM.VRAM:
            # Prefer GPU with most available VRAM
            return sorted(gpus, key=lambda g: -g.vram_avail)
        else:  # ROUND_ROBIN
            # Rotate through GPUs
            if not gpus:
                return []
            self._rr_index = (self._rr_index + 1) % len(gpus)
            return gpus[self._rr_index:] + gpus[:self._rr_index]

    def _find_gpus_for_model(self, model: UDT_Model) -> list[str] | None:
        """
        Find suitable GPU(s) for a model.

        THE UNLOCK: Cards ADD capacity, don't bottleneck on slowest.

        Returns:
            List of GPU hashes to use, or None if no suitable GPUs found.
        """
        avail = self._sort_gpus_by_mode(self.available_gpus)

        if not avail:
            return None

        # 1. Already loaded? Use existing GPUs
        if model.loaded:
            # Verify GPUs are still available
            if all(self._gpus.get(h, UDT_GPU("", 0, 0, 0)).ok for h in model.on):
                return model.on

        # 2. Single GPU fits? Use best available
        for g in avail:
            if model.fits(g):
                return [g.h]

        # 3. Shard across multiple (ADDITIVE throughput)
        if model.shard:
            selected: list[str] = []
            total_vram = 0
            for g in avail:
                selected.append(g.h)
                total_vram += g.vram_avail
                if total_vram >= model.vram:
                    return selected

        # 4. No suitable configuration found
        return None

    async def _load_model(self, model: UDT_Model, gpu_hashes: list[str]) -> bool:
        """Load model onto specified GPU(s)."""
        if self._on_load:
            success = await self._on_load(model, gpu_hashes)
            if success:
                model.on = gpu_hashes
                self._models[model.h] = model
                logger.info(f"Model {model.name} loaded on GPUs: {gpu_hashes}")
            return success
        else:
            # Mock loading
            model.on = gpu_hashes
            self._models[model.h] = model
            return True

    async def _unload_model(self, model: UDT_Model) -> bool:
        """Unload model from GPUs."""
        if model.refs > 0:
            logger.warning(f"Cannot unload {model.name}: {model.refs} active refs")
            return False

        if self._on_unload:
            success = await self._on_unload(model)
            if success:
                model.on = []
                self._models[model.h] = model
                logger.info(f"Model {model.name} unloaded")
            return success
        else:
            # Mock unloading
            model.on = []
            self._models[model.h] = model
            return True

    async def _infer(
        self,
        model: UDT_Model,
        gpu_hashes: list[str],
        prompt: str,
        params: dict[str, Any],
    ) -> InferenceResult:
        """Execute inference on GPU(s)."""
        if self._on_infer:
            return await self._on_infer(model, gpu_hashes, prompt, params)
        else:
            # Mock inference
            return InferenceResult(
                success=True,
                text=f"[Mock response to: {prompt[:50]}...]",
                tokens_in=len(prompt.split()),
                tokens_out=10,
                latency_ms=100,
                gpu_hashes=gpu_hashes,
            )

    async def route(
        self,
        model_h: str,
        prompt: str,
        params: dict[str, Any] | None = None,
        priority: int = 1,
    ) -> InferenceResult:
        """
        Route an inference request.

        This is THE UNLOCK - the core routing algorithm.

        Args:
            model_h: Model hash
            prompt: Input prompt
            params: Inference parameters
            priority: Request priority (0=low, 1=normal, 2=high)

        Returns:
            InferenceResult with response or error
        """
        params = params or {}

        # Check router state
        if self.state not in (RTR_ST.EXECUTE,):
            return InferenceResult(
                success=False,
                error=f"Router not accepting requests (state: {self.state.label})",
            )

        # Get model
        model = self._models.get(model_h)
        if not model:
            return InferenceResult(
                success=False,
                error=f"Model not found: {model_h}",
            )

        async with self._lock:
            # Find suitable GPUs
            gpu_hashes = self._find_gpus_for_model(model)

            if gpu_hashes is None:
                # Queue the request
                if len(self._queue) >= self._queue.maxlen:
                    return InferenceResult(
                        success=False,
                        error="Queue full",
                    )

                req = UDT_Request(
                    h=R(model_h),
                    model_h=model_h,
                    prompt=prompt,
                    priority=priority,
                )
                self._queue.append(req)
                logger.debug(f"Request {req.h} queued (no GPU available)")
                return InferenceResult(
                    success=False,
                    error="Request queued - no GPU available",
                )

            # Load model if needed
            if not model.loaded:
                if not await self._load_model(model, gpu_hashes):
                    return InferenceResult(
                        success=False,
                        error="Failed to load model",
                    )

            # Create request record
            req = UDT_Request(
                h=R(model_h),
                model_h=model_h,
                gpu_h=",".join(gpu_hashes),
                priority=priority,
                status=RS.RUNNING,
            )
            self._active[req.h] = req
            model.refs += 1
            self._stats["total_requests"] += 1

        try:
            # Execute inference
            result = await self._infer(model, gpu_hashes, prompt, params)

            # Update stats
            async with self._lock:
                model.refs -= 1
                req.status = RS.DONE if result.success else RS.ERROR
                req.t_end = int(time.time())
                req.tok_in = result.tokens_in
                req.tok_out = result.tokens_out

                if result.success:
                    self._stats["completed_requests"] += 1
                    self._stats["total_tokens_in"] += result.tokens_in
                    self._stats["total_tokens_out"] += result.tokens_out
                else:
                    self._stats["failed_requests"] += 1

                del self._active[req.h]

            return result

        except Exception as e:
            async with self._lock:
                model.refs -= 1
                if req.h in self._active:
                    del self._active[req.h]
                self._stats["failed_requests"] += 1

            logger.error(f"Inference error: {e}")
            return InferenceResult(
                success=False,
                error=str(e),
            )

    async def route_by_name(
        self,
        model_name: str,
        prompt: str,
        params: dict[str, Any] | None = None,
        priority: int = 1,
    ) -> InferenceResult:
        """Route request by model name instead of hash."""
        model = self.get_model_by_name(model_name)
        if not model:
            return InferenceResult(
                success=False,
                error=f"Model not found: {model_name}",
            )
        return await self.route(model.h, prompt, params, priority)

    # --- Queue Management ---

    @property
    def queue_depth(self) -> int:
        """Get current queue depth."""
        return len(self._queue)

    @property
    def active_requests(self) -> int:
        """Get number of active requests."""
        return len(self._active)

    async def process_queue(self) -> int:
        """Process queued requests. Returns number processed."""
        processed = 0

        while self._queue and self.state == RTR_ST.EXECUTE:
            req = self._queue[0]

            model = self._models.get(req.model_h)
            if not model:
                self._queue.popleft()
                continue

            gpu_hashes = self._find_gpus_for_model(model)
            if gpu_hashes is None:
                # Still no GPUs available
                break

            # Pop and process
            req = self._queue.popleft()
            result = await self.route(
                req.model_h,
                req.prompt,
                priority=req.priority,
            )

            if result.success:
                processed += 1

        return processed

    # --- Statistics ---

    @property
    def stats(self) -> dict[str, Any]:
        """Get router statistics."""
        uptime = int(time.time()) - self._stats["start_time"] if self._stats["start_time"] else 0
        req_per_sec = self._stats["total_requests"] / max(uptime, 1)

        return {
            "state": self.state.label,
            "uptime_sec": uptime,
            "gpu_count": len(self._gpus),
            "gpu_ready": len(self.available_gpus),
            "model_count": len(self._models),
            "model_loaded": len(self.loaded_models),
            "queue_depth": self.queue_depth,
            "active_requests": self.active_requests,
            "total_requests": self._stats["total_requests"],
            "completed_requests": self._stats["completed_requests"],
            "failed_requests": self._stats["failed_requests"],
            "requests_per_sec": round(req_per_sec, 2),
            "total_tokens_in": self._stats["total_tokens_in"],
            "total_tokens_out": self._stats["total_tokens_out"],
        }

    def get_vram_summary(self) -> dict[str, int]:
        """Get VRAM summary across all GPUs."""
        total = sum(g.vram_total for g in self._gpus.values())
        avail = sum(g.vram_avail for g in self._gpus.values())
        return {
            "total_mb": total,
            "available_mb": avail,
            "used_mb": total - avail,
        }

    def get_temp_summary(self) -> dict[str, float]:
        """Get temperature summary."""
        if not self._gpus:
            return {"max": 0, "avg": 0, "min": 0}

        temps = [g.temp for g in self._gpus.values()]
        return {
            "max": max(temps),
            "avg": sum(temps) / len(temps),
            "min": min(temps),
        }
