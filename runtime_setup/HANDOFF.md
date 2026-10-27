# CPU inference runtime handoff

## Runtime

The project `.venv` uses the installed Python 3.12.10 environment. Installed packages are `llama-cpp-python==0.3.36` (CPU wheel), `huggingface-hub==2.3.0`, `numpy==2.5.4`, and `Pillow==12.2.0`. No PyTorch, Transformers, CUDA, Ollama, or GPU is required. The llama.cpp Python wheel bundles `mtmd.dll`, so the same runtime supports both text and image inference.

The host reported 16 GiB RAM with about 2.7 GiB available at the initial probe. The tested 1.5B Qwen is about 1.12 GB on disk; SmolVLM and its projector total about 365 MB. Keep models loaded sequentially. Set `n_gpu_layers=0`; for VLM set `MTMDChatHandler(..., use_gpu=False)`.

## Installed model files

| File | Hugging Face repo | Revision | Size |
|---|---|---|---:|
| `models/qwen2.5-1.5b-instruct-q4_k_m.gguf` | [Qwen/Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) | `91cad51170dc346986eccefdc2dd33a9da36ead9` | 1,117,320,736 bytes |
| `models/SmolVLM-256M-Instruct-Q8_0.gguf` | [ggml-org/SmolVLM-256M-Instruct-GGUF](https://huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF) | `b9e4379657e1450d04d02eec8e345667265b0a00` | 175,054,528 bytes |
| `models/mmproj-SmolVLM-256M-Instruct-f16.gguf` | same repo | same revision | 190,031,616 bytes |
| `models/qwen2.5-3b-instruct-q4_k_m.gguf` | [Qwen/Qwen2.5-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF) | `7dabda4d13d513e3e842b20f0d435c732f172cbe` | 2,104,932,768 bytes |

Qwen2.5-1.5B and the SmolVLM repository declare Apache-2.0; Qwen2.5-3B declares `qwen-research`. Revisions were resolved from Hub metadata before downloading. Exact local SHA-256 hashes, sizes and per-repository licenses for all four files are in [configs/model_lock.json](../configs/model_lock.json). Install the pinned Python dependencies inside the existing project environment with:

```powershell
uv pip install --python .venv\Scripts\python.exe --no-cache --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r runtime_setup/requirements-cpu.txt
```

## Text smoke run

From the project root:

```powershell
.\.venv\Scripts\python.exe runtime_setup\smoke_text.py "Make a six-node flowchart for even/odd: start; input a number; decide whether divisible by 2; yes leads to display Even; no leads to display Odd; both lead to one end node."
```

`smoke_text.py` constructs `Llama(model_path=..., n_ctx=4096, n_threads=4, n_gpu_layers=0, verbose=False)` and calls `create_chat_completion(..., temperature=0, max_tokens=240, response_format={"type":"json_object"})`. The actual inference completed in 17.7 seconds after a 0.98 second model load (436 total tokens, 197 completion tokens). Output:

```json
{
  "nodes": [
    ["n1", "start", "Start", 0, 0],
    ["n2", "process", "Read input", 0, 1],
    ["n3", "decision", "Divisible by 2?", 0, 2],
    ["n4", "process", "Display Even", 1, 3],
    ["n5", "process", "Display Odd", 1, 4],
    ["n6", "end", "Done", 2, 5]
  ],
  "edges": [
    ["n1", "n2", "next"],
    ["n2", "n3", "next"],
    ["n3", "n4", "next"],
    ["n3", "n5", "next"],
    ["n4", "n6", "next"],
    ["n5", "n6", "next"]
  ]
}
```

The larger 3B model is also downloaded as an optional fallback. A few-shot pilot loaded in 1.6 seconds and generated 195 tokens in 36.9 seconds. It identified the six expected node labels and types, but inverted the yes/no branches and returned malformed edge arrays despite valid JSON parsing. At a 4096-token context, available host RAM dropped to about 0.7 GiB. The 3B file is available for the runner to select, with strict graph validation and sequential model loading recommended; this pilot did not show a reliable drop-in improvement over the tested 1.5B sample.

## Vision smoke run

Create a small diagram image and run the local image model:

```powershell
.\.venv\Scripts\python.exe runtime_setup\create_sample_image.py
.\.venv\Scripts\python.exe runtime_setup\smoke_vlm.py
```

The VLM script uses `MTMDChatHandler(clip_model_path=..., use_gpu=False)` with `n_gpu_layers=0`, then passes a PNG data URL in the user message's `image_url` block. On this host it loaded in 0.1 seconds, encoded each image pass in about 1.8 seconds, and completed in 4.6 seconds. Real output:

> START is connected with READ NUMBER which is then connected with both YES and NO branches. YES and NO both are connected with PRINT EVEN and PRINT ODD.

It read the text and split labels, but incorrectly said both branches connect to both outcomes. Treat this as proof the image path runs, not reliable flowchart semantics. The native mtmd library currently emits a few diagnostic lines even with `verbose=False`.
