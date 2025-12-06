# Megazord Documentation

**Generic Local LLM Cluster - ISA-88/95/101 Compliant**

> "industry 4.0 calls it ERP, I call it Megazord"

## Overview

Megazord is a local GPU cluster management system for running LLM inference at scale. It provides:

- **Multi-GPU Support**: Manage up to 16 GPUs with automatic load balancing
- **Model Sharding**: Split large models across multiple GPUs (THE UNLOCK)
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI endpoints
- **Real-time Monitoring**: Temperature, VRAM, and throughput tracking
- **ISA Compliance**: Industrial-grade state machines and alarm handling

## Quick Start

```bash
# Install
pip install megazord

# Initialize and scan GPUs
megazord init

# Register a model
megazord model add my-model 48000 --shard

# Start the API server
megazord serve --port 8420
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

## Key Concepts

### THE UNLOCK

The core insight: **Cards ADD capacity, don't bottleneck on slowest**.

When sharding a model across GPUs, throughput is additive. A 70B model split across 4x 24GB GPUs can achieve 4x the throughput of a single card.

### State Machines

Megazord uses PackML-compliant state machines for reliable operation:

- **GPU States**: OFF → STARTING → READY → BUSY → THROTTLE → ERROR
- **Router States**: IDLE → STARTING → EXECUTE → HELD → STOPPING

### Alarms

ISA-18.2 compliant alarm management with:

- Priority levels: CRITICAL, HIGH, MEDIUM, LOW
- Automatic thermal monitoring
- Acknowledgement and shelving

## API Reference

See the [API Documentation](./api/) for full endpoint details.

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/completions` | POST | OpenAI-compatible text completion |
| `/v1/chat/completions` | POST | OpenAI-compatible chat completion |
| `/health` | GET | System health check |
| `/gpus` | GET | List all GPUs |
| `/models` | GET | List all models |

## Python SDK

```python
from megazord import Megazord

# Initialize
Z = Megazord(gpu_max=8, api_port=8420)

# Scan GPUs
Z.scan()

# Register model
Z.m('my-model', vram=48000, shard=True)

# Run inference
result = await Z.r(M('my-model'), "Hello, world!")
```

## Configuration

All parameters are environment-configurable:

```bash
# System
SYS_NAME=Megazord
GPU_MAX=16
API_PORT=8420

# Thermal
TEMP_WARN=75
TEMP_THROT=83
TEMP_SHUT=90

# Router
RTR_TIMEOUT=300
RTR_BAL=0  # 0=Speed, 1=VRAM, 2=RoundRobin
```

## License

MIT License - "nothing leaves premises"
