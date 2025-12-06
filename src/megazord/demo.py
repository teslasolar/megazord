"""
Megazord Demo Mode
Generate mock data for testing and demonstrations
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from megazord.core.hash import H, M, R
from megazord.core.states import ST, RS
from megazord.core.udts import UDT_GPU, UDT_Model, UDT_Request, UDT_Alarm
from megazord.core.router import InferenceResult


# GPU name templates
GPU_NAMES = [
    "NVIDIA RTX 4090",
    "NVIDIA RTX 4080",
    "NVIDIA RTX 3090 Ti",
    "NVIDIA A100 80GB",
    "NVIDIA A6000",
    "NVIDIA RTX A5000",
    "NVIDIA Tesla V100",
    "NVIDIA RTX 3080",
]

# Model templates
MODEL_TEMPLATES = [
    {"name": "llama-70b", "vram": 48000, "shard": True, "speed": 45},
    {"name": "llama-13b", "vram": 12000, "shard": True, "speed": 120},
    {"name": "mistral-7b", "vram": 8000, "shard": False, "speed": 180},
    {"name": "codellama-34b", "vram": 24000, "shard": True, "speed": 75},
    {"name": "mixtral-8x7b", "vram": 96000, "shard": True, "speed": 35},
    {"name": "phi-2", "vram": 4000, "shard": False, "speed": 250},
]


def generate_mock_gpus(count: int = 4) -> list[UDT_GPU]:
    """Generate mock GPU data."""
    gpus = []
    for i in range(count):
        name = GPU_NAMES[i % len(GPU_NAMES)]
        vram_total = random.choice([24000, 48000, 80000, 16000])
        vram_used = random.randint(0, int(vram_total * 0.7))

        gpu = UDT_GPU(
            h=H(f"mock-{i}"),
            idx=i,
            name=name,
            uuid=f"GPU-MOCK-{i:04d}-{random.randint(1000, 9999)}",
            vram_total=vram_total,
            vram_avail=vram_total - vram_used,
            speed=random.uniform(80, 200),
            temp=random.randint(45, 78),
            load=random.uniform(0, 0.8),
            status=ST.READY if random.random() > 0.1 else ST.BUSY,
            t=int(time.time()),
        )
        gpus.append(gpu)
    return gpus


def generate_mock_models(count: int = 3) -> list[UDT_Model]:
    """Generate mock model data."""
    models = []
    templates = random.sample(MODEL_TEMPLATES, min(count, len(MODEL_TEMPLATES)))

    for template in templates:
        model = UDT_Model(
            h=M(template["name"]),
            name=template["name"],
            vram=template["vram"],
            shard=template["shard"],
            on=[],
            refs=0,
            context_len=8192,
        )
        # Randomly load some models
        if random.random() > 0.5:
            model.on = [H(f"mock-{random.randint(0, 3)}")]
            model.refs = random.randint(0, 5)
        models.append(model)
    return models


def generate_mock_requests(count: int = 5) -> list[UDT_Request]:
    """Generate mock request data."""
    requests = []
    for i in range(count):
        status = random.choice([RS.QUEUED, RS.RUNNING, RS.DONE])
        req = UDT_Request(
            h=R(f"mock-{i}"),
            model_h=M(random.choice(MODEL_TEMPLATES)["name"]),
            gpu_h=H(f"mock-{random.randint(0, 3)}") if status != RS.QUEUED else "",
            tok_in=random.randint(50, 500),
            tok_out=random.randint(100, 2000) if status == RS.DONE else 0,
            status=status,
            t_start=int(time.time()) - random.randint(0, 300),
            t_end=int(time.time()) if status == RS.DONE else 0,
            priority=random.randint(0, 2),
        )
        requests.append(req)
    return requests


def generate_mock_alarms(count: int = 2) -> list[UDT_Alarm]:
    """Generate mock alarm data."""
    alarm_templates = [
        ("GPU0_Temp_Warn", 3, "GPU 0 temperature warning: 78°C", 78.0),
        ("GPU2_VRAM_Low", 3, "GPU 2 VRAM low: 92% used", 92.0),
        ("RTR_Queue_Warn", 3, "Queue depth warning: 85 requests", 85.0),
        ("GPU1_Temp_Throt", 2, "GPU 1 throttling: 84°C", 84.0),
    ]

    alarms = []
    for i in range(min(count, len(alarm_templates))):
        tag, priority, message, value = alarm_templates[i]
        alarm = UDT_Alarm(
            h=f"alm{random.randint(10000, 99999)}",
            tag=tag,
            priority=priority,
            message=message,
            t_raised=int(time.time()) - random.randint(60, 3600),
            value=value,
        )
        alarms.append(alarm)
    return alarms


def generate_mock_stats(gpus: list[UDT_GPU], models: list[UDT_Model]) -> dict[str, Any]:
    """Generate mock statistics."""
    vram_total = sum(g.vram_total for g in gpus)
    vram_avail = sum(g.vram_avail for g in gpus)
    temps = [g.temp for g in gpus] if gpus else [0]

    return {
        "state": "Execute",
        "uptime_sec": random.randint(3600, 86400),
        "gpu_count": len(gpus),
        "gpu_ready": len([g for g in gpus if g.ok]),
        "model_count": len(models),
        "model_loaded": len([m for m in models if m.loaded]),
        "queue_depth": random.randint(0, 20),
        "active_requests": random.randint(0, 8),
        "total_requests": random.randint(1000, 50000),
        "completed_requests": random.randint(900, 49000),
        "failed_requests": random.randint(10, 500),
        "requests_per_sec": round(random.uniform(1, 15), 2),
        "total_tokens_in": random.randint(100000, 5000000),
        "total_tokens_out": random.randint(500000, 10000000),
        "vram_total_mb": vram_total,
        "vram_available_mb": vram_avail,
        "temp_max": max(temps),
        "temp_avg": sum(temps) / len(temps),
    }


class DemoMode:
    """
    Demo mode controller for generating and managing mock data.

    Usage:
        demo = DemoMode(gpu_count=4, model_count=3)
        demo.start()

        # Get mock data
        gpus = demo.gpus
        stats = demo.stats
    """

    def __init__(
        self,
        gpu_count: int = 4,
        model_count: int = 3,
        update_interval: float = 2.0,
    ):
        self.gpu_count = gpu_count
        self.model_count = model_count
        self.update_interval = update_interval

        self._gpus: list[UDT_GPU] = []
        self._models: list[UDT_Model] = []
        self._requests: list[UDT_Request] = []
        self._alarms: list[UDT_Alarm] = []
        self._running = False
        self._task: asyncio.Task | None = None

        # Initialize data
        self._regenerate()

    def _regenerate(self) -> None:
        """Regenerate all mock data."""
        self._gpus = generate_mock_gpus(self.gpu_count)
        self._models = generate_mock_models(self.model_count)
        self._requests = generate_mock_requests(5)
        self._alarms = generate_mock_alarms(2)

    def _update_metrics(self) -> None:
        """Update GPU metrics with slight variations."""
        for gpu in self._gpus:
            # Vary temperature
            gpu.temp = max(40, min(85, gpu.temp + random.randint(-2, 2)))

            # Vary load
            gpu.load = max(0, min(1, gpu.load + random.uniform(-0.1, 0.1)))

            # Vary VRAM (small changes)
            delta = random.randint(-500, 500)
            gpu.vram_avail = max(1000, min(gpu.vram_total, gpu.vram_avail + delta))

            # Update status based on temp
            if gpu.temp >= 83:
                gpu.status = ST.THROTTLE
            elif gpu.status == ST.THROTTLE and gpu.temp < 78:
                gpu.status = ST.READY

            gpu.t = int(time.time())

    async def _update_loop(self) -> None:
        """Background update loop."""
        while self._running:
            self._update_metrics()
            await asyncio.sleep(self.update_interval)

    def start(self) -> None:
        """Start background updates."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._update_loop())

    def stop(self) -> None:
        """Stop background updates."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    @property
    def gpus(self) -> list[UDT_GPU]:
        """Get current GPU data."""
        return self._gpus

    @property
    def models(self) -> list[UDT_Model]:
        """Get current model data."""
        return self._models

    @property
    def requests(self) -> list[UDT_Request]:
        """Get current request data."""
        return self._requests

    @property
    def alarms(self) -> list[UDT_Alarm]:
        """Get current alarm data."""
        return self._alarms

    @property
    def stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return generate_mock_stats(self._gpus, self._models)

    async def mock_inference(self, model_name: str, prompt: str) -> InferenceResult:
        """Simulate inference request."""
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate latency

        return InferenceResult(
            success=True,
            text=f"[Demo Mode] This is a mock response to: {prompt[:50]}...",
            tokens_in=len(prompt.split()),
            tokens_out=random.randint(50, 200),
            latency_ms=random.randint(100, 500),
            gpu_hashes=[self._gpus[0].h] if self._gpus else [],
        )


# Export for convenience
def create_demo_data() -> dict[str, Any]:
    """Create a complete set of demo data."""
    gpus = generate_mock_gpus(4)
    models = generate_mock_models(3)

    return {
        "gpus": [g.to_dict() for g in gpus],
        "models": [m.to_dict() for m in models],
        "requests": [r.to_dict() for r in generate_mock_requests(5)],
        "alarms": [a.to_dict() for a in generate_mock_alarms(2)],
        "stats": generate_mock_stats(gpus, models),
    }
