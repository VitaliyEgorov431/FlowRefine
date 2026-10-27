# Pilot experiment summary

Tasks: 3. Provenance: real_model_inference.

| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |
|---|---:|---:|---:|---:|---:|
| B0 | 3 / 3 | 1 | 0.000 | 0.242 | 0.000 |
| B1 | 0 / 3 | 0 | unavailable | unavailable | unavailable |
| B2 | 0 / 3 | 0 | unavailable | unavailable | unavailable |
| B3 | 0 / 3 | 0 | unavailable | unavailable | unavailable |

Actual saved calls: 5; cached: 0; logged model time: 72.4 seconds.

Pilot on a small template-based dataset; no population-level claim.
Unexecuted arms are excluded, never assigned zero quality.
Executed invalid scenes score zero semantics; geometry is undefined.
Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.
Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.
Model latency excludes local CPU validation and rendering.
