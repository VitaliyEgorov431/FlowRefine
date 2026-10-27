"""Command-line interface for CPU experiments and offline replay."""

import argparse
import json
import hashlib
from pathlib import Path

from .backends import LlamaCPU, HFVisionCPU
from .compact import parse_object, to_scene
from .runner import (read_json, write_json, read_tasks, initialize_run,
                     generate, critique, repair)


def main():
    parser = argparse.ArgumentParser(prog="flowrefine")
    commands = parser.add_subparsers(dest="command", required=True)
    data = commands.add_parser("dataset", help="Write the predeclared public benchmark")
    data.add_argument("--output", default="data")
    draw = commands.add_parser("render", help="Render a full or compact Scene JSON")
    draw.add_argument("input")
    draw.add_argument("--output", required=True)
    run = commands.add_parser("run", help="Resume real model inference; no reference graph access")
    run.add_argument("--tasks", default="data/tasks.jsonl")
    run.add_argument("--split", default="development")
    run.add_argument("--limit", type=int)
    run.add_argument("--output", required=True)
    run.add_argument("--model", default="models/qwen2.5-3b-instruct-q4_k_m.gguf")
    run.add_argument("--vision-model")
    run.add_argument("--vision-projector")
    run.add_argument("--vision-backend", choices=["transformers", "mtmd"], default="mtmd")
    run.add_argument("--phase", choices=["generate", "critique", "repair", "all"], default="all")
    run.add_argument("--modes", default="B1,B2,B3")
    run.add_argument("--threads", type=int, default=4)
    run.add_argument("--max-tokens", type=int, default=900)
    run.add_argument("--vision-max-tokens", type=int, default=180)
    ask = commands.add_parser("ask", help="Generate and refine a new user process description")
    ask.add_argument("prompt", help="Process description in natural language")
    ask.add_argument("--output", required=True)
    ask.add_argument("--model", default="models/qwen2.5-3b-instruct-q4_k_m.gguf")
    ask.add_argument("--vision-model", default="models/SmolVLM-256M-Instruct-Q8_0.gguf")
    ask.add_argument("--vision-projector", default="models/mmproj-SmolVLM-256M-Instruct-f16.gguf")
    ask.add_argument("--threads", type=int, default=4)
    analysis = commands.add_parser("analyze", help="Read references only after inference")
    analysis.add_argument("run")
    analysis.add_argument("--references", default="data/references.json")
    analysis.add_argument("--output", required=True)
    gallery = commands.add_parser("gallery", help="Build a standalone offline results browser")
    gallery.add_argument("run")
    gallery.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "dataset":
        from .dataset import write_dataset
        write_dataset(Path(args.output))
    elif args.command == "render":
        from .rendering import render_scene
        from .validators import check_scene
        scene = to_scene(parse_object(Path(args.input).read_text(encoding="utf-8")))
        print(json.dumps(render_scene(scene, Path(args.output)), indent=2))
        print(json.dumps(check_scene(scene), indent=2))
    elif args.command == "run":
        tasks = read_tasks(args.tasks, args.split, args.limit)
        settings = {"text_model": str(Path(args.model).resolve()),
                    "vision_model": str(Path(args.vision_model).resolve()) if args.vision_model else None,
                    "vision_projector": str(Path(args.vision_projector).resolve()) if args.vision_projector else None,
                    "vision_backend": args.vision_backend, "threads": args.threads,
                    "max_tokens": args.max_tokens, "vision_max_tokens": args.vision_max_tokens,
                    "modes": args.modes, "format_repairs": 1, "temperature": 0.0,
                    "cached_visual_feedback": True}
        initialize_run(args.output, tasks, settings)
        if args.phase in ("generate", "all"):
            backend = LlamaCPU(args.model, threads=args.threads)
            try:
                generate(args.output, tasks, backend, args.max_tokens)
            finally:
                backend.close()
        if args.phase in ("critique", "all") and args.vision_model:
            if args.vision_backend == "mtmd":
                from .backends import MTMDVisionCPU
                if not args.vision_projector:
                    parser.error("--vision-projector required for MTMD")
                backend = MTMDVisionCPU(args.vision_model, args.vision_projector, args.threads)
            else:
                backend = HFVisionCPU(args.vision_model, args.threads)
            try:
                critique(args.output, tasks, backend, args.vision_max_tokens)
            finally:
                backend.close()
        if args.phase in ("repair", "all"):
            backend = LlamaCPU(args.model, threads=args.threads)
            try:
                repair(args.output, tasks, backend, args.max_tokens, tuple(args.modes.split(",")))
            finally:
                backend.close()
    elif args.command == "ask":
        # New descriptions need no reference graph or benchmark files.
        from .backends import MTMDVisionCPU
        from .gallery import build_gallery
        task = {"id": "custom_"+hashlib.sha256(args.prompt.encode()).hexdigest()[:12],
                "split": "custom", "family": "custom", "prompt": args.prompt}
        settings = {"text_model": str(Path(args.model).resolve()),
                    "vision_model": str(Path(args.vision_model).resolve()),
                    "vision_projector": str(Path(args.vision_projector).resolve()),
                    "threads": args.threads, "max_tokens": 900,
                    "vision_max_tokens": 180, "modes": "B1,B2,B3", "format_repairs": 1,
                    "temperature": 0.0, "cached_visual_feedback": True,
                    "interface": "custom_prompt"}
        initialize_run(args.output, [task], settings)
        text_backend = LlamaCPU(args.model, args.threads)
        try:
            generate(args.output, [task], text_backend)
        finally:
            text_backend.close()
        vision_backend = MTMDVisionCPU(args.vision_model, args.vision_projector, args.threads)
        try:
            critique(args.output, [task], vision_backend)
        finally:
            vision_backend.close()
        text_backend = LlamaCPU(args.model, args.threads)
        try:
            repair(args.output, [task], text_backend)
        finally:
            text_backend.close()
        gallery = build_gallery(Path(args.output), Path(args.output)/"index.html")
        print("Saved custom result:", gallery)
    elif args.command == "analyze":
        from .analysis import analyze_run
        analyze_run(Path(args.run), Path(args.references), Path(args.output))
    elif args.command == "gallery":
        from .gallery import build_gallery
        build_gallery(Path(args.run), Path(args.output))


if __name__ == "__main__":
    main()
