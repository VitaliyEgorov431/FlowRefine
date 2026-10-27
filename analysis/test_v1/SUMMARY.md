# Pilot experiment summary

Tasks: 15. Provenance: real_model_inference.

| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |
|---|---:|---:|---:|---:|---:|
| B0 | 15 / 15 | 15 | 0.733 | 0.957 | 0.333 |
| B1 | 15 / 15 | 15 | 0.733 | 0.941 | 0.333 |
| B2 | 15 / 15 | 15 | 0.600 | 0.912 | 0.533 |
| B3 | 15 / 15 | 15 | 0.467 | 0.899 | 0.867 |

Actual saved calls: 75; cached: 0; logged model time: 1312.9 seconds.

Pilot on a small template-based dataset; no population-level claim.
Unexecuted arms are excluded, never assigned zero quality.
Executed invalid scenes score zero semantics; geometry is undefined.
Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.
Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.
Model latency excludes local CPU validation and rendering.
