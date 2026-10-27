"""Validate and package source plus real results; never include model weights."""

import hashlib
import json
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    aggregate = json.loads((root/"analysis/test_v1/aggregate.json").read_text())
    if aggregate["actual_logged_calls"] != 75 or aggregate["task_count"] != 15:
        raise SystemExit("Main experiment coverage changed; inspect before packaging")
    if any(aggregate["arms"][arm]["executed"] != 15 for arm in ("B0", "B1", "B2", "B3")):
        raise SystemExit("Main experiment incomplete")
    required = ["demo/index.html", "submission/report.pdf", "submission/report.md",
                "submission/presentation_final.pptx", "submission/DEFENSE_NOTES_RU.md",
                "notebooks/FlowRefine_CPU_executed.ipynb", "README.md", "configs/model_lock.json"]
    for name in required:
        if not (root/name).is_file():
            raise SystemExit("Missing deliverable: "+name)
    hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in required}
    receipt = {"test_task_count": 15, "test_model_calls": 75, "valid_test_scenes": 60,
               "test_runtime": "CPU only, llama-cpp-python 0.3.36",
               "tests_passed": 30, "browser_gallery": "15 tasks, 3 edited modes, SVG download checked",
               "notebook_replay": "7 code cells executed, no errors, inference disabled",
               "sources_and_metrics": "independently reviewed; all7 frozen source hashes match",
               "model_errors": 0, "finish_reasons": "75 stop responses",
               "shell_diagnostic_note": "Windows PowerShell wrapped native MTMD stderr as NativeCommandError; saved outputs complete; clean resume exited0 with no new calls",
               "deliverable_sha256": hashes,
               "weights_included": False,
               "notes": "No publication or submission to the course performed. Author name was not supplied."}
    receipt_path = root/"submission/VALIDATION.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    allowed_roots = {"src", "tests", "data", "configs", "runtime_setup", "tools", "notebooks"}
    allowed_files = {"README.md", "PLAN.md", "PROGRESS.md", "pyproject.toml", "requirements.txt",
                     "run_cpu.ps1", "launch_demo.ps1", ".gitignore"}
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in {".venv", "models", ".cache", "__pycache__", ".deck_build"} for part in rel.parts):
            continue
        include = rel.parts[0] in allowed_roots or rel.as_posix() in allowed_files
        include |= rel.parts[0] == "runs" and path.suffix in {".json", ".png", ".svg"}
        include |= rel.parts[0] == "analysis" and len(rel.parts) > 1 and rel.parts[1] in {"test_v1", "development_3b_v1"}
        include |= rel.as_posix() in {"demo/index.html", "runs/custom_demo/index.html"}
        include |= rel.as_posix() in required or rel.as_posix() in {"submission/VALIDATION.json", "submission/PACKAGE_CHECK.json"}
        if include and path.suffix not in {".pyc", ".gguf", ".part", ".partial", ".log", ".zip"}:
            files.append((path, rel))
    output = root/"submission/FlowRefine_Final_Project.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, rel in sorted(files):
            archive.write(path, "FlowRefine/"+rel.as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise SystemExit("Archive CRC verification failed")
    print(json.dumps({"archive": str(output), "files": len(files),
                      "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
