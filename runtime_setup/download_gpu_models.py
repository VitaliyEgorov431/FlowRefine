"""Download only the two models needed by the GPU comparison; freeze Hub revision."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Qwen/Qwen2.5-VL-3B-Instruct'
REVISION = '66285546d2b821cf421d4f5eb2576359d3770cd3'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    from huggingface_hub import snapshot_download, hf_hub_download
    lock_path = ROOT / 'runtime_setup/gpu_model_lock.json'
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding='utf-8'))
        if lock['repo_id'] != REPO:
            raise ValueError('Different model already locked; preserve this bundle and use a new copy.')
    else:
        lock = {'repo_id': REPO, 'revision': REVISION,
                'local_path': 'models/Qwen2.5-VL-3B-Instruct',
                'dtype': 'float16', 'license': 'qwen-research (see upstream model card)'}
        lock_path.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    print('Frozen VLM:', lock['repo_id'], lock['revision'], flush=True)
    target = ROOT / lock['local_path']
    snapshot_download(repo_id=REPO, revision=lock['revision'], local_dir=target,
                      allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', '*.jinja', 'README.md', 'LICENSE'],
                      max_workers=4)
    # Record byte hashes so a later experiment cannot silently use altered weights.
    lock['files_sha256'] = {p.relative_to(target).as_posix(): digest(p)
        for p in sorted(target.rglob('*')) if p.is_file() and '.cache' not in p.parts}
    temp = lock_path.with_suffix('.tmp')
    temp.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    temp.replace(lock_path)
    original = json.loads((ROOT / 'configs/model_lock.json').read_text(encoding='utf-8'))
    item = next(x for x in original['files'] if '3b-instruct' in x['filename'])
    path = ROOT / 'models' / item['filename']
    if not path.exists():
        hf_hub_download(repo_id=item['repo_id'], filename=item['filename'],
                        revision=item['revision'], local_dir=ROOT / 'models')
    if path.stat().st_size != item['size_bytes'] or digest(path) != item['sha256']:
        raise ValueError('Text GGUF fails frozen size/hash check. Preserve file and inspect.')
    print('Both models downloaded and verified.', flush=True)


if __name__ == '__main__':
    main()
