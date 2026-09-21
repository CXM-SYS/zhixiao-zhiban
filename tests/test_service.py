from mozhi_yansuan.service import analyze_payload


def test_coze_payload_returns_workplace_answer() -> None:
    result = analyze_payload(
        {
            "request_text": "请整理项目进度，列出负责人和风险。",
            "document_text": "李宁负责整理验收材料，9月23日前完成。",
            "data_csv": "team,owner,hours\n项目组,李宁,6\n项目组,,40\n",
            "report_text": "结论：项目需要继续关注延期风险。",
        }
    )
    assert result["status"] == "COMPLETED"
    assert "任务理解" in result["answer"]
    assert "人工确认事项" in result["answer"]
    assert [item["tool"] for item in result["tool_trace"]] == [
        "extract_task_requirements",
        "summarize_document",
        "extract_action_items",
        "inspect_dataset",
        "audit_evidence",
        "recommend_analysis_route",
    ]


def test_coze_payload_can_use_legacy_task_alias_without_data() -> None:
    result = analyze_payload({"task_text": "请整理这项工作并列出下一步。"})
    assert result["status"] == "COMPLETED"
    assert "下一步" in result["answer"]
