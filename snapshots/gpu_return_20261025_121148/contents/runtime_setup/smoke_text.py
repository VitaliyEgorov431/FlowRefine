import argparse
import json
from pathlib import Path

from llama_cpp import Llama


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
SYSTEM = (
    'Return ONLY one JSON object with exact schema '
    '{"nodes":[["id","start|process|decision|end","label",column,row]],'
    '"edges":[["source_id","target_id","edge_label"]]}. '
    "Each node MUST have exactly 5 items; type is start/process/decision/end; "
    "column is integer 0..2, row integer 0..7. Each edge has exactly 3 strings. "
    "Use unique string IDs. No markdown or extra keys. Example: "
    '{"nodes":[["n1","start","Start",1,0],["n2","process","Read input",1,1],'
    '["n3","end","Done",1,2]],"edges":[["n1","n2","next"],["n2","n3","next"]]}'
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local CPU Qwen JSON generator")
    parser.add_argument("prompt", help="A short flowchart description")
    parser.add_argument("--max-tokens", type=int, default=240)
    args = parser.parse_args()

    llm = Llama(
        model_path=str(MODEL),
        n_ctx=4096,
        n_threads=4,
        n_gpu_layers=0,
        verbose=False,
    )
    result = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": args.prompt},
        ],
        temperature=0,
        max_tokens=args.max_tokens,
        response_format={"type": "json_object"},
    )
    content = result["choices"][0]["message"]["content"]
    # Fail visibly on malformed output instead of silently accepting it.
    json.loads(content)
    print(content)


if __name__ == "__main__":
    main()
