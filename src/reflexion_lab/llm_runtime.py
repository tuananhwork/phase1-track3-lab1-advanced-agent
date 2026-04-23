from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Protocol

from dotenv import load_dotenv
from openai import OpenAI

from . import mock_runtime
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import JudgeResult, QAExample, ReflectionEntry


@dataclass
class RuntimeOutput:
    payload: str | JudgeResult | ReflectionEntry
    tokens: int
    latency_ms: int


class RuntimeAdapter(Protocol):
    def actor_answer(
        self,
        example: QAExample,
        attempt_id: int,
        agent_type: str,
        reflection_memory: list[str],
    ) -> RuntimeOutput: ...

    def evaluator(self, example: QAExample, answer: str) -> RuntimeOutput: ...

    def reflector(self, example: QAExample, attempt_id: int, judge: JudgeResult) -> RuntimeOutput: ...


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model response did not contain a valid JSON object.")
        return json.loads(text[start : end + 1])


class MockRuntime:
    def actor_answer(
        self,
        example: QAExample,
        attempt_id: int,
        agent_type: str,
        reflection_memory: list[str],
    ) -> RuntimeOutput:
        answer = mock_runtime.actor_answer(example, attempt_id, agent_type, reflection_memory)
        tokens = 220 + (attempt_id * 35) + (80 if agent_type == "reflexion" else 0)
        latency_ms = 120 + (attempt_id * 20) + (70 if agent_type == "reflexion" else 0)
        return RuntimeOutput(payload=answer, tokens=tokens, latency_ms=latency_ms)

    def evaluator(self, example: QAExample, answer: str) -> RuntimeOutput:
        judge = mock_runtime.evaluator(example, answer)
        return RuntimeOutput(payload=judge, tokens=140, latency_ms=90)

    def reflector(self, example: QAExample, attempt_id: int, judge: JudgeResult) -> RuntimeOutput:
        reflection = mock_runtime.reflector(example, attempt_id, judge)
        return RuntimeOutput(payload=reflection, tokens=120, latency_ms=85)


class OpenAICompatibleRuntime:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    @classmethod
    def from_env(cls, model_override: str | None = None) -> "OpenAICompatibleRuntime":
        load_dotenv()
        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")
        model = model_override or os.getenv("LLM_MODEL")
        missing = [
            name
            for name, value in [
                ("LLM_BASE_URL", base_url),
                ("LLM_API_KEY", api_key),
                ("LLM_MODEL", model),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(base_url=base_url, api_key=api_key, model=model)

    def _chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> RuntimeOutput:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        usage = response.usage
        if usage is None or usage.total_tokens is None:
            raise RuntimeError("Real LLM response is missing `usage.total_tokens`; aborting token accounting.")
        content = response.choices[0].message.content or ""
        return RuntimeOutput(payload=content.strip(), tokens=int(usage.total_tokens), latency_ms=latency_ms)

    def actor_answer(
        self,
        example: QAExample,
        attempt_id: int,
        agent_type: str,
        reflection_memory: list[str],
    ) -> RuntimeOutput:
        context_text = "\n".join(f"- {chunk.title}: {chunk.text}" for chunk in example.context)
        memory_text = "\n".join(f"- {line}" for line in reflection_memory) if reflection_memory else "- none"
        user_prompt = (
            f"Question:\n{example.question}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Attempt: {attempt_id}\n"
            f"Agent type: {agent_type}\n"
            f"Reflection memory:\n{memory_text}\n\n"
            "Return only the final answer."
        )
        out = self._chat(ACTOR_SYSTEM, user_prompt, temperature=0.1)
        return RuntimeOutput(payload=str(out.payload), tokens=out.tokens, latency_ms=out.latency_ms)

    def evaluator(self, example: QAExample, answer: str) -> RuntimeOutput:
        user_prompt = (
            f"Question: {example.question}\n"
            f"Gold answer: {example.gold_answer}\n"
            f"Candidate answer: {answer}\n"
            "Judge the candidate and return strict JSON."
        )
        out = self._chat(EVALUATOR_SYSTEM, user_prompt, temperature=0.0)
        payload = _extract_json_object(str(out.payload))
        judge = JudgeResult.model_validate(payload)
        return RuntimeOutput(payload=judge, tokens=out.tokens, latency_ms=out.latency_ms)

    def reflector(self, example: QAExample, attempt_id: int, judge: JudgeResult) -> RuntimeOutput:
        user_prompt = (
            f"Question: {example.question}\n"
            f"Attempt id: {attempt_id}\n"
            f"Evaluator reason: {judge.reason}\n"
            f"Missing evidence: {judge.missing_evidence}\n"
            f"Spurious claims: {judge.spurious_claims}\n"
            "Return strict JSON for lesson and next strategy."
        )
        out = self._chat(REFLECTOR_SYSTEM, user_prompt, temperature=0.0)
        payload = _extract_json_object(str(out.payload))
        reflection = ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=judge.reason,
            lesson=str(payload["lesson"]),
            next_strategy=str(payload["next_strategy"]),
        )
        return RuntimeOutput(payload=reflection, tokens=out.tokens, latency_ms=out.latency_ms)
