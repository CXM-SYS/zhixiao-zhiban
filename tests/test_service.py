from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen

from mozhi_yansuan.service import _Handler, analyze_payload


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


def test_homepage_is_available_to_public_visitors() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "职效智办" in page
            assert "aiAgentReady ? '/agent' : '/analyze'" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
