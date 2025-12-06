# Configuration Reference

All Megazord parameters are environment-configurable with sensible defaults.

## System Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `SYS_NAME` | Megazord | System name |
| `GPU_MAX` | 16 | Maximum GPUs to manage |
| `API_PORT` | 8420 | REST API port |
| `WS_PORT` | 8421 | WebSocket port |
| `DB_PATH` | ~/.megazord/state.db | SQLite database path |
| `HEALTH_INT` | 30 | Health check interval (seconds) |
| `QUEUE_MAX` | 100 | Maximum queue depth |
| `LOG_LVL` | 2 | Log level (0=ERR, 1=WARN, 2=INFO, 3=DEBUG) |

## Thermal Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `TEMP_WARN` | 75 | Warning temperature (°C) |
| `TEMP_THROT` | 83 | Throttle temperature (°C) |
| `TEMP_SHUT` | 90 | Shutdown temperature (°C) |
| `TEMP_HYST` | 5 | Hysteresis for state clearing (°C) |

## Router Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `RTR_TIMEOUT` | 300 | Request timeout (seconds) |
| `RTR_RETRY` | 3 | Maximum retry attempts |
| `RTR_PREFER` | true | Prefer already-loaded models |
| `RTR_BAL` | 0 | Balance mode (0=Speed, 1=VRAM, 2=RoundRobin) |

### Balance Modes

- **Speed (0)**: Route to fastest available GPU
- **VRAM (1)**: Route to GPU with most available memory
- **RoundRobin (2)**: Distribute evenly across GPUs

## Model Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `MDL_IDLE` | 30 | Unload after idle (minutes) |
| `MDL_CACHE` | 3 | Maximum cached models |
| `MDL_SHARD_MIN` | 2 | Minimum GPUs for sharding |

## Recipe Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `RCP_TOKENS` | 4096 | Default max tokens |
| `RCP_TEMP` | 0.7 | Default temperature |
| `RCP_TOP_P` | 0.9 | Default top_p |
| `RCP_CTX` | 8192 | Default context length |

## ISA-95 Physical Model

| Variable | Default | Description |
|----------|---------|-------------|
| `ENTERPRISE` | LocalCompute | Enterprise name |
| `SITE` | HomeLab | Site name |
| `AREA` | GPUCluster | Area name |

## Example Configuration

### Environment File

```bash
# .env
SYS_NAME=ProductionCluster
GPU_MAX=8
API_PORT=8420

TEMP_WARN=70
TEMP_THROT=80
TEMP_SHUT=85

RTR_BAL=0  # Speed priority
RTR_TIMEOUT=600

MDL_IDLE=60  # Unload after 1 hour
```

### Python Configuration

```python
from megazord import Megazord

Z = Megazord(
    gpu_max=8,
    api_port=8420,
    temp_throttle=80,
    temp_shutdown=85,
    health_interval=15,
    queue_max=200,
)
```

### CLI Configuration

```bash
# Set individual parameters
megazord config set sys.api_port 9000
megazord config set therm.throttle 80

# View current config
megazord config get
megazord config get sys.name
```

## Runtime Updates

Some parameters can be updated at runtime via API:

```bash
curl -X POST http://localhost:8420/params \
  -H "Content-Type: application/json" \
  -d '{"params": {"therm.warn": 72}}'
```

## Database Storage

Parameters are persisted to SQLite:

```sql
SELECT * FROM param;
-- k              | v
-- sys.api_port   | 8420
-- therm.throttle | 80
```
