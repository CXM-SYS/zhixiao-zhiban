from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .core import TraceableResearchAgent, read_table
from .workplace import extract_action_items, summarize_document


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "extract_task_requirements",
        "description": "读取用户需求，提取办公目标、限制条件和交付物线索。",
        "parameters": {
            "type": "object",
            "properties": {"task_path": {"type": "string"}},
            "required": ["task_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "summarize_document",
        "description": "读取会议记录、通知或业务材料，生成保留原文线索的摘要。",
        "parameters": {
            "type": "object",
            "properties": {"document_path": {"type": "string"}},
            "required": ["document_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "extract_action_items",
        "description": "从办公材料中提取待办事项、负责人和截止时间线索。",
        "parameters": {
            "type": "object",
            "properties": {"document_path": {"type": "string"}},
            "required": ["document_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_dataset",
        "description": "读取CSV、TSV或Excel表格，检查缺失值、重复行、数值摘要、异常值和单位标记。",
        "parameters": {
            "type": "object",
            "properties": {"data_path": {"type": "string"}},
            "required": ["data_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "audit_evidence",
        "description": "把汇报材料中的数值和结论与表格进行初步匹配，提示缺少依据的结论。",
        "parameters": {
            "type": "object",
            "properties": {
                "data_path": {"type": "string"},
                "report_path": {"type": "string"},
            },
            "required": ["data_path", "report_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "recommend_analysis_route",
        "description": "结合办公需求和表格字段，给出数据整理、统计和汇报步骤。",
        "parameters": {
            "type": "object",
            "properties": {
                "task_path": {"type": "string"},
                "data_path": {"type": "string"},
            },
            "required": ["task_path", "data_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


AGENT_INSTRUCTIONS = """你是“职效智办”，面向日常办公场景的通用效能智能体。
你负责理解需求、整理文档、提取待办、检查表格和核验汇报依据，并把结果组织成可直接复核的工作清单。
工作规则：
1. 必须先调用 extract_task_requirements 理解用户需求。
2. 有会议记录或办公材料时，调用 summarize_document 和 extract_action_items。
3. 有表格时，调用 inspect_dataset；同时提供汇报材料时，调用 audit_evidence。
4. 需要统计或整理建议时，调用 recommend_analysis_route。
5. 不得编造数据结果、完成状态、负责人、截止时间或用户反馈；无法确认的内容写成“待确认”。
6. 最终回答用中文，包含任务理解、文档摘要与待办、数据发现、风险提示、建议动作和人工确认事项。
7. 工具返回的是辅助线索，来源位置和文件指纹用于复核，不能把自动提示直接写成确定事实。
"""


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _dump_item(item: Any) -> Any:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return item


class ResearchToolRegistry:
    """只读办公工具集合；不执行用户代码，也不修改输入文件。"""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.functions: dict[str, Callable[..., dict[str, Any]]] = {
            "extract_task_requirements": self.extract_task_requirements,
            "summarize_document": self.summarize_document,
            "extract_action_items": self.extract_action_items,
            "inspect_dataset": self.inspect_dataset,
            "audit_evidence": self.audit_evidence,
            "recommend_analysis_route": self.recommend_analysis_route,
        }

    def _safe_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{path}")
        try:
            path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise PermissionError(f"工具只允许读取工作区内文件：{path}") from exc
        return path

    def extract_task_requirements(self, task_path: str) -> dict[str, Any]:
        task = self._safe_path(task_path)
        helper = TraceableResearchAgent(task, task)
        text = task.read_text(encoding="utf-8")
        return {"task_path": str(task), "requirements": helper.extract_task(text)}

    def summarize_document(self, document_path: str) -> dict[str, Any]:
        document = self._safe_path(document_path)
        result = summarize_document(document.read_text(encoding="utf-8"))
        return {"document_path": str(document), "summary": result}

    def extract_action_items(self, document_path: str) -> dict[str, Any]:
        document = self._safe_path(document_path)
        result = extract_action_items(document.read_text(encoding="utf-8"))
        return {"document_path": str(document), "actions": result}

    def inspect_dataset(self, data_path: str) -> dict[str, Any]:
        data = self._safe_path(data_path)
        frame = read_table(data)
        helper = TraceableResearchAgent(data, data)
        findings_before = len(helper.findings)
        audit = helper.audit_data(frame)
        return {
            "data_path": str(data),
            "rows": int(frame.shape[0]),
            "columns": int(frame.shape[1]),
            "audit": audit,
            "findings": [item.__dict__ for item in helper.findings[findings_before:]],
        }

    def audit_evidence(self, data_path: str, report_path: str) -> dict[str, Any]:
        data = self._safe_path(data_path)
        report = self._safe_path(report_path)
        frame = read_table(data)
        helper = TraceableResearchAgent(data, data, report)
        result = helper.audit_evidence(frame, report.read_text(encoding="utf-8"))
        return {
            "data_path": str(data),
            "report_path": str(report),
            "evidence": result,
            "findings": [item.__dict__ for item in helper.findings],
        }

    def recommend_analysis_route(self, task_path: str, data_path: str) -> dict[str, Any]:
        task = self._safe_path(task_path)
        data = self._safe_path(data_path)
        frame = read_table(data)
        helper = TraceableResearchAgent(task, data)
        parsed = helper.extract_task(task.read_text(encoding="utf-8"))
        numeric_columns = [str(name) for name in frame.select_dtypes(include="number").columns]
        text_columns = [str(name) for name in frame.columns if str(name) not in numeric_columns]
        recommendations = [
            {
                "stage": "口径确认",
                "recommendation": "确认交付物、统计口径、负责人和截止时间；未明确的信息保留为待确认。",
            },
            {
                "stage": "数据整理",
                "recommendation": "先处理缺失、重复、单位和候选异常值，并保留处理记录。",
            },
            {
                "stage": "统计汇总",
                "recommendation": (
                    f"数值字段包括{','.join(numeric_columns) or '无'}，可生成汇总指标和分组对比；"
                    f"文本字段包括{','.join(text_columns) or '无'}，适合用作分类或负责人维度。"
                ),
            },
            {
                "stage": "汇报输出",
                "recommendation": "把每项结论绑定到表格字段、原始记录或图表，并列出风险和下一步。",
            },
        ]
        return {
            "task_path": str(task),
            "data_path": str(data),
            "task_excerpt": parsed["source_excerpt"],
            "recommendations": recommendations,
        }

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self.functions:
            raise ValueError(f"未知工具：{name}")
        return self.functions[name](**arguments)


class ToolCallingResearchAgent:
    """通用办公工具调用智能体，支持真实模型与离线回放。"""

    def __init__(
        self,
        workspace_root: Path,
        model: str = "gpt-5",
        max_turns: int = 8,
    ):
        self.workspace_root = workspace_root.resolve()
        self.model = model
        self.max_turns = max_turns
        self.registry = ResearchToolRegistry(self.workspace_root)

    def run(
        self,
        task_path: Path,
        data_path: Path | None = None,
        report_path: Path | None = None,
        mode: str = "mock",
        document_path: Path | None = None,
    ) -> dict[str, Any]:
        if mode == "mock":
            return self._run_mock(task_path, data_path, report_path, document_path)
        if mode == "openai":
            return self._run_openai(task_path, data_path, report_path, document_path)
        raise ValueError("mode 必须是 mock 或 openai")

    def _context_prompt(
        self,
        task_path: Path,
        data_path: Path | None,
        report_path: Path | None,
        document_path: Path | None,
    ) -> str:
        lines = [
            "请处理以下办公输入并生成最终中文工作报告。",
            f"用户需求文件：{task_path.resolve()}",
            f"办公材料文件：{document_path.resolve() if document_path else '无'}",
            f"数据表格文件：{data_path.resolve() if data_path else '无'}",
            f"汇报材料文件：{report_path.resolve() if report_path else '无'}",
            "请根据实际提供的材料先调用工具，不要直接猜测。",
        ]
        return "\n".join(lines)

    def _run_mock(
        self,
        task_path: Path,
        data_path: Path | None,
        report_path: Path | None,
        document_path: Path | None,
    ) -> dict[str, Any]:
        calls: list[dict[str, Any]] = []
        source_document = document_path or task_path
        plan: list[tuple[str, dict[str, Any]]] = [
            ("extract_task_requirements", {"task_path": str(task_path.resolve())}),
        ]
        if document_path:
            plan.append((
                "summarize_document",
                {"document_path": str(document_path.resolve())},
            ))
        plan.append((
            "extract_action_items",
            {"document_path": str(source_document.resolve())},
        ))
        if data_path:
            plan.append(("inspect_dataset", {"data_path": str(data_path.resolve())}))
            if report_path:
                plan.append((
                    "audit_evidence",
                    {
                        "data_path": str(data_path.resolve()),
                        "report_path": str(report_path.resolve()),
                    },
                ))
            plan.append((
                "recommend_analysis_route",
                {
                    "task_path": str(task_path.resolve()),
                    "data_path": str(data_path.resolve()),
                },
            ))
        for name, arguments in plan:
            output = self.registry.call(name, arguments)
            calls.append({"tool": name, "arguments": arguments, "output": output})
        final = self._mock_final(calls, report_without_data=bool(report_path and not data_path))
        return {
            "mode": "mock",
            "model": "deterministic-tool-replay",
            "final_output": final,
            "tool_trace": calls,
            "status": "COMPLETED",
        }

    def _mock_final(
        self,
        calls: list[dict[str, Any]],
        report_without_data: bool = False,
    ) -> str:
        by_name = {item["tool"]: item["output"] for item in calls}
        req = by_name["extract_task_requirements"]["requirements"]
        actions = by_name["extract_action_items"]["actions"]
        summary = by_name.get("summarize_document", {}).get("summary")
        lines = [
            "# 职效智办工作效率报告",
            "",
            "## 任务理解",
            f"- 目标线索：{'；'.join(req['objectives'][:5]) or '待人工补充'}",
            f"- 限制条件：{'；'.join(req['constraints'][:5]) or '待人工确认'}",
            "",
            "## 文档摘要与待办",
        ]
        if summary:
            lines.append(f"- 摘要：{summary['summary']}")
            if summary["headings"]:
                lines.append(f"- 文档结构：{'、'.join(summary['headings'])}")
        else:
            lines.append("- 未单独提供办公材料，待办线索从用户需求中提取。")
        if actions["items"]:
            for item in actions["items"]:
                lines.append(
                    f"- 待办：{item['item']}｜负责人：{item['owner']}｜"
                    f"截止：{item['deadline']}｜来源行：{item['source_line']}"
                )
        else:
            lines.append("- 未识别到明确待办，请人工补充负责人和截止时间。")

        lines += ["", "## 数据发现"]
        if "inspect_dataset" in by_name:
            audit = by_name["inspect_dataset"]["audit"]
            findings = by_name["inspect_dataset"]["findings"]
            lines.extend([
                f"- 数据规模：{audit['rows']} 行 × {audit['columns']} 列。",
                f"- 完全重复行：{audit['duplicates']} 行。",
                f"- 缺失值统计：{json.dumps(audit['missing'], ensure_ascii=False)}。",
            ])
            if findings:
                lines.append("- 自动提示：")
                lines.extend([f"  - {item['title']}：{item['detail']}" for item in findings])
        else:
            lines.append("- 未提供表格，本次不执行数据统计与质量检查。")

        lines += ["", "## 风险提示"]
        evidence = by_name.get("audit_evidence", {}).get("evidence")
        if evidence:
            lines.append(
                f"- 汇报材料是否提供：{evidence['report_provided']}；"
                f"数值锚点匹配率：{evidence['numeric_anchor_coverage']!s}。"
            )
            lines.extend([
                f"  - 缺少依据线索的结论：{item}"
                for item in evidence["unanchored_claim_lines"]
            ])
        elif report_without_data:
            lines.append("- 已提供汇报材料，但缺少数据表格，无法核对其中的数值和结论。")
        else:
            lines.append("- 未同时提供表格与汇报材料，本次不执行结论依据核验。")

        lines += ["", "## 建议动作"]
        routes = by_name.get("recommend_analysis_route", {}).get("recommendations", [])
        if routes:
            lines.extend([f"- {item['stage']}：{item['recommendation']}" for item in routes])
        else:
            lines.append("- 先确认交付物、负责人和截止时间，再按待办清单推进。")
        lines += [
            "",
            "## 人工确认事项",
            "- 自动提取的负责人、日期、异常值和风险均需回到原始材料确认。",
            "- 未明确的任务状态统一保留为待确认，不自动标记为已完成。",
            "- 对外发送前，请复核敏感信息、数字口径、附件版本和收件人。",
        ]
        return "\n".join(lines)

    def _run_openai(
        self,
        task_path: Path,
        data_path: Path | None,
        report_path: Path | None,
        document_path: Path | None,
    ) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "缺少OpenAI SDK。请执行：pip install -e \".[agent]\""
            ) from exc
        client = OpenAI()
        transcript: list[Any] = [{
            "role": "user",
            "content": self._context_prompt(task_path, data_path, report_path, document_path),
        }]
        trace: list[dict[str, Any]] = []
        for turn in range(1, self.max_turns + 1):
            response = client.responses.create(
                model=self.model,
                instructions=AGENT_INSTRUCTIONS,
                input=transcript,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                parallel_tool_calls=False,
                max_output_tokens=3000,
                store=False,
                include=["reasoning.encrypted_content"],
            )
            output_items = list(getattr(response, "output", []) or [])
            transcript.extend([_dump_item(item) for item in output_items])
            calls = [item for item in output_items if _get(item, "type") == "function_call"]
            if not calls:
                return {
                    "mode": "openai",
                    "model": self.model,
                    "final_output": getattr(response, "output_text", "") or "",
                    "tool_trace": trace,
                    "turns": turn,
                    "response_id": getattr(response, "id", None),
                    "status": "COMPLETED",
                }
            for call in calls:
                name = _get(call, "name")
                call_id = _get(call, "call_id")
                raw_args = _get(call, "arguments", "{}")
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                try:
                    tool_output = self.registry.call(name, arguments)
                except Exception as exc:
                    tool_output = {"error": type(exc).__name__, "message": str(exc)}
                trace.append({
                    "turn": turn,
                    "tool": name,
                    "arguments": arguments,
                    "output": tool_output,
                })
                transcript.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(tool_output, ensure_ascii=False),
                })
        raise RuntimeError(f"智能体在 {self.max_turns} 轮内未生成最终答复")


def write_agent_outputs(result: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    answer = output_dir / "agent_answer.md"
    trace = output_dir / "agent_trace.json"
    answer.write_text(result["final_output"], encoding="utf-8")
    trace.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"answer": str(answer), "trace": str(trace)}
