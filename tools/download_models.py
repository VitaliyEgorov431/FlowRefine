"""Download the pinned public weights and verify SHA-256 (optional for replay)."""

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-development", action="store_true", help="Also download the exploratory 1.5B model")
    args = parser.parse_args()
    lock = json.loads((root/"configs/model_lock.json").read_text(encoding="utf-8"))
    target = root/"models"
    target.mkdir(exist_ok=True)
    for item in lock["files"]:
        filename = item["filename"]
        if Path(filename).name != filename:
            raise ValueError("Unsafe filename in model lock")
        if "1.5b" in filename.lower() and not args.include_development:
            continue
        path = target/filename
        print(f"Model: {item['repo_id']}, license: {item.get('license', 'see model card')}", flush=True)
        if path.exists():
            if path.stat().st_size == item["size_bytes"] and digest(path) == item["sha256"]:
                print("Verified existing:", filename, flush=True)
                continue
            raise SystemExit(f"Existing file fails verification: {path}. Preserve it and inspect before retrying.")
        part = path.with_suffix(path.suffix+".partial")
        offset = part.stat().st_size if part.exists() else 0
        url = f"https://huggingface.co/{item['repo_id']}/resolve/{item['revision']}/{filename}"
        request = urllib.request.Request(url, headers={"User-Agent": "FlowRefine-CPU/0.1"})
        if offset:
            request.add_header("Range", f"bytes={offset}-")
        last = 0
        with urllib.request.urlopen(request, timeout=60) as response:
            append = response.status == 206 and offset > 0
            written = offset if append else 0
            with part.open("ab" if append else "wb") as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
                    written += len(block)
                    if time.monotonic() - last > 3:
                        print(f"  {written/1024**2:.0f} / {item['size_bytes']/1024**2:.0f} MiB", flush=True)
                        last = time.monotonic()
        if part.stat().st_size != item["size_bytes"] or digest(part) != item["sha256"]:
            raise SystemExit(f"Verification failed for {filename}; partial preserved, not used as a model.")
        part.replace(path)
        print("Verified:", filename, flush=True)


if __name__ == "__main__":
    main()
