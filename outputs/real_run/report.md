# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_100.json
- Mode: real
- Records: 200
- Agents: react, reflexion

## Summary
| Metric             |   ReAct | Reflexion |   Delta |
| ------------------ | ------: | --------: | ------: |
| EM                 |     0.9 |      0.96 |    0.06 |
| Avg attempts       |       1 |      1.12 |    0.12 |
| Avg token estimate | 10099.1 |  11847.74 | 1748.64 |
| Avg latency (ms)   | 6380.45 |    7734.5 | 1354.05 |

## Failure modes
```json
{
  "react": {
    "none": 90,
    "wrong_final_answer": 10
  },
  "reflexion": {
    "none": 96,
    "looping": 4
  },
  "overall": {
    "none": 186,
    "wrong_final_answer": 10,
    "looping": 4
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- adaptive_max_attempts

## Discussion
This benchmark was executed in real mode to compare single-pass ReAct against iterative Reflexion. ReAct EM=0.9 while Reflexion EM=0.96, giving delta=0.06. Reflexion used more attempts on average (1.12 vs 1) and therefore higher token/latency budgets (11847.74 tokens, 7734.5 ms). Failure profile indicates where reflection still did not recover the trajectory. ReAct failures: {'none': 90, 'wrong_final_answer': 10}. Reflexion failures: {'none': 96, 'looping': 4}. The gains depend strongly on evaluator quality and whether reflections are specific, actionable, and grounded in second-hop evidence rather than generic advice.
