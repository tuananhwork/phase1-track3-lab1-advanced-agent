from __future__ import annotations
import json
import random
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.llm_runtime import MockRuntime, OpenAICompatibleRuntime, RuntimeAdapter
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(
    dataset: str = "data/hotpot_mini.json",
    out_dir: str = "outputs/sample_run",
    reflexion_attempts: int = 3,
    mode: str = "mock",
    model: str | None = None,
    sample_size: int = 0,
    seed: int = 42,
) -> None:
    examples = load_dataset(dataset)
    if sample_size > 0 and sample_size < len(examples):
        rng = random.Random(seed)
        examples = rng.sample(examples, sample_size)

    runtime: RuntimeAdapter
    if mode == "real":
        runtime = OpenAICompatibleRuntime.from_env(model_override=model)
    elif mode == "mock":
        runtime = MockRuntime()
    else:
        raise typer.BadParameter(f"Unsupported mode: {mode}. Expected 'mock' or 'real'.")

    react = ReActAgent(runtime=runtime)
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts, runtime=runtime, adaptive_max_attempts=True)
    react_records = [react.run(example) for example in examples]
    reflexion_records = [reflexion.run(example) for example in examples]
    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    report = build_report(
        all_records,
        dataset_name=Path(dataset).name,
        mode=mode,
        extensions=[
            "structured_evaluator",
            "reflection_memory",
            "benchmark_report_json",
            "adaptive_max_attempts",
        ]
        + (["mock_mode_for_autograding"] if mode == "mock" else []),
    )
    json_path, md_path = save_report(report, out_path)
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()
