# FlowRefine

Editable flowchart generation and feedback-driven correction with local language and vision-language models.

Generative AI course project. Personal motivation: process documentation in oil and gas engineering. The experiments use **general synthetic processes**, not real industrial procedures.

## Final deliverables

- [Final presentation in English](submission/defense_v3/FlowRefine_Defense_EN_final.pptx): 10 main slides and 3 reference/backup slides, with Russian speaker notes.
- [Russian defense script and Q&A](submission/defense_v3/DEFENSE_SPEECH_RU.md).
- [Original CPU report](submission/report.md) and [PDF](submission/report.pdf).
- [CPU follow-up report](submission/followup_v1/report_followup.md).
- [GPU experiment comparison](snapshots/gpu_return_20261025_121148/contents/runs/gpu_vlm_v1/COMPARISON.md).
- [Detailed historical documentation in Russian](README_HISTORY_RU.md).

## Main results

Each task shares one saved initial graph, B0. B1 edits it using programmatic feedback, B2 uses visual feedback, and B3 uses both. These are independent edits of B0, not consecutive steps.

| Configuration | Initial B0 | Programmatic B1 | Visual B2 | Combined B3 |
|---|---:|---:|---:|---:|
| CPU: SmolVLM-256M critic | 11/15 | 11/15 | 9/15 | 7/15 |
| GPU: Qwen2.5-VL-3B critic | reused | reused | 5/15 | 5/15 |

Values are exactly correct graphs out of 15 tasks. Original mean edge F1 is 0.957 / 0.941 / 0.912 / 0.899 for B0/B1/B2/B3. New B2/B3 edge F1 is approximately 0.810, with 14 valid outputs out of 15 in each arm. Invalid executions receive zero semantic scores.

The second experiment replaces only the visual critic. It reuses the original B0/B1 and keeps the Qwen2.5-3B Q4_K_M CPU text editor. The critic runs in FP16 on an RTX 3060 12 GB, with a measured peak PyTorch allocation of 7.33 GiB. Model family, precision, image processing and inference backend change together, so this is not an isolated model-size experiment.

The GPU experiment is exploratory: it repeats the same 15 tasks after inspecting the first results. It does not establish a general ranking of model families. The results show false criticism propagating into harmful edits and useful feedback sometimes remaining unexecuted.

## Offline result galleries

Download or clone the repository, then open these HTML files in a browser:

- [Original CPU gallery](demo/index.html).
- [CPU follow-up gallery](demo/followup.html).
- [GPU gallery](snapshots/gpu_return_20261025_121148/contents/runs/gpu_vlm_v1/index.html).

These are standalone saved-output viewers. No GPU, model weights, network access or inference is required. GitHub displays HTML source; open the downloaded file locally to use the interactive viewer.

## Pipeline and data

1. A fixed public process description enters the text model.
2. The model creates compact graph JSON. A deterministic renderer produces SVG and PNG.
3. Programmatic checks inspect the graph/layout. The VLM sees only the original request and rendered image.
4. The text editor creates one corrected graph for each feedback arm.
5. Evaluation compares saved graphs against separately stored references.

There are 5 development tasks and 15 test tasks, including chains, branches and loops. The tasks and reference graphs come from predefined synthetic specifications. References enter evaluation only, never inference prompts. See the [dataset card](data/DATASET_CARD.md).

## Install and replay without models

Python 3.12 is the tested version. From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -m unittest discover -s tests -q
.venv\Scripts\python.exe -m flowrefine.cli analyze runs/test_v1 --output analysis/replay_cpu
.venv\Scripts\python.exe -m flowrefine.cli gallery runs/test_v1 --output demo/replay_cpu.html
```

For saved GPU results, the same analysis command can use `snapshots/gpu_return_20261025_121148/contents/runs/gpu_vlm_v1` as the run directory and a new analysis output directory. Analysis does not call models. Raw call timings for B0/B1 are historical reused costs; use `comparison.json` for newly executed GPU experiment costs.

## New inference

### Windows GPU experiment

Read [GPU_EXPERIMENT_RU.md](GPU_EXPERIMENT_RU.md). With Python 3.12 x64, Python Launcher and a suitable NVIDIA driver:

1. Run `01_SETUP_GPU.cmd` to install pinned CUDA dependencies and download/verify the models.
2. Run `02_RUN_EXPERIMENT.cmd` for the full 15-task comparison, or `02_RUN_QUICK5.cmd` for a fixed five-task subset.
3. Results and logs are collected into `GPU_RESULTS_*.zip`.

The VLM weights are about 7.52 GB and the text GGUF about 2.10 GB. They are not included in this repository. GPU inference uses its own `.venv-gpu`; CPU and VLM models are loaded sequentially. See [runtime requirements](runtime_setup/requirements-gpu.txt) and [downloader](runtime_setup/download_gpu_models.py).

### CPU inference

The tested CPU runtime is `llama-cpp-python==0.3.36`. See [runtime handoff](runtime_setup/HANDOFF.md), [model lock](configs/model_lock.json), and `tools/download_models.py`. Runtime dependencies are optional for replay. Model licenses differ by repository; refer to the upstream cards and model lock. No fine-tuning was performed in this project.

## Repository layout

| Directory | Contents |
|---|---|
| `src/flowrefine` | Generation, rendering, checks, evaluation, galleries and experiment runners |
| `data`, `configs` | Public tasks, isolated references and frozen model/protocol metadata |
| `runs`, `analysis` | Original and follow-up experiment evidence and metrics |
| `snapshots/gpu_return_20261025_121148` | Imported GPU results, runtime provenance and verification |
| `runtime_setup` | Optional inference setup, model download and result collection |
| `tests` | Regression and fixture-based runner tests |
| `submission` | Reports, final presentation and historical presentation versions |
| `tools`, `notebooks` | Reproduction and artifact-building helpers |

Temporary build directories, virtual environments, model weights and redundant transfer ZIPs are excluded. Historical manifests and raw responses retain original paths and runtime metadata for provenance. Model calls in tests use fixtures and are not experimental evidence. Code and presentation materials were developed with substantial AI assistance.
