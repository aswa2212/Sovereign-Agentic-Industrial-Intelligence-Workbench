# Hardware Architecture & Tier Strategy

## 1. Development vs. Production Target

| Parameter | Dev Tier (Local Laptop) | Target Tier (Grand Finale Workstation) |
| :--- | :--- | :--- |
| **GPU** | NVIDIA GeForce RTX 4060 Laptop GPU | NVIDIA RTX 3090 / 4090 / RTX A5000 |
| **VRAM** | 8 GB GDDR6 | 24 GB – 48 GB GDDR6 / ECC |
| **Host RAM** | 16 GB DDR5 | 64 GB – 128 GB DDR5 |
| **Concurrency Strategy** | **Serial Model Swapping** (1 resident model) | **Quantized Colocation** (2–3 resident models) |
| **Swapping Strategy** | Ollama `keep_alive: "0m"` on context switch | Long `keep_alive`, continuous resident cache |
| **Embedding Engine** | Host CPU (torch / onnx / Ollama) | Dedicated GPU allocation |

## 2. Dev Tier VRAM Budgeting (8 GB Strict Ceiling)

- **Available VRAM:** ~7.8 GB usable.
- **Model Quantization:** Q4_K_M (4-bit quantization).
- **Resident Model Sizes:**
  - `deepseek-r1:7b` (Q4): ~4.7 GB VRAM
  - `qwen2.5-coder:3b` (Q4): ~2.2 GB VRAM
  - `qwen2.5-vl:3b` (Q4): ~3.1 GB VRAM
- **Safety Margin:** Operating a single model at a time leaves $\ge 3\text{ GB}$ VRAM free for the Windows DWM display subsystem and KV-cache expansion, preventing any paging to shared system RAM.
