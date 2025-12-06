# Megazord Models Directory

This directory contains the model registry and downloaded model files.

## Structure

```
models/
├── registry.json         # Model registry (source of truth)
├── registry.schema.json  # JSON Schema for validation
├── README.md             # This file
└── <model-id>/           # Downloaded model files (created on download)
    ├── config.json
    ├── model.safetensors
    └── tokenizer.json
```

## Registry Format

The `registry.json` file defines available models following the `UDT_Model` schema:

```json
{
  "id": "llama-3-70b",
  "name": "Llama 3 70B",
  "family": "llama",
  "params": "70B",
  "vram_mb": 42000,
  "quant": "fp16",
  "shard": true,
  "context_len": 8192,
  "source": "meta-llama/Meta-Llama-3-70B",
  "path": null,
  "loaded": false
}
```

## ISA-95 Tags

Each model generates tags following the convention:
```
GPUCluster_MDL_{model_id}_State
GPUCluster_MDL_{model_id}_VRAM
GPUCluster_MDL_{model_id}_Loaded
```

## CLI Commands

```bash
# List available models
megazord model ls

# Add model to registry
megazord model add <id> <vram_mb> [--source <hf_id>] [--shard]

# Download model
megazord model pull <id>

# Load model onto GPU(s)
megazord model load <id> [--gpu 0] [--gpu 1]

# Unload model
megazord model unload <id>
```

## Hash Function

Model hashes are generated using:
```python
M = lambda x: hashlib.md5(f"mdl:{x}".encode()).hexdigest()[:8]
```

Example: `M("llama-3-70b")` → `"a1b2c3d4"`
