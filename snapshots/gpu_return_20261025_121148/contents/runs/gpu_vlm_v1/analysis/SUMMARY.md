# Pilot experiment summary

Tasks: 15. Provenance: real_model_inference_with_historical_B0_B1_reused.

| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |
|---|---:|---:|---:|---:|---:|
| B0 | 15 / 15 | 15 | 0.733 | 0.957 | 0.333 |
| B1 | 15 / 15 | 15 | 0.733 | 0.941 | 0.333 |
| B2 | 15 / 15 | 14 | 0.333 | 0.810 | 0.143 |
| B3 | 15 / 15 | 14 | 0.333 | 0.810 | 0.214 |

Actual saved calls: 78; cached: 0; logged model time: 1698.0 seconds.

Pilot on a small template-based dataset; no population-level claim.
Unexecuted arms are excluded, never assigned zero quality.
Executed invalid scenes score zero semantics; geometry is undefined.
Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.
Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.
Model latency excludes local CPU validation and rendering.
