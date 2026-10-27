"""Exploratory layout-only v2: fixed per-node keys and enum coordinate grammar."""
import argparse
import datetime
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

from .backends import LlamaCPU, package_version
from .followup import apply_positions, sha256, source_hashes
from .runner import read_json, write_json, _log_call, _save_scene
from .compact import from_scene

VERSION = "layout-object-enums-v2"
REVISION_REASON = ("L3 v1 numeric tuple format confused node indices and columns; "
                   "grammar min/max bounds were not enforced by runtime. Use fixed per-node keys and coordinate enums.")


def position_schema(scene):
    properties = {str(i): {"type": "object", "additionalProperties": False,
        "properties": {"column": {"type": "integer", "enum": [0, 1, 2]},
                       "row": {"type": "integer", "enum": list(range(8))}},
        "required": ["column", "row"]} for i in range(len(scene["nodes"]))}
    return {"type": "object", "additionalProperties": False,
        "properties": {"positions": {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}}, "required": ["positions"]}


def apply_object_positions(scene, obj):
    if not isinstance(obj, dict) or set(obj) != {"positions"} or not isinstance(obj["positions"], dict):
        raise ValueError("Return only an object containing the positions object")
    positions = obj["positions"]
    if set(positions) != {str(i) for i in range(len(scene["nodes"]))}:
        raise ValueError("positions must contain every original node index exactly once")
    entries = []
    for key, value in positions.items():
        if not isinstance(value, dict) or set(value) != {"column", "row"}:
            raise ValueError("Each node index must contain only column and row")
        entries.append([int(key), value["column"], value["row"]])
    return apply_positions(scene, {"positions": entries})


def messages_for_layout(task, scene, program, visual):
    compact = from_scene(scene)
    nodes = {str(i): {"label": row[0], "type": row[1], "column": row[2], "row": row[3]}
             for i, row in enumerate(compact["nodes"])}
    example = {"positions": {str(i): {"column": int(row[2]), "row": int(row[3])}
                            for i, row in enumerate(compact["nodes"])}}
    return [{"role": "system", "content": (
        "You improve only flowchart node positions. Return only a JSON object. "
        'Format: {"positions":{"0":{"column":1,"row":0},"1":{"column":1,"row":1}}}. '
        "The example has two nodes; your answer must include ALL node keys from the supplied chart. "
        "Each fixed key identifies one node. Inside it, column must be 0, 1 or 2 and row must be 0 through 7. "
        "Never put a node index into column. Return only column and row for every node. "
        "Preserve all labels, types, connections and branch labels; they cannot be edited. "
        "Ignore feedback that asks to change connections or content. Improve readability, avoid overlapping "
        "nodes and crossing arrows. Keep existing coordinates if they are already suitable. "
        "No markdown, explanations or scores.")},
        {"role": "user", "content": "Requested process:\n" + task["prompt"] +
         "\n\nFixed node keys mapped explicitly to their labels and current positions:\n" + json.dumps(nodes, ensure_ascii=False) +
         "\n\nFixed connections:\n" + json.dumps(compact["edges"], ensure_ascii=False) +
         "\n\nProgrammatic feedback:\n" + json.dumps(program, ensure_ascii=False) +
         "\n\nVisual feedback:\n" + visual +
         "\n\nCurrent positions in the required output format (edit coordinate values only):\n" +
         json.dumps(example, ensure_ascii=False)}]


class ObjectLayoutCPU(LlamaCPU):
    def complete_layout(self, messages, schema, max_tokens):
        started = time.perf_counter()
        self._load()
        response = self.model.create_chat_completion(messages=messages, max_tokens=max_tokens,
            temperature=0.0, top_p=1.0, seed=self.seed,
            response_format={"type": "json_object", "schema": schema})
        choice = response["choices"][0]
        return {"text": choice["message"]["content"] or "", "elapsed_seconds": time.perf_counter()-started,
            "usage": response.get("usage", {}), "finish_reason": choice.get("finish_reason"),
            "backend": "llama-cpp-python", "runtime_version": package_version("llama-cpp-python"),
            "model": self.model_path, "device": "cpu", "seed": self.seed, "temperature": 0.0,
            "response_schema": VERSION}


