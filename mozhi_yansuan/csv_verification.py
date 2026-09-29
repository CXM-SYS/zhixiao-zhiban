"""Deterministic checks for the office-task CSV used by the public demo."""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from decimal import Decimal, InvalidOperation


def _number(value: Decimal) -> str:
    return format(value, "f").rstrip("0").rstrip(".") if value % 1 else str(int(value))


def _parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    nonempty = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not nonempty:
        raise ValueError("CSV 为空，请提供包含表头的数据")
    headers = [cell.strip().lstrip("\ufeff") for cell in nonempty[0]]
    if not all(headers) or len(headers) != len(set(headers)):
        raise ValueError("CSV 表头不能为空或重复")
    rows = nonempty[1:]
    if any(len(row) != len(headers) for row in rows):
        raise ValueError("CSV 数据行的列数与表头不一致，请检查逗号和引号")
    return headers, rows


def verified_office_csv(data_csv: str, report_text: str = "") -> str | None:
    """Return a checked report for task sheets, or None for other CSV schemas.

    This route deliberately does not ask a language model to add numbers. It
    preserves raw rows, including suspected duplicates, until a person decides.
    """
    headers, rows = _parse_csv(data_csv)
    if not {"任务", "负责人", "工时", "状态"}.issubset(headers):
        return None

    index = {name: headers.index(name) for name in headers}
    count = len(rows)
    task_count = len({row[index["任务"]].strip() for row in rows})
    statuses = Counter(row[index["状态"]].strip() or "（空）" for row in rows)
    missing_owners = [i for i, row in enumerate(rows, 1) if not row[index["负责人"]].strip()]
    first_seen: dict[tuple[str, ...], int] = {}
    duplicates: list[tuple[int, int]] = []
    for i, row in enumerate(rows, 1):
        key = tuple(row)
        if key in first_seen:
            duplicates.append((first_seen[key], i))
        else:
            first_seen[key] = i

    hours: list[Decimal] = []
    invalid_hours: list[int] = []
    for i, row in enumerate(rows, 1):
        try:
            value = Decimal(row[index["工时"]].strip())
            if not value.is_finite():
                raise InvalidOperation
            hours.append(value)
        except InvalidOperation:
            invalid_hours.append(i)
    total = sum(hours, Decimal(0)) if not invalid_hours else None

    lines = [
        "## CSV 程序核验（按原始数据行，未去重）",
        f"- 表头之后有 {count} 条记录；按“任务”字段区分有 {task_count} 类。",
    ]
    if total is None:
        lines.append(f"- 工时列第 {', '.join(map(str, invalid_hours))} 条不是有效数字，不能计算完整合计。")
    else:
        expression = "+".join(_number(value) for value in hours)
        lines.append(f"- 登记工时原始合计：{expression} = {_number(total)} 小时（包含所有原始行）。")
    status_text = "、".join(f"{name} {amount} 条" for name, amount in statuses.items())
    lines.append(f"- 状态分布：{status_text}；合计 {sum(statuses.values())} 条。")
    lines.append(
        f"- 负责人缺失：{len(missing_owners)} 条"
        + (f"（数据第 {', '.join(map(str, missing_owners))} 条）" if missing_owners else "")
        + "。"
    )
    lines.append(
        f"- 完全重复：{len(duplicates)} 条"
        + ("（" + "、".join(f"第 {later} 条与第 {earlier} 条相同" for earlier, later in duplicates) + "）" if duplicates else "")
        + "；这里只提示，不自动删除。"
    )

    claims = [item.strip() for item in re.split(r"[。；;，,\n]+", report_text) if item.strip()]
    if claims:
        lines.append("\n## 汇报草稿逐条核验")
    for claim in claims:
        verdict = "待人工核验：这句话不属于当前可自动判定的口径。"
        record_match = re.search(r"(?:共有|共计|共)\s*(\d+)\s*条记录", claim)
        hour_match = re.search(r"工时(?:合计|总计|累计|为)?\s*(\d+(?:\.\d+)?)\s*小时", claim)
        if record_match:
            stated = int(record_match.group(1))
            verdict = f"{'有数据支持' if stated == count else '与数据不一致'}：CSV 表头后有 {count} 条原始记录。"
        elif hour_match:
            stated = Decimal(hour_match.group(1))
            if total is None:
                verdict = "无法判定：工时列含非数字，需先确认原始记录。"
            else:
                verdict = f"{'有数据支持' if stated == total else '与数据不一致'}：原始记录工时合计 {_number(total)} 小时；重复行尚未删除。"
        elif re.search(r"(?:所有|全部|每条).*(?:任务|记录).*?(?:已完成|完成)", claim):
            completed = statuses.get("已完成", 0)
            verdict = f"{'有数据支持' if completed == count else '与数据不一致'}：已完成 {completed}/{count} 条。"
        elif re.search(r"(?:所有|全部|每条).*(?:任务|记录).*负责人", claim):
            verdict = f"{'有数据支持' if not missing_owners else '与数据不一致'}：负责人缺失 {len(missing_owners)} 条。"
        elif re.search(r"(?:没有|无|不存在).*(?:重复|相同).*记录", claim):
            verdict = f"{'有数据支持' if not duplicates else '与数据不一致'}：完全重复 {len(duplicates)} 条。"
        lines.append(f"- “{claim}”：{verdict}")

    lines.append("\n## 人工确认事项")
    if duplicates:
        lines.append("- 确认重复记录是否为导出错误或真实业务记录；核实前保留原始合计。")
    if missing_owners:
        lines.append("- 补充或解释负责人为空的任务。")
    if invalid_hours:
        lines.append("- 核对非数字工时及其单位，确认后重新计算。")
    lines.append("- 对外发布前，核对 CSV 版本、任务状态和未能自动判定的结论。")
    return "\n".join(lines)
