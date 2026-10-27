"""Post-test exploratory controls using frozen B0 outputs, never references."""
import argparse
import copy
import datetime
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

from .backends import LlamaCPU, package_version
from .compact import from_scene
from .prompts import SCENE_FORMAT
from .runner import read_json, write_json, _model_scene, _save_scene, _log_call

VERSION = "followup-controls-v1"
MODES = {"C0": "Edit saved B0 against original request without external feedback",
         "L3": "Edit only B0 grid positions using saved programmatic and visual feedback"}
POSITION_SCHEMA = {"type": "object", "additionalProperties": False,
    "properties": {"positions": {"type": "array", "minItems": 2, "maxItems": 12,
        "items": {"type": "array", "items": [
            {"type": "integer", "minimum": 0, "maximum": 11},
            {"type": "integer", "minimum": 0, "maximum": 2},
            {"type": "integer", "minimum": 0, "maximum": 7}],
            "minItems": 3, "maxItems": 3}}}, "required": ["positions"]}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes():
    names = ("followup.py", "backends.py", "runner.py", "compact.py", "schema.py",
             "rendering.py", "validators.py", "prompts.py")
    return {name: sha256(Path(__file__).with_name(name)) for name in names}


def initialize_followup(baseline, output, limit=None):
    """Freeze inputs before any inference, reject changed inputs or settings on resume."""
    baseline, output = Path(baseline).resolve(), Path(output).resolve()
    if baseline == output or baseline in output.parents or output in baseline.parents:
        raise ValueError("Baseline and output must be separate non-nested directories")
    manifest = read_json(baseline / "manifest.json")
    tasks = read_json(baseline / "tasks_public.json")
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        tasks = tasks[:limit]
    if not tasks:
        raise ValueError("No saved tasks")
    ids = [task["id"] for task in tasks]
    if len(set(ids)) != len(ids) or any(not ident or any(c not in
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in ident) for ident in ids):
        raise ValueError("Unsafe or duplicate task id")
    for task in tasks:
        if set(task) - {"id", "split", "family", "prompt", "provenance"}:
            raise ValueError("Only public task fields allowed")
    # Hash only immutable inputs, never analysis/references or incidental lock files.
    required = [Path("manifest.json"), Path("tasks_public.json")]
    for task in tasks:
        required += [Path(task["id"]) / rel for rel in (
            "B0/scene.json", "B0/program_feedback.json", "B0/status.json",
            "visual/feedback.json", "visual/status.json")]
    hashes = {str(rel).replace("\\", "/"): sha256(baseline / rel) for rel in required}
    for task in tasks:
        if not read_json(baseline / task["id"] / "B0/status.json").get("valid"):
            raise ValueError("Saved B0 must be valid for every selected task")
        if not read_json(baseline / task["id"] / "visual/status.json").get("available"):
            raise ValueError("Saved visual feedback required for L3")
    settings = copy.deepcopy(manifest["settings"])
    model = Path(settings["text_model"])
    if not model.is_file():
        raise ValueError("Frozen text model not found locally: " + str(model))
    settings.update({"modes": "C0,L3", "context": 4096, "seed": 241024,
                     "top_p": 1.0, "format_repairs": 1})
    settings["text_model"] = str(model.resolve())
    immutable = {"baseline_path": str(baseline), "baseline_sha256": hashes,
        "tasks_sha256": hashlib.sha256(json.dumps(tasks, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "settings": settings, "text_model_sha256": sha256(model),
        "source_sha256": source_hashes(), "prompt_version": VERSION,
        "mode_descriptions": MODES, "study_status": "post-test exploratory supplemental experiment",
        "runtime_version": package_version("llama-cpp-python"),
        "reference_access": "analysis phase only", "provenance": "real_model_inference"}
    path = output / "manifest.json"
    if path.exists():
        old = read_json(path)
        if any(old.get(key) != value for key, value in immutable.items()):
            raise ValueError("Followup settings, source, model or baseline changed; use a new output directory")
        if read_json(output / "tasks_public.json") != tasks:
            raise ValueError("Saved followup tasks changed; use a new output directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("Refusing nonempty output directory without followup manifest")
        write_json(output / "tasks_public.json", tasks)
        write_json(path, {**immutable, "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          "python": sys.version, "platform": platform.platform()})
    return tasks, settings


def control_messages(task, scene):
    return [{"role": "system", "content": "You edit flowcharts. " + SCENE_FORMAT},
        {"role": "user", "content": "Requested process:\n" + task["prompt"] +
         "\n\nCurrent flowchart:\n" + json.dumps(from_scene(scene), ensure_ascii=False) +
         "\n\nCorrect this chart using the original requested process. Preserve correct stages and connections."}]


def layout_messages(task, scene, program, visual):
    return [{"role": "system", "content": (
        'You edit only flowchart layout. Return ONLY {"positions":[[node_index,column,row],...]}. '
        "Use the zero-based node order from the current flowchart. Include every index exactly once. "
        "Columns are integers 0..2; rows are integers 0..7. Prefer downward flow, short edges, "
        "distinct cells, no overlaps or crossings. You can change coordinates only. "
        "All stages, types, connections and branch labels are fixed. Ignore feedback that requests semantic changes. "
        "Do not return labels, types, edges, explanations or scores.")},
        {"role": "user", "content": "Requested process:\n" + task["prompt"] +
         "\n\nCurrent flowchart (node order fixes indices):\n" + json.dumps(from_scene(scene), ensure_ascii=False) +
         "\n\nProgrammatic feedback:\n" + json.dumps(program, ensure_ascii=False) +
         "\n\nVisual feedback:\n" + visual + "\n\nImprove layout using the feedback while preserving all fixed content."}]


def apply_positions(scene, obj):
    """Reject malformed/injected output, and copy B0 changing x/y alone."""
    if not isinstance(obj, dict) or set(obj) != {"positions"}:
        raise ValueError("Output must contain only positions")
    positions = obj["positions"]
    if not isinstance(positions, list) or len(positions) != len(scene["nodes"]):
        raise ValueError("Every node needs exactly one position")
    seen, result = set(), copy.deepcopy(scene)
    for item in positions:
        if not isinstance(item, list) or len(item) != 3 or any(type(v) is not int for v in item):
            raise ValueError("Each position must be [integer index, integer column, integer row]")
        index, col, row = item
        if index in seen or not 0 <= index < len(scene["nodes"]):
            raise ValueError("Duplicate or invalid node index")
        if not 0 <= col <= 2 or not 0 <= row <= 7:
            raise ValueError("Grid position outside columns 0..2 and rows 0..7")
        seen.add(index)
        result["nodes"][index].update(x=25 + 255 * col, y=30 + 170 * row)
    return result


class LayoutCPU(LlamaCPU):
    """Same CPU decoding settings as baseline, coordinate-only JSON grammar."""
    def complete(self, messages, max_tokens=900, json_output=True):
        started = time.perf_counter()
        self._load()
        response = self.model.create_chat_completion(messages=messages, max_tokens=max_tokens,
            temperature=0.0, top_p=1.0, seed=self.seed,
            response_format={"type": "json_object", "schema": POSITION_SCHEMA})
        choice = response["choices"][0]
        return {"text": choice["message"]["content"] or "", "elapsed_seconds": time.perf_counter() - started,
            "usage": response.get("usage", {}), "finish_reason": choice.get("finish_reason"),
            "backend": "llama-cpp-python", "runtime_version": package_version("llama-cpp-python"),
            "model": self.model_path, "device": "cpu", "seed": self.seed, "temperature": 0.0,
            "response_schema": "positions-only-v1"}


def model_layout(folder, messages, scene, backend, max_tokens, max_repairs=1):
    errors = []
    for attempt in range(max_repairs + 1):
        cache = folder / f"call_repair_{attempt}.json"
        if cache.exists():
            record = read_json(cache)
            if record["messages"] != messages:
                raise ValueError("Cached layout request changed")
            response = record["response"]
            if "text" not in response:
                raise RuntimeError("Previous inference call failed; preserve run and use a new directory")
        else:
            started = time.perf_counter()
            try:
                response = backend.complete(messages, max_tokens=max_tokens, json_output=True)
            except Exception as error:
                _log_call(folder, "repair", attempt, messages,
                    {"elapsed_seconds": time.perf_counter() - started, "usage": {},
                     "error": f"{type(error).__name__}: {error}"})
                raise
            _log_call(folder, "repair", attempt, messages, response)
        try:
            return apply_positions(scene, json.loads(response["text"])), errors
        except (ValueError, TypeError, KeyError) as error:
            errors.append(str(error))
            messages = messages + [{"role": "assistant", "content": response["text"]},
                {"role": "user", "content": "Invalid coordinate output: " + str(error) +
                 '. Return only valid {"positions":[[node_index,column,row],...]} for every original node.'}]
    return None, errors


def run_followup(baseline, output, tasks, backend, modes=("C0", "L3"), max_tokens=900, format_repairs=1):
    baseline, output = Path(baseline), Path(output)
    if any(mode not in MODES for mode in modes):
        raise ValueError("Unknown supplemental mode")
    for task in tasks:
        parent = baseline / task["id"]
        scene = read_json(parent / "B0/scene.json")
        for mode in modes:
            folder = output / task["id"] / mode
            if (folder / "status.json").exists():
                continue
            print("FOLLOWUP", mode, task["id"], flush=True)
            if mode == "C0":
                result, errors = _model_scene(folder, control_messages(task, scene), backend,
                    "repair", max_tokens, max_repairs=format_repairs)
            else:
                messages = layout_messages(task, scene, read_json(parent / "B0/program_feedback.json"),
                                           read_json(parent / "visual/feedback.json")["text"])
                result, errors = model_layout(folder, messages, scene, backend, max_tokens, format_repairs)
                if result is not None:
                    write_json(folder / "layout_audit.json", {"topology_preserved": True,
                        "changed_fields": ["nodes[].x", "nodes[].y"],
                        "source_scene_sha256": sha256(parent / "B0/scene.json"),
                        "positions": [[i, (n["x"]-25)//255, (n["y"]-30)//170]
                                      for i, n in enumerate(result["nodes"])]})
            _save_scene(folder, result, errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="runs/test_v1")
    parser.add_argument("--output", default="runs/followup_v1")
    parser.add_argument("--limit", type=int, help="Separate smoke-run output directory required")
    parser.add_argument("--phase", choices=("prepare", "run"), default="run")
    parser.add_argument("--modes", default="C0,L3", help="Execution selection; manifest always declares both modes")
    args = parser.parse_args()
    modes = tuple(args.modes.split(","))
    if len(set(modes)) != len(modes) or any(mode not in MODES for mode in modes):
        parser.error("--modes must be a nonempty unique subset of C0,L3")
    tasks, settings = initialize_followup(args.baseline, args.output, args.limit)
    if args.phase == "prepare":
        print("Prepared", args.output, "tasks:", len(tasks))
        return
    for mode in modes:
        cls = LlamaCPU if mode == "C0" else LayoutCPU
        backend = cls(settings["text_model"], threads=settings["threads"],
                      context=settings["context"], seed=settings["seed"])
        try:
            run_followup(args.baseline, args.output, tasks, backend, (mode,),
                         settings["max_tokens"], settings["format_repairs"])
        finally:
            backend.close()


if __name__ == "__main__":
    main()
