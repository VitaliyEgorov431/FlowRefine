# VLM replacement comparison

| Arm | Old executed | New executed | Paired | Edge F1 delta |
|---|---:|---:|---:|---:|
| B2 | 15 | 15 | 15 | -0.1022 |
| B3 | 15 | 15 | 15 | -0.0895 |

Costs (logged model time; includes cold loading):
{
  "historical_reused": {
    "calls": 30,
    "seconds": 556.9636179000045
  },
  "newly_executed": {
    "calls": 48,
    "seconds": 1141.0553934004856
  }
}

Only paired executed tasks enter deltas; invalid executions score zero semantics.
Unexecuted arms remain unavailable, not zero.
B0/B1 and their exact call logs are historical reused artifacts.
Shared analysis totals mix historical and new calls; use costs here for new experiment time.
Different machines and mixed historical costs do not support a speed comparison.
