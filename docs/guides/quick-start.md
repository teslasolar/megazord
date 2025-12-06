# Quick Start Guide

Get Megazord up and running in minutes.

## Prerequisites

- Python 3.10+
- NVIDIA GPU(s) with CUDA support
- `pynvml` compatible drivers

## Installation

```bash
# Install from PyPI
pip install megazord

# Or install from source
git clone https://github.com/teslasolar/megazord
cd megazord
pip install -e ".[dev]"
```

## Initialize

```bash
# Create database and scan GPUs
megazord init
```

This will:
1. Create `~/.megazord/state.db`
2. Detect all available NVIDIA GPUs
3. Register them with the system

## Register a Model

```bash
# Register a model with VRAM requirements
megazord model add llama-70b 48000 --shard

# Check registered models
megazord model ls
```

Parameters:
- `name`: Model identifier
- `vram`: Required VRAM in MB
- `--shard`: Allow splitting across GPUs

## Load Model

```bash
# Auto-select best GPU(s)
megazord model load llama-70b

# Or specify GPUs
megazord model load llama-70b --gpu 0 --gpu 1
```

## Start Server

```bash
# Start on default port 8420
megazord serve

# Custom port
megazord serve --port 9000
```

## Make Requests

### Using curl

```bash
# Text completion
curl http://localhost:8420/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-70b",
    "prompt": "Hello, world!",
    "max_tokens": 100
  }'

# Chat completion
curl http://localhost:8420/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-70b",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Using Python

```python
import httpx

client = httpx.Client(base_url="http://localhost:8420")

response = client.post("/v1/completions", json={
    "model": "llama-70b",
    "prompt": "Hello, world!",
    "max_tokens": 100
})

print(response.json()["choices"][0]["text"])
```

### Using OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8420/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="llama-70b",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## Monitor Status

```bash
# Check cluster status
megazord status

# View in browser
open http://localhost:8420
```

## Next Steps

- [Configuration Reference](./configuration.md)
- [API Documentation](../api/openapi.yaml)
- [Architecture Overview](./architecture.md)
