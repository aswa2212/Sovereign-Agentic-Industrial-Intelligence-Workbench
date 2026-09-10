# Model Management Policy & Local Inference Strategy

## 1. Zero Automatic Model Downloading
In strict compliance with air-gap and sovereign principles:
- **No models are downloaded automatically** by backend startup scripts or build commands.
- Weights are managed locally via Ollama or mounted offline storage.
- Model development, fine-tuning, and notebook experimentation are performed offline or in separate Google Colab environments (see `/experiments`).

## 2. Dev Tier vs. Target Tier Execution

### Dev Tier (RTX 4060 Laptop — 8 GB VRAM)
- **Constraint:** Attempting to load multiple $\ge 3\text{B}$ parameter models simultaneously will trigger CUDA Out-Of-Memory (OOM) errors or heavy Windows shared GPU memory paging (causing massive latency spikes).
- **Execution Pattern:** **Serial Model Swapping**.
  - The Local Model Manager maintains a single resident model in VRAM at any given time.
  - When switching from Task Routing to Deep Reasoning or Coding, Ollama's `keep_alive: 0` mechanism is invoked to immediately unload the prior model from VRAM before initializing the subsequent model.
  - Embeddings run on the host CPU, conserving the full 8 GB VRAM budget for generation.

### Target Tier (Workstation / Lab — 24–48 GB VRAM)
- **Execution Pattern:** **Quantized Colocation**.
  - Up to 3 models reside concurrently in VRAM.
  - Router, Reasoning, and Coding models are kept hot in memory for sub-50ms dispatch.

## 3. Model Configuration Reference
All active model references are managed declaratively in [`models/configs/model_tiers.yaml`](file:///d:/PROJECT%20WORKS/SIH%202026/models/configs/model_tiers.yaml). Core application code interacts only with the abstract `ModelHandle` interface, guaranteeing that model tags or parameter sizes can be swapped without modifying business logic.
