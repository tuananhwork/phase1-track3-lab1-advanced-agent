from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from .llm_runtime import MockRuntime, RuntimeAdapter
from .mock_runtime import FAILURE_MODE_BY_QID
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord
from .utils import normalize_answer

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    runtime: RuntimeAdapter = field(default_factory=MockRuntime)
    adaptive_max_attempts: bool = False

    def _resolve_attempt_budget(self, example: QAExample) -> int:
        if self.agent_type != "reflexion" or not self.adaptive_max_attempts:
            return self.max_attempts
        adaptive = {"easy": 2, "medium": 3, "hard": 4}.get(example.difficulty, 3)
        return min(self.max_attempts, adaptive)

    def _infer_failure_mode(self, example: QAExample, is_looping: bool, reflections: list[ReflectionEntry]) -> str:
        if is_looping:
            return "looping"
        if example.qid in FAILURE_MODE_BY_QID:
            return FAILURE_MODE_BY_QID[example.qid]
        if len(reflections) >= 2:
            return "reflection_overfit"
        return "wrong_final_answer"

    def run(self, example: QAExample) -> RunRecord:
        budget = self._resolve_attempt_budget(example)
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        seen_wrong_answers: set[str] = set()
        is_looping = False

        for attempt_id in range(1, budget + 1):
            actor_out = self.runtime.actor_answer(example, attempt_id, self.agent_type, reflection_memory)
            answer = str(actor_out.payload)
            judge_out = self.runtime.evaluator(example, answer)
            judge = judge_out.payload
            if not hasattr(judge, "score") or not hasattr(judge, "reason"):
                raise RuntimeError("Evaluator runtime must return JudgeResult payload.")

            token_estimate = actor_out.tokens + judge_out.tokens
            latency_ms = actor_out.latency_ms + judge_out.latency_ms
            trace = AttemptTrace(
                attempt_id=attempt_id,
                answer=answer,
                score=judge.score,
                reason=judge.reason,
                token_estimate=token_estimate,
                latency_ms=latency_ms,
            )
            final_answer = answer
            final_score = judge.score

            if judge.score == 1:
                traces.append(trace)
                break

            normalized = normalize_answer(answer)
            if normalized in seen_wrong_answers:
                is_looping = True
                traces.append(trace)
                break
            seen_wrong_answers.add(normalized)

            if self.agent_type == "reflexion" and attempt_id < budget:
                reflection_out = self.runtime.reflector(example, attempt_id, judge)
                reflection = reflection_out.payload
                if not isinstance(reflection, ReflectionEntry):
                    raise RuntimeError("Reflector runtime must return ReflectionEntry payload.")
                reflections.append(reflection)
                reflection_memory.append(reflection.lesson)
                reflection_memory.append(reflection.next_strategy)
                trace.reflection = reflection
                trace.token_estimate += reflection_out.tokens
                trace.latency_ms += reflection_out.latency_ms

            traces.append(trace)

        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        failure_mode = "none" if final_score == 1 else self._infer_failure_mode(example, is_looping, reflections)
        return RunRecord(qid=example.qid, question=example.question, gold_answer=example.gold_answer, agent_type=self.agent_type, predicted_answer=final_answer, is_correct=bool(final_score), attempts=len(traces), token_estimate=total_tokens, latency_ms=total_latency, failure_mode=failure_mode, reflections=reflections, traces=traces)

class ReActAgent(BaseAgent):
    def __init__(self, runtime: RuntimeAdapter | None = None) -> None:
        super().__init__(agent_type="react", max_attempts=1, runtime=runtime or MockRuntime())

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3, runtime: RuntimeAdapter | None = None, adaptive_max_attempts: bool = True) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts, runtime=runtime or MockRuntime(), adaptive_max_attempts=adaptive_max_attempts)
