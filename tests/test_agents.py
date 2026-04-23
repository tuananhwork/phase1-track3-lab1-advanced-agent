from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.reflexion_lab.agents import ReflexionAgent
from src.reflexion_lab.llm_runtime import MockRuntime, OpenAICompatibleRuntime
from src.reflexion_lab.schemas import ContextChunk, QAExample
from src.reflexion_lab.utils import load_dataset


def test_reflexion_memory_recovers_second_attempt():
    dataset = load_dataset("data/hotpot_mini.json")
    example = next(item for item in dataset if item.qid == "hp2")
    agent = ReflexionAgent(max_attempts=3, runtime=MockRuntime(), adaptive_max_attempts=True)
    record = agent.run(example)
    assert record.is_correct is True
    assert record.attempts == 2
    assert len(record.reflections) == 1
    assert record.traces[0].reflection is not None


def test_adaptive_attempt_budget_caps_with_cli_max():
    example = QAExample(
        qid="x1",
        difficulty="hard",
        question="q",
        gold_answer="a",
        context=[ContextChunk(title="t", text="x")],
    )
    capped = ReflexionAgent(max_attempts=3, runtime=MockRuntime(), adaptive_max_attempts=True)
    uncapped = ReflexionAgent(max_attempts=5, runtime=MockRuntime(), adaptive_max_attempts=True)
    assert capped._resolve_attempt_budget(example) == 3
    assert uncapped._resolve_attempt_budget(example) == 4


def test_real_runtime_fails_when_usage_missing():
    runtime = OpenAICompatibleRuntime(base_url="http://localhost:1/v1", api_key="k", model="m")

    fake_response = SimpleNamespace(
        usage=None,
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
    )

    runtime.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_: fake_response),
        )
    )

    with pytest.raises(RuntimeError, match="usage.total_tokens"):
        runtime._chat("sys", "user")
