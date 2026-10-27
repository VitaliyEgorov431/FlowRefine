"""Create a new source/result archive and verify extracted tests without inference."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "submission/followup_v1/FlowRefine_Followup_Project.zip"
    if output.exists():
        raise SystemExit("Archive exists; preserve it and choose a new output version")
    (root / "tmp").mkdir(exist_ok=True)
    staged_archive = root / "tmp/FlowRefine_Followup_Project.staging.zip"
    required = ["README.md", "submission/report.pdf", "submission/report.md", "submission/presentation_final.pptx",
        "submission/DEFENSE_NOTES_RU.md", "submission/followup_v1/report_followup.md", "submission/followup_v1/report_followup.pdf",
        "submission/followup_v1/FlowRefine_Defense.pptx", "analysis/followup_v1/aggregate.json", "analysis/followup_v1/metrics.csv",
        "runs/followup_v1/manifest.json", "runs/followup_v1/INTERRUPTION_NOTE.json",
        "runs/layout_v2/manifest.json", "runs/layout_development_v2/manifest.json",
        "demo/followup.html", "snapshots/baseline_test_v1/manifest.json"]
    for name in required:
        if not (root / name).is_file():
            raise SystemExit("Missing deliverable: " + name)
    top = {"src", "tests", "data", "configs", "runtime_setup", "tools", "notebooks"}
    root_files = {"README.md", "PLAN.md", "PROGRESS.md", "pyproject.toml", "requirements.txt", "run_cpu.ps1", "launch_demo.ps1", ".gitignore"}
    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        r = p.relative_to(root)
        if any(x in {".venv", "models", ".cache", "__pycache__", ".deck_build", "tmp", ".pytest_cache"} for x in r.parts):
            continue
        include = r.parts[0] in top or r.as_posix() in root_files or r.as_posix() in required
        include |= r.parts[0] in {"runs", "analysis"} and len(r.parts) > 1 and (r.parts[1] in {"test_v1", "followup_v1", "layout_v2", "development_3b_v1"} or r.parts[1].startswith("layout_development"))
        include |= r.as_posix() in {"demo/index.html", "submission/VALIDATION.json", "snapshots/baseline_test_v1/baseline.zip"}
        include |= r.parts[0] == "submission" and len(r.parts) > 2 and r.parts[1] == "followup_v1" and p.suffix in {".md", ".pdf"}
        if include and p.suffix not in {".pyc", ".gguf", ".part", ".partial", ".log"} and (p.suffix != ".zip" or r.as_posix() == "snapshots/baseline_test_v1/baseline.zip"):
            files.append((p, r))
    with zipfile.ZipFile(staged_archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p, r in sorted(files):
            archive.write(p, "FlowRefine/" + r.as_posix())
    with zipfile.ZipFile(staged_archive) as archive:
        if archive.testzip():
            raise SystemExit("Archive CRC failure")
        (root / "tmp").mkdir(exist_ok=True)
        extraction = Path(tempfile.mkdtemp(prefix="followup_package_", dir=root / "tmp"))
        archive.extractall(extraction)
    check = extraction / "FlowRefine"
    env = dict(os.environ, PYTHONPATH=str(check / "src"))
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=check, env=env, text=True, capture_output=True)
    log = result.stdout + result.stderr
    count = re.search(r"Ran (\d+) tests?", log)
    if result.returncode or not count:
        raise SystemExit("Extracted tests failed:\n" + log)
    skipped_match = re.search(r"skipped=(\d+)", log)
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    changed = [name for name in required if sha(root / name) != sha(check / name)]
    if changed:
        raise SystemExit("Extracted deliverable hash mismatch: " + str(changed))
    replay = subprocess.run([sys.executable, "-m", "flowrefine.followup_analysis", "--baseline", "runs/test_v1",
        "--followup", "runs/followup_v1", "--layout-followup", "runs/layout_v2", "--output", "analysis/package_replay"],
        cwd=check, env=env, text=True, capture_output=True)
    if replay.returncode:
        raise SystemExit("Extracted analysis failed:\n" + replay.stdout + replay.stderr)
    expected = json.loads((root / "analysis/followup_v1/aggregate.json").read_text(encoding="utf-8"))
    observed = json.loads((check / "analysis/package_replay/aggregate.json").read_text(encoding="utf-8"))
    compare = ["arms", "paired_differences", "critic_audit", "failed_layout_attempts", "baseline_actual_logged_calls",
        "baseline_actual_logged_inference_seconds", "followup_actual_logged_calls", "followup_actual_logged_inference_seconds"]
    analysis_equal = all(expected[k] == observed[k] for k in compare)
    if not analysis_equal:
        raise SystemExit("Extracted supplemental analysis differs in: " + str([k for k in compare if expected[k] != observed[k]]))
    if output.exists():
        raise SystemExit("Final archive appeared while validation ran; refusing overwrite")
    staged_archive.rename(output)
    receipt = {"archive": str(output), "sha256": sha(output), "files": len(files), "bytes": output.stat().st_size,
        "crc_ok": True, "extraction": str(extraction), "extracted_tests_run": int(count.group(1)),
        "extracted_tests_skipped": skipped, "extracted_tests_passed": int(count.group(1)) - skipped,
        "test_command": "python -m unittest discover -s tests -v", "test_exit_code": result.returncode,
        "extracted_analysis_equal": analysis_equal, "analysis_compared_keys": compare,
        "deliverable_sha256": {name: sha(root / name) for name in required}, "weights_included": False,
        "original_archive_preserved": True, "new_inference_during_package_check": False}
    (root / "submission/followup_v1/PACKAGE_CHECK.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "submission/followup_v1/package_tests.txt").write_text(log, encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
