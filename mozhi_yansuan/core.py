from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class Finding:
    finding_id: str
    category: str
    severity: str
    title: str
    detail: str
    source: str
    recommendation: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix in {".csv", ".tsv", ".txt"}:
        separator = "\t" if suffix == ".tsv" else ","
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return pd.read_csv(path, sep=separator, encoding=encoding)
            except UnicodeDecodeError:
                continue
    raise ValueError(f"不支持的数据格式：{path.suffix}。请提供 CSV、TSV 或 Excel 文件。")


def _numeric_tokens(text: str) -> list[str]:
    return re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", text)


class TraceableResearchAgent:
    """本地、可审计的办公材料检查流程。

    它把需求拆解、表格审查和汇报依据提示做成稳定流程，结果绑定到
    输入文件哈希和来源位置，供用户复核。
    """

    def __init__(
        self,
        task_path: Path,
        data_path: Path,
        report_path: Path | None = None,
        code_path: Path | None = None,
    ):
        self.task_path = task_path
        self.data_path = data_path
        self.report_path = report_path
        self.code_path = code_path
        self.findings: list[Finding] = []

    def run(self) -> dict[str, Any]:
        task_text = _read_text(self.task_path)
        frame = read_table(self.data_path)
        report_text = _read_text(self.report_path) if self.report_path else ""
        task = self.extract_task(task_text)
        audit = self.audit_data(frame)
        evidence = self.audit_evidence(frame, report_text)
        recommendations = self.recommend(task, frame)
        inputs: dict[str, Any] = {
            "task": {"path": str(self.task_path), "sha256": sha256_file(self.task_path)},
            "data": {"path": str(self.data_path), "sha256": sha256_file(self.data_path)},
        }
        if self.report_path:
            inputs["report"] = {
                "path": str(self.report_path),
                "sha256": sha256_file(self.report_path),
            }
        if self.code_path:
            inputs["code"] = {
                "path": str(self.code_path),
                "sha256": sha256_file(self.code_path),
            }
        return {
            "agent": "zhixiao-zhiban",
            "version": "0.1.0",
            "inputs": inputs,
            "task": task,
            "data_audit": audit,
            "evidence_audit": evidence,
            "recommendations": recommendations,
            "findings": [asdict(item) for item in self.findings],
            "status": "PASS_WITH_REVIEW" if self.findings else "PASS",
        }

    def extract_task(self, text: str) -> dict[str, Any]:
        lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
        signal_words = (
            "目标", "任务", "问题", "研究", "需要", "约束",
            "限制", "评价", "预测", "分析", "比较",
        )
        objectives = [
            line
            for line in lines
            if not line.startswith("#")
            and not line.endswith(("：", ":"))
            and any(word in line for word in signal_words)
        ]
        constraints = [
            line for line in lines
            if not line.endswith(("：", ":"))
            and any(word in line for word in ("约束", "限制", "必须", "不得", "不超过"))
        ]
        variables: list[str] = []
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{1,30}", text):
            if token.lower() not in {"the", "and", "with", "from", "data", "csv"}:
                if token not in variables:
                    variables.append(token)
        if not objectives:
            objectives = lines[: min(5, len(lines))]
        return {
            "line_count": len(lines),
            "objectives": objectives[:12],
            "constraints": constraints[:12],
            "candidate_variables": variables[:30],
            "source_excerpt": " ".join(lines)[:500],
        }

    def audit_data(self, frame: pd.DataFrame) -> dict[str, Any]:
        audit: dict[str, Any] = {
            "rows": int(frame.shape[0]),
            "columns": int(frame.shape[1]),
            "column_types": {str(name): str(dtype) for name, dtype in frame.dtypes.items()},
            "missing": {},
            "duplicates": int(frame.duplicated().sum()),
            "numeric_summary": {},
            "unit_tokens": {},
        }
        if audit["duplicates"]:
            self.findings.append(Finding(
                "DATA-001", "data", "medium", "存在重复行",
                f"发现 {audit['duplicates']} 行完全重复记录。",
                "data:rows",
                "确认重复是业务记录还是导入错误，并在正式分析前记录处理规则。",
            ))
        for name in frame.columns:
            series = frame[name]
            missing = int(series.isna().sum())
            audit["missing"][str(name)] = missing
            if missing:
                self.findings.append(Finding(
                    f"DATA-M-{len(self.findings)+1:03d}",
                    "data",
                    "medium",
                    f"列“{name}”存在缺失值",
                    f"{missing}/{len(series)} 个单元为空。",
                    f"data:column={name}",
                    "说明缺失机制；根据业务含义选择删除、填补或保留，并记录影响。",
                ))
            tokens = re.findall(
                r"(?:^|[_\-\(\[])(%|kg|mg|km|cm|mm|g|m|元|万元|秒|分钟|小时|c|℃|摄氏)(?:$|[_\-\)\]])",
                str(name),
                flags=re.I,
            )
            if tokens:
                audit["unit_tokens"][str(name)] = tokens
            if pd.api.types.is_numeric_dtype(series):
                clean = series.dropna()
                if not clean.empty:
                    q1, q3 = clean.quantile([0.25, 0.75])
                    iqr = float(q3 - q1)
                    lower, upper = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
                    outlier_count = (
                        int(((clean < lower) | (clean > upper)).sum()) if iqr else 0
                    )
                    audit["numeric_summary"][str(name)] = {
                        "count": int(clean.size),
                        "min": float(clean.min()),
                        "max": float(clean.max()),
                        "mean": float(clean.mean()),
                        "median": float(clean.median()),
                        "std": float(clean.std(ddof=1)) if clean.size > 1 else 0.0,
                        "iqr_outliers": outlier_count,
                    }
                    if outlier_count:
                        self.findings.append(Finding(
                            f"DATA-O-{len(self.findings)+1:03d}",
                            "data",
                            "high",
                            f"列“{name}”疑似存在异常值",
                            f"IQR规则识别到 {outlier_count} 个候选异常值，范围约为 [{lower:.4g}, {upper:.4g}]。",
                            f"data:column={name}",
                            "回到原始记录确认单位、录入和真实极端情况，避免直接删除。",
                        ))
                    if clean.nunique() <= 1:
                        self.findings.append(Finding(
                            f"DATA-C-{len(self.findings)+1:03d}",
                            "data",
                            "low",
                            f"列“{name}”几乎没有变化",
                            "有效数值只有一个取值，可能无法提供解释或预测信息。",
                            f"data:column={name}",
                            "确认该列是否为常量、标识列或应从特征集合中移除。",
                        ))
        if audit["unit_tokens"]:
            self.findings.append(Finding(
                "DATA-UNIT-001",
                "data",
                "low",
                "检测到列名中的单位标记",
                "单位信息已提取，但尚未证明不同列之间口径一致。",
                "data:headers",
                "在分析前建立单位和换算表；跨文件合并时再次检查。",
            ))
        return audit

    def audit_evidence(self, frame: pd.DataFrame, report_text: str) -> dict[str, Any]:
        if not report_text:
            self.findings.append(Finding(
                "EVIDENCE-001",
                "evidence",
                "medium",
                "缺少结果或分析报告",
                "当前只能审查任务和数据，无法建立结果表、图形与文字结论之间的证据关联。",
                "report:missing",
                "补充分析报告、结果表或代码，再运行一次核验。",
            ))
            return {
                "report_provided": False,
                "numeric_anchor_coverage": None,
                "unanchored_claim_lines": [],
            }
        report_numbers = _numeric_tokens(report_text)
        data_numbers: set[str] = set()
        for column in frame.select_dtypes(include="number").columns:
            for value in frame[column].dropna().tolist():
                data_numbers.add(str(round(float(value), 6)))
        matched = 0
        for token in report_numbers:
            raw = token.rstrip("%")
            try:
                candidate = str(round(float(raw), 6))
            except ValueError:
                continue
            if candidate in data_numbers:
                matched += 1
        claim_lines = [
            line.strip()
            for line in report_text.splitlines()
            if not line.lstrip().startswith("#")
            and any(word in line for word in ("因此", "结论", "表明", "显著", "建议"))
        ]
        unanchored = [line for line in claim_lines if not _numeric_tokens(line)]
        for index, line in enumerate(unanchored, start=1):
            self.findings.append(Finding(
                f"EVIDENCE-U-{index:03d}",
                "evidence",
                "medium",
                "结论行缺少可定位数值锚点",
                line[:180],
                f"report:line={index}",
                "补充数据、表格、图形或代码位置，说明该结论的验证依据。",
            ))
        coverage = matched / len(report_numbers) if report_numbers else None
        if coverage is not None and coverage < 0.5:
            self.findings.append(Finding(
                "EVIDENCE-002",
                "evidence",
                "medium",
                "报告数值与数据的直接匹配较少",
                f"报告中的数值锚点匹配率为 {coverage:.1%}。该指标只用于提示，不替代人工复核。",
                "report:numeric_tokens",
                "为关键结论绑定结果表、代码输出或图形文件，并保留运行配置。",
            ))
        return {
            "report_provided": True,
            "report_numeric_tokens": len(report_numbers),
            "matched_numeric_tokens": matched,
            "numeric_anchor_coverage": coverage,
            "unanchored_claim_lines": unanchored,
        }

    def recommend(self, task: dict[str, Any], frame: pd.DataFrame) -> list[dict[str, str]]:
        numeric_count = len(frame.select_dtypes(include="number").columns)
        has_target_signal = any(
            word in task["source_excerpt"]
            for word in ("预测", "分类", "回归", "影响", "优化")
        )
        route = (
            "字段分布、分组统计和可视化"
            if numeric_count < 2
            else "字段分布、分组统计、趋势对比和可视化"
        )
        if has_target_signal:
            route += "；根据业务目标补充分组或趋势验证"
        return [
            {
                "stage": "task",
                "recommendation": "先人工确认任务目标、交付格式和约束，再让智能体生成整理草案。",
            },
            {
                "stage": "data",
                "recommendation": "优先处理缺失、重复、单位和异常值问题，保留处理前后记录。",
            },
            {
                "stage": "analysis",
                "recommendation": route + "，并保留原始汇总结果作为复核基线。",
            },
            {
                "stage": "evidence",
                "recommendation": "每个核心结论绑定数据列、运行记录、结果表或图形位置。",
            },
        ]

    def render_markdown(self, result: dict[str, Any]) -> str:
        lines = [
            "# 职效智办办公材料核验报告",
            "",
            f"> 状态：**{result['status']}**　版本：{result['version']}",
            "",
            "## 1. 输入与可追溯信息",
            "",
        ]
        for name, item in result["inputs"].items():
            lines.append(
                f"- **{name}**：{item['path']}；SHA-256 {item['sha256']}"
            )
        lines += [
            "",
            "## 2. 任务拆解",
            "",
            f"- 任务行数：{result['task']['line_count']}",
            "- 目标/任务线索：",
        ]
        lines += [
            f"  - {item}" for item in result["task"]["objectives"]
        ] or ["  - 未提取到明显目标，请人工补充。"]
        if result["task"]["constraints"]:
            lines.append("- 约束/限制线索：")
            lines += [f"  - {item}" for item in result["task"]["constraints"]]
        lines += [
            "",
            "## 3. 数据审查",
            "",
            f"- 数据规模：{result['data_audit']['rows']} 行 × {result['data_audit']['columns']} 列",
            f"- 完全重复行：{result['data_audit']['duplicates']} 行",
            "",
            "### 数值列摘要",
            "",
            "| 列 | 最小值 | 最大值 | 均值 | 中位数 | IQR候选异常 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for name, stats in result["data_audit"]["numeric_summary"].items():
            lines.append(
                f"| {name} | {stats['min']:.4g} | {stats['max']:.4g} | "
                f"{stats['mean']:.4g} | {stats['median']:.4g} | "
                f"{stats['iqr_outliers']} |"
            )
        lines += ["", "## 4. 证据核验", ""]
        evidence = result["evidence_audit"]
        if not evidence["report_provided"]:
            lines.append(
                "当前未提供分析报告、结果表或代码，因此无法完成结果—结论核验。"
            )
        else:
            coverage = evidence["numeric_anchor_coverage"]
            if coverage is not None:
                lines.append(
                    f"- 报告数值锚点：{evidence['matched_numeric_tokens']}/"
                    f"{evidence['report_numeric_tokens']}；直接匹配率：{coverage:.1%}"
                )
            else:
                lines.append("- 报告中未发现可比较的数值锚点。")
            if evidence["unanchored_claim_lines"]:
                lines.append("- 缺少数值锚点的结论行：")
                lines += [
                    f"  - {item}" for item in evidence["unanchored_claim_lines"]
                ]
        lines += ["", "## 5. 建议分析路线", ""]
        lines += [
            f"- **{item['stage']}**：{item['recommendation']}"
            for item in result["recommendations"]
        ]
        lines += [
            "",
            "## 6. 待处理问题",
            "",
            "| 编号 | 严重度 | 类型 | 问题 | 来源 | 建议 |",
            "|---|---|---|---|---|---|",
        ]
        if result["findings"]:
            for item in result["findings"]:
                lines.append(
                    f"| {item['finding_id']} | {item['severity']} | "
                    f"{item['category']} | {item['title']}：{item['detail']} | "
                    f"{item['source']} | {item['recommendation']} |"
                )
        else:
            lines.append(
                "| - | - | - | 未发现自动规则触发的问题 | - | "
                "仍需人工确认任务口径与业务含义。 |"
            )
        lines += [
            "",
            "## 7. 人工复核声明",
            "",
            "本报告用于辅助办公检查，不替代用户对数据、结论、附件和版权合规性的最终判断。"
            "正式发送或归档前应保存原始输入、运行配置和人工复核记录。",
            "",
        ]
        return "\n".join(lines)

    def render_html(self, result: dict[str, Any]) -> str:
        markdown = self.render_markdown(result)
        body = html.escape(markdown).replace("\n", "<br>\n")
        return (
            "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
            "<title>职效智办报告</title>"
            "<style>body{max-width:1100px;margin:40px auto;padding:0 24px;"
            "font:15px/1.7 system-ui,sans-serif;color:#182230;background:#f6f8fb}"
            "pre{white-space:pre-wrap;background:white;border:1px solid #d9e1ec;"
            "border-radius:12px;padding:24px;box-shadow:0 8px 30px #1c355710}"
            "</style><pre>"
            f"{body}</pre></html>"
        )


def write_outputs(
    result: dict[str, Any],
    output_dir: Path,
    agent: TraceableResearchAgent,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_md = output_dir / "analysis_report.md"
    report_html = output_dir / "analysis_report.html"
    manifest = output_dir / "run_manifest.json"
    report_md.write_text(agent.render_markdown(result), encoding="utf-8")
    report_html.write_text(agent.render_html(result), encoding="utf-8")
    manifest.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "markdown": str(report_md),
        "html": str(report_html),
        "manifest": str(manifest),
    }
