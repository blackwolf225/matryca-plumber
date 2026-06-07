### Problem / motivation

Lower the barrier to entry for Tier-1 Gardener setup by recommending a local LLM model matched to host hardware — preventing memory saturation during background indexing on 8–16 GB machines.

### Scope clarification (v1.9.5 baseline)

**Already exists (different purpose):**
- `probe_cpu_topology()` in `src/agent/process_priority.py` — CPU affinity for daemon sandbox, not LLM sizing
- Static model copy in `PreFlightModal.tsx` / `README.md` — recommends Gemma 4-E4b, not dynamic tiers

**This issue tracks:** dynamic RAM/VRAM/arch probing + tiered recommendation matrix + CLI output.

### Proposed solution

1. Probe host: total RAM, GPU VRAM (if any), Apple Silicon vs x86
2. Hardcoded recommendation matrix, e.g.:
   - Tier A: >16 GB Apple Silicon → Llama-3-8B class
   - Tier B: 8 GB → Phi-3-mini / Qwen2-small
3. Display in CLI (`matryca …`) and/or Sovereign UI first boot with `ollama run <suggested_model>`

### Out of scope

- Replacing `probe_cpu_topology` (daemon scheduling)
- Cloud model routing

### Related

Parent epic: #20 (independent DX track)
