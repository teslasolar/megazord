"""
Megazord Health Monitor
Continuous GPU and system health monitoring
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Callable, Awaitable

from megazord.core.states import ST
from megazord.core.udts import UDT_GPU

if TYPE_CHECKING:
    from megazord.megazord import Megazord

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Health monitoring loop for GPU and system status.

    Responsibilities:
    - Periodic GPU metric updates (temp, VRAM, load)
    - State machine transitions based on thermal thresholds
    - Database persistence
    - Alarm triggering
    """

    def __init__(
        self,
        megazord: "Megazord",
        interval_sec: int = 30,
    ):
        self.megazord = megazord
        self.interval = interval_sec
        self._running = False
        self._task: asyncio.Task | None = None

        # Callbacks
        self._on_gpu_update: list[Callable[[UDT_GPU], Awaitable[None]]] = []
        self._on_alarm: list[Callable[[str, str, float], Awaitable[None]]] = []

    def add_gpu_callback(self, callback: Callable[[UDT_GPU], Awaitable[None]]) -> None:
        """Add GPU update callback."""
        self._on_gpu_update.append(callback)

    def add_alarm_callback(self, callback: Callable[[str, str, float], Awaitable[None]]) -> None:
        """Add alarm callback (tag, message, value)."""
        self._on_alarm.append(callback)

    async def _check_gpu(self, gpu: UDT_GPU) -> UDT_GPU:
        """Check and update a single GPU."""
        z = self.megazord

        # Update metrics from scanner
        if z.scanner and z.scanner.available:
            gpu = z.scanner.update_metrics(gpu)

        # Thermal state machine
        prev_status = gpu.status
        therm = z.params.therm

        if gpu.temp >= therm.shutdown:
            gpu.status = ST.ERROR
            await self._trigger_alarm(
                f"GPU{gpu.idx}_Temp_Crit",
                f"GPU {gpu.idx} critical temperature: {gpu.temp}°C",
                gpu.temp,
            )
        elif gpu.temp >= therm.throttle:
            if gpu.status not in (ST.ERROR,):
                gpu.status = ST.THROTTLE
            await self._trigger_alarm(
                f"GPU{gpu.idx}_Temp_Throt",
                f"GPU {gpu.idx} throttling: {gpu.temp}°C",
                gpu.temp,
            )
        elif gpu.temp >= therm.warn:
            await self._trigger_alarm(
                f"GPU{gpu.idx}_Temp_Warn",
                f"GPU {gpu.idx} temperature warning: {gpu.temp}°C",
                gpu.temp,
            )
        elif gpu.status == ST.THROTTLE:
            # Clear throttle with hysteresis
            if gpu.temp < (therm.throttle - therm.hysteresis):
                gpu.status = ST.READY

        # VRAM low warning
        if gpu.vram_pct > 90:
            await self._trigger_alarm(
                f"GPU{gpu.idx}_VRAM_Low",
                f"GPU {gpu.idx} VRAM low: {gpu.vram_pct:.1f}% used",
                gpu.vram_pct,
            )

        # Log state changes
        if gpu.status != prev_status:
            logger.info(f"GPU {gpu.idx} state: {ST(prev_status).label} -> {ST(gpu.status).label}")

        # Trigger callbacks
        for callback in self._on_gpu_update:
            try:
                await callback(gpu)
            except Exception as e:
                logger.error(f"GPU callback error: {e}")

        return gpu

    async def _trigger_alarm(self, tag: str, message: str, value: float) -> None:
        """Trigger an alarm."""
        for callback in self._on_alarm:
            try:
                await callback(tag, message, value)
            except Exception as e:
                logger.error(f"Alarm callback error: {e}")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        logger.info(f"Health monitor started (interval: {self.interval}s)")

        while self._running:
            try:
                z = self.megazord

                # Update all GPUs
                for gpu in list(z.router.gpus):
                    updated = await self._check_gpu(gpu)
                    z.router.update_gpu(updated)

                    # Persist to database
                    if z.db:
                        await z.db.upsert_gpu(updated)

                # Process queue if possible
                if z.router.queue_depth > 0:
                    processed = await z.router.process_queue()
                    if processed > 0:
                        logger.debug(f"Processed {processed} queued requests")

                # Check queue depth alarm
                if z.router.queue_depth >= z.params.sys.queue_max * 0.8:
                    await self._trigger_alarm(
                        "RTR_Queue_Warn",
                        f"Queue depth warning: {z.router.queue_depth}/{z.params.sys.queue_max}",
                        z.router.queue_depth,
                    )

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(self.interval)

        logger.info("Health monitor stopped")

    def start(self) -> None:
        """Start the health monitor."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    def stop(self) -> None:
        """Stop the health monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    @property
    def running(self) -> bool:
        """Check if monitor is running."""
        return self._running
