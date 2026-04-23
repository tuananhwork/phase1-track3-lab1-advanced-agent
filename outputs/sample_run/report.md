# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_100.json
- Mode: mock
- Records: 200
- Agents: react, reflexion

## Summary
| Metric             | ReAct | Reflexion | Delta |
| ------------------ | ----: | --------: | ----: |
| EM                 |   1.0 |       1.0 |   0.0 |
| Avg attempts       |     1 |         1 |     0 |
| Avg token estimate |   395 |       475 |    80 |
| Avg latency (ms)   |   230 |       300 |    70 |

## Failure modes
```json
{
  "react": {
    "none": 100
  },
  "reflexion": {
    "none": 100
  },
  "overall": {
    "none": 200
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- adaptive_max_attempts
- mock_mode_for_autograding

## Discussion
This benchmark was executed in mock mode to compare single-pass ReAct against iterative Reflexion. ReAct EM=1.0 while Reflexion EM=1.0, giving delta=0.0. Reflexion used more attempts on average (1 vs 1) and therefore higher token/latency budgets (475 tokens, 300 ms). Failure profile indicates where reflection still did not recover the trajectory. ReAct failures: {'none': 100}. Reflexion failures: {'none': 100}. The gains depend strongly on evaluator quality and whether reflections are specific, actionable, and grounded in second-hop evidence rather than generic advice.
