"""
Megazord Core Tests
"""

import pytest
import asyncio

from megazord.core.params import Params, SysParams, ThermParams
from megazord.core.states import ST, RS, RM
from megazord.core.hash import H, M, R
from megazord.core.udts import UDT_GPU, UDT_Model, UDT_Request
from megazord.core.router import Router


class TestParams:
    """Test configuration parameters."""

    def test_default_params(self):
        params = Params()
        assert params.sys.name == "Megazord"
        assert params.sys.gpu_count_max == 16
        assert params.sys.api_port == 8420
        assert params.therm.throttle == 83

    def test_params_to_dict(self):
        params = Params()
        d = params.to_dict()
        assert "sys" in d
        assert "therm" in d
        assert d["sys"]["name"] == "Megazord"


class TestStates:
    """Test state enums."""

    def test_gpu_states(self):
        assert ST.OFF == 0
        assert ST.READY == 2
        assert ST.BUSY == 3
        assert ST(2).label == "Ready"

    def test_request_states(self):
        assert RS.QUEUED == 0
        assert RS.DONE == 2

    def test_router_modes(self):
        assert RM.SPEED == 0
        assert RM.VRAM == 1
        assert RM.ROUND_ROBIN == 2


class TestHash:
    """Test hash functions."""

    def test_gpu_hash(self):
        h1 = H(0)
        h2 = H(0)
        h3 = H(1)
        assert len(h1) == 8
        assert h1 == h2  # Deterministic
        assert h1 != h3  # Different input

    def test_model_hash(self):
        h1 = M("my-model")
        h2 = M("my-model")
        h3 = M("other-model")
        assert len(h1) == 8
        assert h1 == h2
        assert h1 != h3

    def test_request_hash(self):
        h1 = R("data")
        h2 = R("data")
        assert len(h1) == 8
        # Request hashes include timestamp, so should be different
        # (unless called in same ms with same uuid fragment)


class TestUDTs:
    """Test User Defined Types."""

    def test_gpu_udt(self):
        gpu = UDT_GPU(
            h="abc12345",
            idx=0,
            vram_total=24000,
            vram_avail=20000,
            temp=65,
            status=ST.READY,
        )
        assert gpu.ok is True
        assert gpu.vram_used == 4000
        assert gpu.vram_pct == pytest.approx(16.67, rel=0.1)

    def test_gpu_not_ok_when_throttle(self):
        gpu = UDT_GPU(
            h="abc12345",
            idx=0,
            vram_total=24000,
            vram_avail=20000,
            temp=85,
            status=ST.THROTTLE,
        )
        assert gpu.ok is False

    def test_model_udt(self):
        model = UDT_Model(
            h="def67890",
            name="test-model",
            vram=48000,
            shard=True,
        )
        assert model.loaded is False
        model.on = ["abc12345"]
        assert model.loaded is True

    def test_model_fits(self):
        model = UDT_Model(h="m1", name="test", vram=20000)
        gpu_big = UDT_GPU(h="g1", idx=0, vram_total=24000, vram_avail=22000)
        gpu_small = UDT_GPU(h="g2", idx=1, vram_total=16000, vram_avail=15000)

        assert model.fits(gpu_big) is True
        assert model.fits(gpu_small) is False

    def test_request_udt(self):
        req = UDT_Request(
            h="req12345",
            model_h="m1",
            status=RS.QUEUED,
        )
        assert req.latency_ms >= 0


class TestRouter:
    """Test router logic."""

    def test_router_init(self):
        router = Router()
        assert router.state.label == "Idle"

    def test_router_start_stop(self):
        router = Router()
        router.start()
        assert router.state.label == "Execute"
        router.stop()
        assert router.state.label == "Idle"

    def test_register_gpu(self):
        router = Router()
        gpu = UDT_GPU(h="g1", idx=0, vram_total=24000, vram_avail=22000, status=ST.READY)
        router.register_gpu(gpu)
        assert len(router.gpus) == 1
        assert router.get_gpu("g1") == gpu

    def test_register_model(self):
        router = Router()
        model = UDT_Model(h="m1", name="test", vram=20000)
        router.register_model(model)
        assert len(router.models) == 1
        assert router.get_model("m1") == model

    def test_find_gpus_single(self):
        router = Router()
        gpu = UDT_GPU(h="g1", idx=0, vram_total=24000, vram_avail=22000, speed=100, status=ST.READY, temp=50)
        model = UDT_Model(h="m1", name="test", vram=20000)

        router.register_gpu(gpu)
        router.register_model(model)

        gpus = router._find_gpus_for_model(model)
        assert gpus == ["g1"]

    def test_find_gpus_sharded(self):
        router = Router()
        gpu1 = UDT_GPU(h="g1", idx=0, vram_total=24000, vram_avail=22000, speed=100, status=ST.READY, temp=50)
        gpu2 = UDT_GPU(h="g2", idx=1, vram_total=24000, vram_avail=22000, speed=90, status=ST.READY, temp=50)
        model = UDT_Model(h="m1", name="test", vram=40000, shard=True)

        router.register_gpu(gpu1)
        router.register_gpu(gpu2)
        router.register_model(model)

        gpus = router._find_gpus_for_model(model)
        assert len(gpus) == 2
        assert "g1" in gpus and "g2" in gpus

    def test_stats(self):
        router = Router()
        router.start()
        stats = router.stats
        assert "state" in stats
        assert "gpu_count" in stats
        assert stats["state"] == "Execute"


@pytest.mark.asyncio
async def test_router_route():
    """Test async routing."""
    router = Router()
    gpu = UDT_GPU(h="g1", idx=0, vram_total=24000, vram_avail=22000, speed=100, status=ST.READY, temp=50)
    model = UDT_Model(h="m1", name="test", vram=20000)

    router.register_gpu(gpu)
    router.register_model(model)
    router.start()

    result = await router.route("m1", "Hello, world!")
    assert result.success is True
