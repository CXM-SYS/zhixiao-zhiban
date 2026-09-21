import json
from pathlib import Path

from mozhi_yansuan.agent import ToolCallingResearchAgent, write_agent_outputs


ROOT = Path(__file__).parents[1]


def test_mock_agent_calls_workplace_tools_and_writes_trace(tmp_path: Path) -> None:
    agent = ToolCallingResearchAgent(ROOT)
    result = agent.run(
        ROOT / "examples" / "task.md",
        ROOT / "data" / "demo_workplace_tasks.csv",
        ROOT / "examples" / "report.txt",
        mode="mock",
        document_path=ROOT / "examples" / "meeting_notes.md",
    )
    names = [item["tool"] for item in result["tool_trace"]]
    assert names == [
        "extract_task_requirements",
        "summarize_document",
        "extract_action_items",
        "inspect_dataset",
        "audit_evidence",
        "recommend_analysis_route",
    ]
    assert "文档摘要与待办" in result["final_output"]
    assert "数据发现" in result["final_output"]
    outputs = write_agent_outputs(result, tmp_path)
    trace = json.loads(Path(outputs["trace"]).read_text(encoding="utf-8"))
    assert trace["status"] == "COMPLETED"


def test_mock_agent_accepts_request_without_data(tmp_path: Path) -> None:
    agent = ToolCallingResearchAgent(ROOT)
    result = agent.run(ROOT / "examples" / "task.md", mode="mock")
    assert "未提供表格" in result["final_output"]
