"""
Megazord GPU Scanner
pynvml wrapper for GPU detection and monitoring
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable

from megazord.core.hash import H
from megazord.core.states import ST
from megazord.core.udts import UDT_GPU

logger = logging.getLogger(__name__)

# Try to import pynvml, provide mock for systems without NVIDIA GPUs
try:
    import pynvml

    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    pynvml = None  # type: ignore


@dataclass
class GPUInfo:
    """Raw GPU information from NVML."""

    index: int
    name: str
    uuid: str
    memory_total: int  # bytes
    memory_used: int   # bytes
    memory_free: int   # bytes
    temperature: int   # celsius
    utilization: int   # percent 0-100
    power_draw: float  # watts
    power_limit: float # watts


class GPUScanner:
    """
    GPU Scanner using NVIDIA Management Library (NVML).

    Handles:
    - GPU detection and enumeration
    - Real-time monitoring (VRAM, temp, load)
    - Benchmarking for speed estimation
    """

    def __init__(self, max_gpus: int = 16):
        self.max_gpus = max_gpus
        self._initialized = False
        self._gpu_count = 0

    def init(self) -> bool:
        """Initialize NVML library."""
        if not NVML_AVAILABLE:
            logger.warning("pynvml not available - GPU scanning disabled")
            return False

        try:
            pynvml.nvmlInit()
            self._gpu_count = min(pynvml.nvmlDeviceGetCount(), self.max_gpus)
            self._initialized = True
            logger.info(f"NVML initialized: {self._gpu_count} GPU(s) detected")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize NVML: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown NVML library."""
        if self._initialized and NVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._initialized = False

    @property
    def available(self) -> bool:
        """Check if GPU scanning is available."""
        return self._initialized and NVML_AVAILABLE

    @property
    def gpu_count(self) -> int:
        """Get number of detected GPUs."""
        return self._gpu_count

    def _get_handle(self, index: int):
        """Get NVML device handle."""
        if not self._initialized:
            raise RuntimeError("NVML not initialized")
        return pynvml.nvmlDeviceGetHandleByIndex(index)

    def get_gpu_info(self, index: int) -> GPUInfo | None:
        """Get detailed GPU information."""
        if not self.available or index >= self._gpu_count:
            return None

        try:
            handle = self._get_handle(index)

            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")

            uuid = pynvml.nvmlDeviceGetUUID(handle)
            if isinstance(uuid, bytes):
                uuid = uuid.decode("utf-8")

            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)

            try:
                temp = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )
            except Exception:
                temp = 0

            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                utilization = util.gpu
            except Exception:
                utilization = 0

            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
            except Exception:
                power_draw = 0.0
                power_limit = 0.0

            return GPUInfo(
                index=index,
                name=name,
                uuid=uuid,
                memory_total=memory.total,
                memory_used=memory.used,
                memory_free=memory.free,
                temperature=temp,
                utilization=utilization,
                power_draw=power_draw,
                power_limit=power_limit,
            )
        except Exception as e:
            logger.error(f"Failed to get GPU {index} info: {e}")
            return None

    def scan(self) -> list[UDT_GPU]:
        """Scan all GPUs and return UDT_GPU list."""
        gpus: list[UDT_GPU] = []

        if not self.available:
            return gpus

        for idx in range(self._gpu_count):
            info = self.get_gpu_info(idx)
            if info is None:
                continue

            gpu = UDT_GPU(
                h=H(info.uuid or idx),
                idx=idx,
                name=info.name,
                uuid=info.uuid,
                vram_total=info.memory_total // (1024 * 1024),  # bytes to MB
                vram_avail=info.memory_free // (1024 * 1024),
                speed=0.0,  # Will be set by benchmark
                temp=info.temperature,
                load=info.utilization / 100.0,
                status=ST.READY if info.temperature < 83 else ST.THROTTLE,
                t=int(time.time()),
            )
            gpus.append(gpu)

        return gpus

    def scan_one(self, index: int) -> UDT_GPU | None:
        """Scan a single GPU."""
        if not self.available or index >= self._gpu_count:
            return None

        info = self.get_gpu_info(index)
        if info is None:
            return None

        return UDT_GPU(
            h=H(info.uuid or index),
            idx=index,
            name=info.name,
            uuid=info.uuid,
            vram_total=info.memory_total // (1024 * 1024),
            vram_avail=info.memory_free // (1024 * 1024),
            speed=0.0,
            temp=info.temperature,
            load=info.utilization / 100.0,
            status=ST.READY if info.temperature < 83 else ST.THROTTLE,
            t=int(time.time()),
        )

    def update_metrics(self, gpu: UDT_GPU) -> UDT_GPU:
        """Update GPU metrics in place."""
        if not self.available or gpu.idx >= self._gpu_count:
            return gpu

        info = self.get_gpu_info(gpu.idx)
        if info is None:
            gpu.status = ST.ERROR
            return gpu

        gpu.vram_avail = info.memory_free // (1024 * 1024)
        gpu.temp = info.temperature
        gpu.load = info.utilization / 100.0
        gpu.t = int(time.time())

        # Update status based on temperature
        if info.temperature >= 90:
            gpu.status = ST.ERROR
        elif info.temperature >= 83:
            gpu.status = ST.THROTTLE
        elif gpu.status in (ST.THROTTLE, ST.ERROR):
            # Clear thermal state when temp drops (with hysteresis)
            if info.temperature < 78:  # 83 - 5
                gpu.status = ST.READY

        return gpu


