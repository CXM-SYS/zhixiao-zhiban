import json
from pathlib import Path

from mozhi_yansuan.core import TraceableResearchAgent, write_outputs


ROOT = Path(__file__).parents[1]


def test_demo_run_is_traceable(tmp_path: Path) -> None:
    agent = TraceableResearchAgent(
        ROOT / "examples" / "task.md",
        ROOT / "data" / "demo_workplace_tasks.csv",
        ROOT / "examples" / "report.txt",
    )
    result = agent.run()
    assert result["inputs"]["data"]["sha256"]
    assert result["data_audit"]["rows"] == 8
    assert result["data_audit"]["missing"]["owner"] == 1
    assert result["data_audit"]["missing"]["deadline"] == 1
    assert result["data_audit"]["numeric_summary"]["hours"]["iqr_outliers"] >= 1
    assert any(item["category"] == "evidence" for item in result["findings"])
    outputs = write_outputs(result, tmp_path, agent)
    assert Path(outputs["markdown"]).exists()
    assert Path(outputs["html"]).exists()
    loaded = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
    assert loaded["status"] == result["status"]


def test_missing_report_is_explicit() -> None:
    agent = TraceableResearchAgent(
        ROOT / "examples" / "task.md",
        ROOT / "data" / "demo_workplace_tasks.csv",
    )
    result = agent.run()
    assert result["evidence_audit"]["report_provided"] is False
    assert any(item["finding_id"] == "EVIDENCE-001" for item in result["findings"])
