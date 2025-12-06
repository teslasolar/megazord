"""
Megazord - Main Controller Class
Generic Local LLM Cluster - ISA-88/95/101 Compliant

"industry 4.0 calls it ERP, I call it Megazord"
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Awaitable

from megazord.core.params import Params
from megazord.core.hash import H, M
from megazord.core.states import ST
from megazord.core.udts import UDT_GPU, UDT_Model
from megazord.core.schema import Database, init_db, close_db
from megazord.core.gpu import GPUScanner, MockGPUScanner, create_scanner
from megazord.core.router import Router, InferenceResult
from megazord.monitor.health import HealthMonitor
from megazord.monitor.alarms import AlarmManager

logger = logging.getLogger(__name__)


class Megazord:
    """
    Megazord - Local LLM Cluster Controller

    Main entry point for the system. Coordinates:
    - GPU scanning and management
    - Model loading/unloading
    - Request routing
    - Health monitoring
    - Alarm management
    - API serving

    Usage:
        >>> from megazord import Megazord
        >>> Z = Megazord(gpu_max=8, api_port=8420)
        >>> Z.scan()  # Detect GPUs
        >>> Z.m('my-model', vram=48000, shard=True)  # Register model
        >>> await Z.serve()  # Start API server
    """

    def __init__(
        self,
        gpu_max: int | None = None,
        api_port: int | None = None,
        ws_port: int | None = None,
        db_path: str | None = None,
        temp_throttle: int | None = None,
        temp_shutdown: int | None = None,
        health_interval: int | None = None,
        queue_max: int | None = None,
        mock_gpus: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize Megazord.

        Args:
            gpu_max: Maximum number of GPUs to manage
            api_port: REST API port
            ws_port: WebSocket port
            db_path: SQLite database path
            temp_throttle: Throttle temperature threshold
            temp_shutdown: Shutdown temperature threshold
            health_interval: Health check interval in seconds
            queue_max: Maximum queue depth
            mock_gpus: Use mock GPU scanner (for testing)
        """
        # Initialize parameters
        self.params = Params()

        # Override from constructor args
        if gpu_max is not None:
            self.params.sys.gpu_count_max = gpu_max
        if api_port is not None:
            self.params.sys.api_port = api_port
        if ws_port is not None:
            self.params.sys.ws_port = ws_port
        if db_path is not None:
            self.params.sys.db_path = db_path
        if temp_throttle is not None:
            self.params.therm.throttle = temp_throttle
        if temp_shutdown is not None:
            self.params.therm.shutdown = temp_shutdown
        if health_interval is not None:
            self.params.sys.health_interval_sec = health_interval
        if queue_max is not None:
            self.params.sys.queue_max = queue_max

        # Initialize components
        self.scanner: GPUScanner | None = None
        self.router = Router(
            params=self.params.router,
            max_queue=self.params.sys.queue_max,
        )
        self.monitor: HealthMonitor | None = None
        self.alarms: AlarmManager | None = None
        self.db: Database | None = None

        # State
        self._mock_gpus = mock_gpus
        self._initialized = False
        self._serving = False

        logger.info(f"Megazord '{self.params.sys.name}' initialized")

    async def init(self) -> bool:
        """
        Initialize the system.

        - Opens database
        - Initializes GPU scanner
        - Sets up monitoring
        - Loads persisted state
        """
        if self._initialized:
            return True

        try:
            # Initialize database
            db_path = self.params.sys.db_path_resolved
            self.db = await init_db(db_path)
            logger.info(f"Database initialized: {db_path}")

            # Initialize GPU scanner
            self.scanner = create_scanner(
                max_gpus=self.params.sys.gpu_count_max,
                mock=self._mock_gpus,
            )
            self.scanner.init()

            # Initialize alarm manager
            self.alarms = AlarmManager(db=self.db)

            # Initialize health monitor
            self.monitor = HealthMonitor(
                megazord=self,
                interval_sec=self.params.sys.health_interval_sec,
            )

            # Wire up alarm callbacks
            async def on_alarm(tag: str, message: str, value: float):
                if self.alarms:
                    await self.alarms.raise_alarm(tag, message, value=value)

            self.monitor.add_alarm_callback(on_alarm)

            # Load persisted state
            await self._load_state()

            self._initialized = True
            logger.info("Megazord initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def _load_state(self) -> None:
        """Load persisted state from database."""
        if not self.db:
            return

        # Load GPUs
        gpus = await self.db.get_all_gpus()
        for gpu in gpus:
            self.router.register_gpu(gpu)

        # Load models
        models = await self.db.get_all_models()
        for model in models:
            self.router.register_model(model)

        logger.info(f"Loaded {len(gpus)} GPUs and {len(models)} models from database")

    async def shutdown(self) -> None:
        """Shutdown the system gracefully."""
        logger.info("Shutting down Megazord...")

        # Stop monitoring
        if self.monitor:
            self.monitor.stop()

        # Stop router
        self.router.stop()

        # Shutdown scanner
        if self.scanner:
            self.scanner.shutdown()

        # Close database
        await close_db()

        self._initialized = False
        logger.info("Megazord shutdown complete")

    # --- GPU Management ---

    def scan(self) -> list[UDT_GPU]:
        """
        Scan for GPUs and register them.

        Returns list of detected GPUs.
        """
        if not self.scanner:
            self.scanner = create_scanner(
                max_gpus=self.params.sys.gpu_count_max,
                mock=self._mock_gpus,
            )
            self.scanner.init()

        gpus = self.scanner.scan()

        for gpu in gpus:
            self.router.register_gpu(gpu)
            if self.db:
                asyncio.create_task(self.db.upsert_gpu(gpu))

        logger.info(f"Scanned {len(gpus)} GPUs")
        return gpus

    def g(self, idx: int) -> UDT_GPU | None:
        """
        Register a specific GPU by index.

        Shorthand for manual GPU registration.
        """
        if not self.scanner:
            return None

        gpu = self.scanner.scan_one(idx)
        if gpu:
            self.router.register_gpu(gpu)
            if self.db:
                asyncio.create_task(self.db.upsert_gpu(gpu))

        return gpu

    async def add_mock_gpu(
        self,
        name: str = "Mock GPU",
        vram: int = 24,
        temp: int = 45,
        speed: float = 100.0,
    ) -> UDT_GPU:
        """Add a mock GPU for testing."""
        if not isinstance(self.scanner, MockGPUScanner):
            self.scanner = MockGPUScanner()
            self.scanner.init()

        self.scanner.add_mock_gpu(name=name, vram=vram, temp=temp)
        gpus = self.scanner.scan()
        gpu = gpus[-1]  # Get the newly added GPU
        gpu.speed = speed

        self.router.register_gpu(gpu)
        if self.db:
            await self.db.upsert_gpu(gpu)

        return gpu

    # --- Model Management ---

    async def add_model(
        self,
        name: str,
        vram: int,
        shard: bool = True,
        backend: str = "",
        context_len: int = 8192,
    ) -> UDT_Model:
        """
        Register a model.

        Args:
            name: Model name/path
            vram: VRAM required in MB
            shard: Whether model can be sharded across GPUs
            backend: Inference backend
            context_len: Maximum context length
        """
        model = UDT_Model(
            h=M(name),
            name=name,
            vram=vram,
            shard=shard,
            backend=backend,
            context_len=context_len,
        )

        self.router.register_model(model)
        if self.db:
            await self.db.upsert_model(model)

        logger.info(f"Model registered: {name} ({vram}MB, shard={shard})")
        return model

    def m(self, name: str, vram: int, shard: bool = True) -> UDT_Model:
        """
        Shorthand model registration.

        Returns model and schedules DB persistence.
        """
        model = UDT_Model(
            h=M(name),
            name=name,
            vram=vram,
            shard=shard,
        )

        self.router.register_model(model)
        if self.db:
            asyncio.create_task(self.db.upsert_model(model))

        return model

    async def load_model(
        self,
        model_h: str,
        gpu_indices: list[int] | None = None,
    ) -> bool:
        """
        Load a model onto GPU(s).

        If gpu_indices is None, automatically selects best GPU(s).
        """
        model = self.router.get_model(model_h)
        if not model:
            logger.error(f"Model not found: {model_h}")
            return False

        # Determine GPUs to use
        if gpu_indices:
            gpu_hashes = [
                g.h for g in self.router.gpus
                if g.idx in gpu_indices
            ]
        else:
            gpu_hashes = self.router._find_gpus_for_model(model)

        if not gpu_hashes:
            logger.error(f"No suitable GPUs for model {model.name}")
            return False

        # Load the model
        return await self.router._load_model(model, gpu_hashes)

    async def unload_model(self, model_h: str) -> bool:
        """Unload a model from GPU(s)."""
        model = self.router.get_model(model_h)
        if not model:
            logger.error(f"Model not found: {model_h}")
            return False

        return await self.router._unload_model(model)

    # --- Inference ---

    async def r(
        self,
        model_h: str,
        prompt: str,
        **params: Any,
    ) -> InferenceResult:
        """
        Shorthand inference request.

        Args:
            model_h: Model hash
            prompt: Input prompt
            **params: Inference parameters
        """
        return await self.router.route(model_h, prompt, params)

    async def infer(
        self,
        model_name: str,
        prompt: str,
        **params: Any,
    ) -> InferenceResult:
        """
        Inference by model name.

        Args:
            model_name: Model name
            prompt: Input prompt
            **params: Inference parameters
        """
        return await self.router.route_by_name(model_name, prompt, params)

    # --- Server ---

    async def serve(
        self,
        host: str = "0.0.0.0",
        port: int | None = None,
    ) -> None:
        """
        Start the API server.

        Args:
            host: Bind host
            port: Bind port (uses params.sys.api_port if None)
        """
        from megazord.api.server import run_server

        if not self._initialized:
            await self.init()

        # Start router
        self.router.start()

        # Start monitoring
        if self.monitor:
            self.monitor.start()

        port = port or self.params.sys.api_port
        self._serving = True

        logger.info(f"Starting Megazord API on {host}:{port}")
        await run_server(self, host=host, port=port)

    # --- Status ---

    @property
    def status(self) -> dict[str, Any]:
        """Get system status."""
        return {
            "name": self.params.sys.name,
            "initialized": self._initialized,
            "serving": self._serving,
            "router": self.router.stats,
            "vram": self.router.get_vram_summary(),
            "temp": self.router.get_temp_summary(),
            "alarms": self.alarms.active_count if self.alarms else 0,
        }

    def __repr__(self) -> str:
        return (
            f"Megazord("
            f"name='{self.params.sys.name}', "
            f"gpus={len(self.router.gpus)}, "
            f"models={len(self.router.models)}"
            f")"
        )
