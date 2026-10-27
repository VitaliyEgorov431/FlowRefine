# Pilot experiment summary

Tasks: 5. Provenance: real_model_inference.

| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |
|---|---:|---:|---:|---:|---:|
| B0 | 5 / 5 | 5 | 0.400 | 0.859 | 0.400 |
| B1 | 5 / 5 | 5 | 0.600 | 0.899 | 0.400 |
| B2 | 5 / 5 | 5 | 0.400 | 0.865 | 0.800 |
| B3 | 5 / 5 | 5 | 0.400 | 0.865 | 0.800 |

Actual saved calls: 25; cached: 0; logged model time: 430.8 seconds.

Pilot on a small template-based dataset; no population-level claim.
Unexecuted arms are excluded, never assigned zero quality.
Executed invalid scenes score zero semantics; geometry is undefined.
Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.
Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.
Model latency excludes local CPU validation and rendering.
