# VLM replacement comparison

| Arm | Old executed | New executed | Paired | Edge F1 delta |
|---|---:|---:|---:|---:|
| B2 | 1 | 1 | 1 | -0.8000 |
| B3 | 1 | 1 | 1 | -0.4923 |

Costs (logged model time; includes cold loading):
{
  "historical_reused": {
    "calls": 2,
    "seconds": 47.419751299999916
  },
  "newly_executed": {
    "calls": 3,
    "seconds": 92.45975149993319
  }
}

Only paired executed tasks enter deltas; invalid executions score zero semantics.
Unexecuted arms remain unavailable, not zero.
B0/B1 and their exact call logs are historical reused artifacts.
Shared analysis totals mix historical and new calls; use costs here for new experiment time.
Different machines and mixed historical costs do not support a speed comparison.
