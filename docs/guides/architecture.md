# Architecture Overview

Megazord follows ISA-88/95/101 standards for industrial automation systems.

## ISA-95 Physical Model

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

### Levels

| Level | Name | Function |
|-------|------|----------|
| L0 | Inference | Direct GPU operations |
| L1 | Sensing | Temperature, VRAM, load monitoring |
| L2 | Control | Router, scheduler, state machines |
| L3 | MES | Request queue, batch records |
| L4 | Business | API, dashboard, reporting |

## Core Components

### Router (THE UNLOCK)

The router implements the key insight: **Cards ADD capacity, don't bottleneck on slowest**.

```python
def route(self, model_h: str, prompt: str):
    m = self.models[model_h]
    avail = sorted([g for g in self.gpus if g.ok], key=lambda x: -x.speed)

    # 1. Already loaded? Use it
    if m.loaded:
        return self._infer(m.on, prompt)

    # 2. Single card fits? Use fastest
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

### State Machines (PackML)

#### GPU States

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

#### Router States

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

### Database Schema

```sql
-- GPU State
CREATE TABLE gpu (
    h       TEXT PRIMARY KEY,  -- 8-char hash
    idx     INTEGER NOT NULL,  -- Device index
    name    TEXT,
    vram_t  INTEGER,           -- Total VRAM (MB)
    vram_a  INTEGER,           -- Available VRAM (MB)
    speed   REAL,              -- Tokens/sec
    temp    INTEGER,           -- Temperature (°C)
    load    REAL,              -- Load (0.0-1.0)
    status  INTEGER,           -- State enum
    t       INTEGER            -- Last update (unix)
);

-- Model Registry
CREATE TABLE model (
    h       TEXT PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    vram    INTEGER NOT NULL,
    shard   INTEGER DEFAULT 1,
    on_gpus TEXT DEFAULT '',   -- CSV of GPU hashes
    refs    INTEGER DEFAULT 0
);

-- Request Log
CREATE TABLE request (
    h       TEXT PRIMARY KEY,
    mdl_h   TEXT NOT NULL,
    gpu_h   TEXT DEFAULT '',
    tok_in  INTEGER,
    tok_out INTEGER,
    status  INTEGER,
    t_start INTEGER,
    t_end   INTEGER,
    prio    INTEGER DEFAULT 1
);

-- Alarms
CREATE TABLE alarm (
    h        TEXT PRIMARY KEY,
    tag      TEXT NOT NULL,
    priority INTEGER,
    message  TEXT,
    t_raised INTEGER,
    t_ack    INTEGER DEFAULT 0,
    t_clear  INTEGER DEFAULT 0
);
```

## Data Flow

```
Request → API → Router → GPU Selection → Load Model → Inference → Response
                  ↓
              Queue (if busy)
                  ↓
              Monitor → Alarms
```

## Hash Functions

All entities use deterministic 8-character MD5 hashes:

```python
H = lambda x: hashlib.md5(f"gpu:{x}".encode()).hexdigest()[:8]
M = lambda x: hashlib.md5(f"mdl:{x}".encode()).hexdigest()[:8]
R = lambda x: hashlib.md5(f"req:{time.time()}:{x}".encode()).hexdigest()[:8]
```

## Tag Naming Convention

ISA-95 compliant tag structure:

```
{AREA}_{UNIT}_{MODULE}_{DESC}_{SUFFIX}

Examples:
GPUCluster_INF_GPU00_Temp        → GPU 0 temperature
GPUCluster_INF_RTR_Queue_Depth   → Router queue depth
GPUCluster_MDL_LDR_Active        → Active model loads
```

## Alarm System (ISA-18.2)

| Class | Priority | Color | Action |
|-------|----------|-------|--------|
| CRIT | 1 | Red | Auto-shutdown |
| HIGH | 2 | Orange | Alert + pause |
| MED | 3 | Yellow | Warning |
| LOW | 4 | Cyan | Info |

Default alarms:
- `GPU_Temp_Crit`: >= 90°C
- `GPU_Temp_Throt`: >= 83°C
- `GPU_Temp_Warn`: >= 75°C
- `GPU_VRAM_Low`: > 90% used
- `RTR_Queue_Full`: Queue at capacity
- `RTR_Timeout`: Request timeout
