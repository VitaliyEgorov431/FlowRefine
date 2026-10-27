import base64
import time
from pathlib import Path

from llama_cpp import Llama
from llama_cpp.llama_chat_format import MTMDChatHandler


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "SmolVLM-256M-Instruct-Q8_0.gguf"
PROJECTOR = ROOT / "models" / "mmproj-SmolVLM-256M-Instruct-f16.gguf"
IMAGE = ROOT / "runtime_setup" / "sample_flowchart.png"

if not IMAGE.exists():
    raise SystemExit("Create the sample image first: python runtime_setup/create_sample_image.py")

image_data = base64.b64encode(IMAGE.read_bytes()).decode("ascii")
data_url = f"data:image/png;base64,{image_data}"
handler = MTMDChatHandler(clip_model_path=str(PROJECTOR), verbose=False, use_gpu=False)
started = time.time()
llm = Llama(
    model_path=str(MODEL),
    chat_handler=handler,
    n_ctx=2048,
    n_threads=4,
    n_gpu_layers=0,
    verbose=False,
)
print(f"loaded_sec={time.time() - started:.1f}", flush=True)
result = llm.create_chat_completion(
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Read this flowchart. List its node labels and explain the yes and no branches.",
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ],
    temperature=0,
    max_tokens=160,
)
print(result["choices"][0]["message"]["content"])
print(f"total_sec={time.time() - started:.1f}")
