# Megazord

```
╔═══════════════════════════════════════════════════════════════╗
║  Generic Local LLM Cluster | ISA-88/95/101 Compliant          ║
║  "industry 4.0 calls it ERP, I call it Megazord"              ║
╚═══════════════════════════════════════════════════════════════╝
```

## Overview

Megazord is a local GPU cluster management system for running LLM inference at scale. Designed with industrial automation standards (ISA-88/95/101) for reliability and observability.

### Key Features

- **Multi-GPU Support**: Manage up to 16 GPUs with automatic load balancing
- **Model Sharding**: Split large models across multiple GPUs (THE UNLOCK)
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI endpoints
- **Real-time Monitoring**: Temperature, VRAM, and throughput tracking
- **PackML State Machines**: Industrial-grade process control
- **ISA-18.2 Alarms**: Thermal and operational alarms with acknowledgement

## Quick Start

```bash
# Install
pip install megazord

# Initialize and scan GPUs
megazord init

# Register a model (48GB VRAM, shardable)
megazord model add llama-70b 48000 --shard

# Load model onto available GPUs
megazord model load llama-70b

# Start the API server
megazord serve --port 8420
```

## Python SDK

```python
from megazord import Megazord, M

# Initialize
Z = Megazord(gpu_max=8, api_port=8420)
await Z.init()

# Scan GPUs
Z.scan()

# Register and infer
Z.m('my-model', vram=48000, shard=True)
result = await Z.r(M('my-model'), "Hello, world!")
print(result.text)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/completions` | POST | OpenAI-compatible text completion |
| `/v1/chat/completions` | POST | OpenAI-compatible chat completion |
| `/health` | GET | System health check |
| `/gpus` | GET | List all GPUs |
| `/models` | GET | List all models |
| `/model/load` | POST | Load model onto GPU(s) |
| `/model/unload` | POST | Unload model |
| `/queue` | GET | View request queue |
| `/stats` | GET | Detailed statistics |
| `/alarms` | GET | Active alarms |
| `/ws` | WS | Real-time updates |

## THE UNLOCK

The core insight: **Cards ADD capacity, don't bottleneck on slowest**.

```python
def route(self, model_h: str, prompt: str):
    """
    KEY INSIGHT: Cards ADD capacity, don't bottleneck on slowest
    """
    m = self.models[model_h]
    avail = sorted([g for g in self.gpus if g.ok], key=lambda x: -x.speed)

    # 1. Already loaded? Use it
    if m.loaded:
        return self._infer(m.on, prompt)

    # 2. Single card fits? Use fastest available
    for g in avail:
        if m.fits(g):
            self._load(m, [g.h])
            return self._infer([g.h], prompt)

    # 3. Shard across multiple (ADDITIVE)
    if m.shard:
        sel, tot = [], 0
        for g in avail:
            sel.append(g.h)
            tot += g.vram_avail
            if tot >= m.vram:
                self._load(m, sel)
                return self._infer(sel, prompt)

    # 4. Queue
    return self._queue(model_h, prompt)
```

## Architecture

```
ENTERPRISE: LocalCompute
└── SITE: HomeLab
    └── AREA: GPUCluster
        └── PROCESS CELL: Megazord
            ├── UNIT: Inference (INF)
            │   ├── EM: Router (RTR)
            │   └── EM: Scheduler (SCH)
            ├── UNIT: Models (MDL)
            │   ├── EM: Loader (LDR)
            │   └── EM: Sharder (SHR)
            └── CONTROL MODULES:
                └── GPU[0..N-1]
```

## Configuration

Environment variables:

```bash
# System
SYS_NAME=Megazord
GPU_MAX=16
API_PORT=8420
WS_PORT=8421
DB_PATH=~/.megazord/state.db
HEALTH_INT=30
QUEUE_MAX=100

# Thermal
TEMP_WARN=75
TEMP_THROT=83
TEMP_SHUT=90
TEMP_HYST=5

# Router
RTR_TIMEOUT=300
RTR_RETRY=3
RTR_BAL=0  # 0=Speed, 1=VRAM, 2=RoundRobin
```

## CLI Commands

```bash
megazord init                     # Initialize database, scan GPUs
megazord gpu ls                   # List GPUs
megazord gpu add 0 1 2 3          # Add specific GPUs
megazord gpu bench                # Benchmark GPUs

megazord model add <name> <vram> [--shard]
megazord model load <name>
megazord model unload <name>
megazord model ls

megazord config get [key]
megazord config set <key> <value>

megazord serve [--port PORT]
megazord status
```

## Dashboard

The built-in React dashboard provides real-time monitoring:

- GPU array visualization
- Temperature and VRAM monitoring
- Model status and loading
- Request queue management
- Alarm acknowledgement

Access at `http://localhost:8420` when the server is running.

## State Machines

### GPU States (PackML)

```
     ┌────────────────────────────────┐
     ▼                                │
┌─────────┐  scan   ┌──────────┐     │
│ OFFLINE │────────▶│ STARTING │     │
└─────────┘         └────┬─────┘     │
     ▲                   │ ready     │
     │ error             ▼           │
┌─────────┐ throt  ┌─────────┐      │
│  ERROR  │◀───────│  READY  │──────┘ reset
└─────────┘        └────┬────┘
     ▲                  │ req
     │ timeout          ▼
     │             ┌────────┐
     └─────────────│  BUSY  │
                   └────────┘
```

### Router States

```
┌────────┐ Start  ┌──────────┐
│  IDLE  │───────▶│ STARTING │
└────────┘        └────┬─────┘
     ▲                 │ ready
     │ Stop            ▼
┌──────────┐      ┌─────────┐
│ STOPPING │◀─────│ EXECUTE │⇄ HELD
└──────────┘ Stop └─────────┘
```

## Alarms

ISA-18.2 compliant alarm classes:

| Priority | Color | Action |
|----------|-------|--------|
| CRIT (1) | Red | Auto-shutdown |
| HIGH (2) | Orange | Alert + pause |
| MED (3) | Yellow | Warning |
| LOW (4) | Cyan | Info |

Built-in alarms:
- `GPU_Temp_Crit`: Temperature >= 90°C
- `GPU_Temp_Throt`: Temperature >= 83°C
- `GPU_Temp_Warn`: Temperature >= 75°C
- `GPU_VRAM_Low`: VRAM usage > 90%
- `RTR_Queue_Full`: Queue at capacity
- `RTR_Timeout`: Request timeout

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/

# Build UI
cd ui && pnpm install && pnpm run build
```

## License

MIT License

---

```
"nothing leaves premises"
                    — Phoenix
```
