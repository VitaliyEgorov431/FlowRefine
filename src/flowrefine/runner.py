"""Resumable experiments; references are read ONLY by the analysis module."""

import datetime
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

from .compact import from_scene, parse_object, to_scene
from .prompts import PROMPT_VERSION, generation_messages, critique_messages, repair_messages
from .rendering import render_scene
from .validators import check_scene


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_tasks(path, split=None, limit=None):
    tasks = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    if split:
        tasks = [task for task in tasks if task["split"] == split]
    if limit is not None:
        tasks = tasks[:limit]
    for task in tasks:
        if set(task)-{"id", "split", "family", "prompt", "provenance"}:
            raise ValueError("Task file contains undeclared fields; references must be separate")
        if not task["id"] or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in task["id"]):
            raise ValueError("Unsafe task id")
    if len({t["id"] for t in tasks}) != len(tasks):
        raise ValueError("Duplicate task id")
    return tasks


def initialize_run(root, tasks, settings):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = root/"manifest.json"
    task_bytes = json.dumps(tasks, sort_keys=True, ensure_ascii=False).encode()
    immutable = {"tasks_sha256": hashlib.sha256(task_bytes).hexdigest(),
                 "settings": settings, "prompt_version": PROMPT_VERSION}
    frozen_names = {"prompts.py", "compact.py", "schema.py", "rendering.py",
                    "validators.py", "runner.py", "backends.py"}
    source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in Path(__file__).parent.glob("*.py") if p.name in frozen_names}
    if manifest.exists():
        old = read_json(manifest)
        if any(old.get(k) != v for k, v in immutable.items()):
            raise ValueError("Run settings changed. Use a new output directory, do not overwrite a run.")
        if any(old.get("source_sha256", {}).get(k) != v for k, v in source.items()):
            raise ValueError("Inference/core source changed. Use a new run directory to preserve provenance.")
    else:
        write_json(manifest, {**immutable, "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              "python": sys.version, "platform": platform.platform(),
                              "source_sha256": source,
                              "reference_access": "analysis phase only", "provenance": "real_model_inference"})
        write_json(root/"tasks_public.json", tasks)


def _log_call(folder, role, index, messages, response, image=None):
    record = {"role": role, "messages": messages, "response": response,
              "reference_access": False}
    if image:
        path = Path(image)
        record["image"] = str(path)
        record["image_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(folder/f"call_{role}_{index}.json", record)


def _model_scene(folder, messages, backend, role, max_tokens, max_repairs=1):
    errors = []
    for attempt in range(max_repairs+1):
        cache = Path(folder)/f"call_{role}_{attempt}.json"
        if cache.exists():
            response = read_json(cache)["response"]
            if "text" not in response:
                raise RuntimeError("Previous inference call failed. Preserve this run; retry in a new run directory.")
        else:
            started = time.perf_counter()
            try:
                response = backend.complete(messages, max_tokens=max_tokens, json_output=True)
            except Exception as error:
                response = {"elapsed_seconds": time.perf_counter()-started,
                            "error": f"{type(error).__name__}: {error}", "usage": {}}
                _log_call(folder, role, attempt, messages, response)
                raise
            _log_call(folder, role, attempt, messages, response)
        try:
            return to_scene(parse_object(response["text"])), errors
        except (ValueError, TypeError, KeyError) as error:
            errors.append(str(error))
            if attempt < max_repairs:
                messages = messages + [
                    {"role": "assistant", "content": response["text"]},
                    {"role": "user", "content": "The JSON could not be rendered: " + str(error)
                     + ". Return a valid complete compact flowchart JSON only."}]
    return None, errors


def _save_scene(folder, scene, errors):
    if scene is not None:
        write_json(folder/"scene.json", scene)
        write_json(folder/"program_feedback.json", check_scene(scene))
        render_scene(scene, folder/"chart")
    # Completion marker is committed only after every artifact has been written.
    write_json(folder/"status.json", {"valid": scene is not None, "parse_errors": errors})


def generate(root, tasks, backend, max_tokens=900):
    for task in tasks:
        folder = Path(root)/task["id"]/"B0"
        if (folder/"status.json").exists():
            continue
        print("GENERATE", task["id"], flush=True)
        scene, errors = _model_scene(folder, generation_messages(task), backend, "generate", max_tokens)
        _save_scene(folder, scene, errors)


def critique(root, tasks, backend, max_tokens=180):
    for task in tasks:
        parent = Path(root)/task["id"]
        folder, image = parent/"visual", parent/"B0"/"chart.png"
        status_path = folder/"status.json"
        if status_path.exists():
            previous = read_json(status_path)
            if previous.get("available") or previous.get("reason") == "initial_scene_invalid":
                continue
        if not image.exists():
            initial_status = parent/"B0"/"status.json"
            if initial_status.exists() and not read_json(initial_status).get("valid"):
                write_json(folder/"status.json", {"available": False, "reason": "initial_scene_invalid"})
            continue
        print("CRITIQUE", task["id"], flush=True)
        messages = critique_messages(task)
        index = len(list(folder.glob("call_visual_*.json")))
        started = time.perf_counter()
        try:
            response = backend.critique(messages, image, max_tokens=max_tokens)
            _log_call(folder, "visual", index, messages, response, image)
            write_json(folder/"feedback.json", {"text": response["text"]})
            write_json(folder/"status.json", {"available": True})
        except Exception as error:
            _log_call(folder, "visual", index, messages,
                      {"elapsed_seconds": time.perf_counter()-started, "usage": {},
                       "error": f"{type(error).__name__}: {error}"}, image)
            write_json(folder/"status.json", {"available": False, "reason": "runtime_error",
                                              "error": f"{type(error).__name__}: {error}"})
            raise


def repair(root, tasks, backend, max_tokens=900, modes=("B1", "B2", "B3")):
    for task in tasks:
        parent = Path(root)/task["id"]
        for mode in modes:
            if mode not in ("B1", "B2", "B3"):
                raise ValueError("Invalid repair mode")
            folder = parent/mode
            if (folder/"status.json").exists():
                continue
            initial_path = parent/"B0"/"scene.json"
            if not initial_path.exists():
                write_json(folder/"status.json", {"valid": False, "reason": "initial_scene_invalid"})
                continue
            visual_path = parent/"visual"/"feedback.json"
            if mode in ("B2", "B3") and not visual_path.exists():
                # Missing VLM is not a bad-model result. Leave mode unexecuted.
                continue
            scene = read_json(initial_path)
            program = read_json(parent/"B0"/"program_feedback.json") if mode in ("B1", "B3") else None
            visual = read_json(visual_path)["text"] if mode in ("B2", "B3") else None
            messages = repair_messages(task, from_scene(scene), program, visual)
            print("REPAIR", mode, task["id"], flush=True)
            result, errors = _model_scene(folder, messages, backend, "repair", max_tokens)
            _save_scene(folder, result, errors)
