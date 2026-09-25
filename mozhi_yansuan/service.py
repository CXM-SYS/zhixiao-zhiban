from __future__ import annotations

import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent import ToolCallingResearchAgent


MAX_REQUEST_BYTES = 8 * 1024 * 1024


def analyze_payload(payload: dict[str, Any]) -> dict[str, Any]:
    request_text = str(payload.get("request_text") or payload.get("task_text") or "").strip()
    document_text = str(payload.get("document_text", "")).strip()
    data_csv = str(payload.get("data_csv", "")).strip()
    report_text = str(payload.get("report_text", "")).strip()
    if not request_text:
        raise ValueError("request_text 不能为空")

    with tempfile.TemporaryDirectory(prefix="zhixiao_zhiban_") as temp_dir:
        root = Path(temp_dir)
        task_path = root / "request.md"
        document_path = root / "document.txt"
        data_path = root / "data.csv"
        report_path = root / "report.txt"
        task_path.write_text(request_text, encoding="utf-8")
        if document_text:
            document_path.write_text(document_text, encoding="utf-8")
        if data_csv:
            data_path.write_text(data_csv, encoding="utf-8")
        if report_text:
            report_path.write_text(report_text, encoding="utf-8")
        agent = ToolCallingResearchAgent(root)
        result = agent.run(
            task_path,
            data_path if data_csv else None,
            report_path if report_text else None,
            mode="mock",
            document_path=document_path if document_text else None,
        )
        trace = [
            {
                "tool": item["tool"],
                "arguments": {
                    key: Path(value).name if key.endswith("_path") else value
                    for key, value in item["arguments"].items()
                },
            }
            for item in result["tool_trace"]
        ]
        return {
            "status": result["status"],
            "answer": result["final_output"],
            "tool_trace": trace,
            "agent": "职效智办",
        }


class _Handler(BaseHTTPRequestHandler):
    server_version = "ZhixiaoZhiban/0.2"

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_homepage(self) -> None:
        page = (Path(__file__).parent / "web.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(page)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send_homepage()
            return
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "zhixiao-zhiban"})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self._send_json(404, {"error": "not_found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                raise ValueError("请求体为空或超过8MB限制")
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("请求体必须是JSON对象")
            self._send_json(200, analyze_payload(payload))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
        except Exception as exc:
            self._send_json(400, {"error": type(exc).__name__, "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        # 不把任务、数据和报告内容写入服务日志。
        return


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"职效智办插件服务已启动：http://{host}:{port}")
    print("健康检查：GET /health；办公处理接口：POST /analyze")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