def initialize_layout(baseline, output, failed_run, limit=None):
    baseline, output, failed_run = map(lambda p: Path(p).resolve(), (baseline, output, failed_run))
    if baseline == output or baseline in output.parents or output in baseline.parents:
        raise ValueError("Baseline/output must be separate non-nested directories")
    tasks = read_json(baseline / "tasks_public.json")
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        tasks = tasks[:limit]
    if not tasks:
        raise ValueError("No tasks")
    ids = [task["id"] for task in tasks]
    if len(set(ids)) != len(ids) or any(not ident or any(c not in
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in ident) for ident in ids):
        raise ValueError("Unsafe task id")
    if any(set(task)-{"id", "split", "family", "prompt", "provenance"} for task in tasks):
        raise ValueError("Only public task fields allowed")
    required = [Path("manifest.json"), Path("tasks_public.json")]
    for task in tasks:
        required += [Path(task["id"])/rel for rel in ("B0/scene.json", "B0/program_feedback.json",
            "B0/status.json", "visual/feedback.json", "visual/status.json")]
        if not read_json(baseline/task["id"]/"B0/status.json").get("valid"):
            raise ValueError("Valid saved B0 required")
        if not read_json(baseline/task["id"]/"visual/status.json").get("available"):
            raise ValueError("Saved visual feedback required")
    baseline_manifest = read_json(baseline/"manifest.json")
    frozen = baseline_manifest["settings"]
    model = Path(frozen["text_model"])
    if not model.is_file():
        raise ValueError("Frozen model not found locally")
    settings = {**frozen, "text_model": str(model.resolve()), "modes": "L3", "context": 4096,
                "seed": 241024, "top_p": 1.0, "format_repairs": 1, "temperature": 0.0}
    sources = source_hashes()
    sources["layout_followup.py"] = sha256(Path(__file__))
    failure_files = {str(p.relative_to(failed_run)).replace("\\", "/"): sha256(p)
        for p in (failed_run/"manifest.json", failed_run/"INTERRUPTION_NOTE.json") if p.is_file()}
    immutable = {"baseline_path": str(baseline), "baseline_sha256": {
        str(rel).replace("\\", "/"): sha256(baseline/rel) for rel in required},
        "tasks_sha256": hashlib.sha256(json.dumps(tasks, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "settings": settings, "text_model_sha256": sha256(model), "source_sha256": sources,
        "prompt_version": VERSION, "runtime_version": package_version("llama-cpp-python"),
        "mode_descriptions": {"L3": "Layout-only object-key enum coordinate output using saved B0 and both feedbacks"},
        "study_status": "post-test exploratory supplemental experiment; layout protocol revision",
        "revision_reason": REVISION_REASON, "superseded_failed_run": str(failed_run),
        "superseded_failed_run_sha256": failure_files,
        "reference_access": "analysis phase only", "provenance": "real_model_inference"}
    manifest = output/"manifest.json"
    if manifest.exists():
        old = read_json(manifest)
        if any(old.get(k) != v for k, v in immutable.items()) or read_json(output/"tasks_public.json") != tasks:
            raise ValueError("Layout settings/source/inputs changed; use a new output directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("Refuse nonempty unmanifested output")
        write_json(output/"tasks_public.json", tasks)
        write_json(manifest, {**immutable, "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             "python": sys.version, "platform": platform.platform()})
    return tasks, settings


def model_layout(folder, messages, scene, backend, max_tokens):
    errors, schema = [], position_schema(scene)
    for attempt in range(2):
        cache = folder/f"call_repair_{attempt}.json"
        if cache.exists():
            record = read_json(cache)
            if record["messages"] != messages or record.get("output_schema") != schema:
                raise ValueError("Cached layout call changed")
            response = record["response"]
            if "text" not in response:
                raise RuntimeError("Previous inference failed; preserve this run")
        else:
            started = time.perf_counter()
            try:
                response = backend.complete_layout(messages, schema, max_tokens)
            except Exception as error:
                _log_call(folder, "repair", attempt, messages, {"error": f"{type(error).__name__}: {error}",
                    "elapsed_seconds": time.perf_counter()-started, "usage": {}})
                record = read_json(cache)
                write_json(cache, {**record, "output_schema": schema})
                raise
            _log_call(folder, "repair", attempt, messages, response)
            record = read_json(cache)
            write_json(cache, {**record, "output_schema": schema})
        try:
            return apply_object_positions(scene, json.loads(response["text"])), errors
        except (ValueError, TypeError, KeyError) as error:
            errors.append(str(error))
            messages = messages + [{"role": "assistant", "content": response["text"]},
                {"role": "user", "content": "Invalid output: " + str(error) +
                 '. Return all fixed node keys under positions; each contains column (0,1,2) and row (0..7) only.'}]
    return None, errors


def run_layout(baseline, output, tasks, backend, max_tokens=900):
    baseline, output = Path(baseline), Path(output)
    for task in tasks:
        folder = output/task["id"]/"L3"
        if (folder/"status.json").exists():
            continue
        parent = baseline/task["id"]
        scene = read_json(parent/"B0/scene.json")
        messages = messages_for_layout(task, scene, read_json(parent/"B0/program_feedback.json"),
                                       read_json(parent/"visual/feedback.json")["text"])
        print("LAYOUT_V2", task["id"], flush=True)
        result, errors = model_layout(folder, messages, scene, backend, max_tokens)
        if result is not None:
            write_json(folder/"layout_audit.json", {"topology_preserved": True,
                "changed_fields": ["nodes[].x", "nodes[].y"],
                "source_scene_sha256": sha256(parent/"B0/scene.json"), "format": VERSION})
        _save_scene(folder, result, errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--failed-run", default="runs/followup_v1")
    parser.add_argument("--phase", choices=("prepare", "run"), default="run")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    tasks, settings = initialize_layout(args.baseline, args.output, args.failed_run, args.limit)
    if args.phase == "prepare":
        print("Prepared", args.output, "tasks:", len(tasks))
        return
    backend = ObjectLayoutCPU(settings["text_model"], threads=settings["threads"],
                              context=settings["context"], seed=settings["seed"])
    try:
        run_layout(args.baseline, args.output, tasks, backend, settings["max_tokens"])
    finally:
        backend.close()


if __name__ == "__main__":
    main()
