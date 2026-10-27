# Pilot experiment summary

Tasks: 1. Provenance: real_model_inference_with_historical_B0_B1_reused.

| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |
|---|---:|---:|---:|---:|---:|
| B0 | 1 / 1 | 1 | 0.000 | 0.800 | 0.000 |
| B1 | 1 / 1 | 1 | 1.000 | 1.000 | 0.000 |
| B2 | 1 / 1 | 1 | 0.000 | 0.000 | 3.000 |
| B3 | 1 / 1 | 1 | 0.000 | 0.308 | 5.000 |

Actual saved calls: 5; cached: 0; logged model time: 139.9 seconds.

Pilot on a small template-based dataset; no population-level claim.
Unexecuted arms are excluded, never assigned zero quality.
Executed invalid scenes score zero semantics; geometry is undefined.
Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.
Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.
Model latency excludes local CPU validation and rendering.