class MockGPUScanner(GPUScanner):
    """
    Mock GPU scanner for testing without real GPUs.
    """

    def __init__(self, mock_gpus: list[dict] | None = None, max_gpus: int = 16):
        super().__init__(max_gpus)
        self._mock_gpus = mock_gpus or []

    def init(self) -> bool:
        """Initialize mock scanner."""
        self._initialized = True
        self._gpu_count = len(self._mock_gpus)
        logger.info(f"Mock GPU scanner: {self._gpu_count} GPU(s)")
        return True

    def shutdown(self) -> None:
        """Shutdown mock scanner."""
        self._initialized = False

    @property
    def available(self) -> bool:
        """Check if mock scanning is available."""
        return self._initialized

    def get_gpu_info(self, index: int) -> GPUInfo | None:
        """Get mock GPU information."""
        if index >= len(self._mock_gpus):
            return None

        mock = self._mock_gpus[index]
        return GPUInfo(
            index=index,
            name=mock.get("name", f"Mock GPU {index}"),
            uuid=mock.get("uuid", f"GPU-MOCK-{index:04d}"),
            memory_total=mock.get("vram", 24) * 1024 * 1024 * 1024,
            memory_used=mock.get("vram_used", 0) * 1024 * 1024 * 1024,
            memory_free=mock.get("vram", 24) * 1024 * 1024 * 1024 - mock.get("vram_used", 0) * 1024 * 1024 * 1024,
            temperature=mock.get("temp", 45),
            utilization=mock.get("load", 0),
            power_draw=mock.get("power", 100.0),
            power_limit=mock.get("power_limit", 350.0),
        )

    def add_mock_gpu(
        self,
        name: str = "Mock GPU",
        vram: int = 24,
        temp: int = 45,
        load: int = 0,
    ) -> None:
        """Add a mock GPU."""
        self._mock_gpus.append({
            "name": name,
            "uuid": f"GPU-MOCK-{len(self._mock_gpus):04d}",
            "vram": vram,
            "vram_used": 0,
            "temp": temp,
            "load": load,
        })
        self._gpu_count = len(self._mock_gpus)


def create_scanner(max_gpus: int = 16, mock: bool = False) -> GPUScanner:
    """Factory function to create appropriate GPU scanner."""
    if mock or not NVML_AVAILABLE:
        return MockGPUScanner(max_gpus=max_gpus)
    return GPUScanner(max_gpus=max_gpus)
