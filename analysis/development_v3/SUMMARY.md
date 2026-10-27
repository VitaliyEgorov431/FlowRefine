# Pilot experiment summary

Tasks: 3. Provenance: real_model_inference.

| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |
|---|---:|---:|---:|---:|---:|
| B0 | 3 / 3 | 2 | 0.000 | 0.485 | 0.000 |
| B1 | 3 / 3 | 2 | 0.000 | 0.485 | 0.000 |
| B2 | 3 / 3 | 2 | 0.000 | 0.485 | 0.000 |
| B3 | 3 / 3 | 2 | 0.000 | 0.485 | 3.000 |

Actual saved calls: 12; cached: 0; logged model time: 147.8 seconds.

Pilot on a small template-based dataset; no population-level claim.
Unexecuted arms are excluded, never assigned zero quality.
Executed invalid scenes score zero semantics; geometry is undefined.
Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.
Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.
Model latency excludes local CPU validation and rendering.
