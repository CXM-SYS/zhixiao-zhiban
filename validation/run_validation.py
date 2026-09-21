from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mozhi_yansuan.agent import ToolCallingResearchAgent, write_agent_outputs


CASES = [
    {
        "id": "case01_meeting",
        "request": "case01_meeting_request.md",
        "document": "case01_meeting_notes.md",
        "expected": {"action_items": 3},
    },
    {
        "id": "case02_table",
        "request": "case02_table_request.md",
        "data": "case02_tasks.csv",
        "expected": {"data_findings": 4},
    },
    {
        "id": "case03_full",
        "request": "case03_full_request.md",
        "document": "case03_full_notes.md",
        "data": "case03_full_tasks.csv",
        "report": "case03_full_report.txt",
        "expected": {"evidence_warnings": 1},
    },
]


def main() -> None:
    cases_dir = ROOT / "validation" / "cases"
    result_dir = ROOT / "validation" / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    agent = ToolCallingResearchAgent(ROOT)
    for case in CASES:
        started = time.perf_counter()
        request = cases_dir / str(case["request"])
        document = cases_dir / str(case["document"]) if case.get("document") else None
        data = cases_dir / str(case["data"]) if case.get("data") else None
        report = cases_dir / str(case["report"]) if case.get("report") else None
        result = agent.run(request, data, report, mode="mock", document_path=document)
        elapsed = round(time.perf_counter() - started, 4)
        trace = result["tool_trace"]
        by_name = {item["tool"]: item["output"] for item in trace}
        actions = by_name.get("extract_action_items", {}).get("actions", {})
        findings = by_name.get("inspect_dataset", {}).get("findings", [])
        evidence = by_name.get("audit_evidence", {}).get("evidence", {})
        expected = case["expected"]
        actual_action_items = int(actions.get("action_item_count", 0))
        actual_findings = len(findings)
        actual_warnings = len(evidence.get("unanchored_claim_lines", []))
        if "action_items" in expected:
            expected_value = int(expected["action_items"])
            actual_value = actual_action_items
            metric = "待办识别覆盖率"
        elif "data_findings" in expected:
            expected_value = int(expected["data_findings"])
            actual_value = actual_findings
            metric = "数据问题识别覆盖率"
        else:
            expected_value = int(expected["evidence_warnings"])
            actual_value = actual_warnings
            metric = "依据风险提示覆盖率"
        coverage = round(min(actual_value / expected_value, 1.0), 4) if expected_value else None
        output_paths = write_agent_outputs(result, result_dir / str(case["id"]))
        rows.append({
            "case_id": case["id"],
            "metric": metric,
            "expected_count": expected_value,
            "actual_count": actual_value,
            "coverage": coverage,
            "elapsed_seconds": elapsed,
            "status": result["status"],
            "answer_path": output_paths["answer"],
            "trace_path": output_paths["trace"],
        })
    summary = {
        "purpose": "内部脱敏案例离线回放，不代表外部用户效果",
        "case_count": len(rows),
        "rows": rows,
    }
    (ROOT / "validation" / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (ROOT / "validation" / "metric_record.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
