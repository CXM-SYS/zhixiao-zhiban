"""Optional connection to a published Model Studio Agent 2.0 application."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_AGENT_INPUT_CHARS = 12000


def is_configured() -> bool:
    return bool(os.getenv("DASHSCOPE_API_KEY") and os.getenv("BAILIAN_APP_ID"))


def ask_agent(payload: dict[str, str]) -> dict[str, str]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    app_id = os.getenv("BAILIAN_APP_ID", "")
    if not api_key or not app_id:
        raise RuntimeError("百炼智能体尚未配置")

    fields = {
        "用户需求": str(payload.get("request_text") or payload.get("task_text") or "").strip(),
        "办公材料": str(payload.get("document_text") or "").strip(),
        "CSV数据": str(payload.get("data_csv") or "").strip(),
        "待核验汇报": str(payload.get("report_text") or "").strip(),
    }
    if not fields["用户需求"]:
        raise ValueError("request_text 不能为空")
    prompt = "请根据以下用户材料完成办公分析；需要统计或核验时先调用已配置的职效智办分析工具，不要编造数字或完成状态。\n" + json.dumps(fields, ensure_ascii=False)
    if len(prompt) > MAX_AGENT_INPUT_CHARS:
        raise ValueError("发送给智能体的内容过长，请缩减至约1.2万字以内")

    request_body = json.dumps({"input": {"prompt": prompt}, "parameters": {}, "debug": {}}, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"https://dashscope.aliyuncs.com/api/v1/apps/{app_id}/completion",
        data=request_body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"百炼调用失败（HTTP {exc.code}）；请在百炼控制台检查应用发布状态与额度") from exc
    except URLError as exc:
        raise RuntimeError("暂时无法连接百炼，请稍后重试") from exc
    output = result.get("output") or {}
    answer = output.get("text")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("百炼未返回有效答复，请检查智能体配置")
    return {"status": "COMPLETED", "answer": answer, "agent": "职效智办·百炼智能体"}
