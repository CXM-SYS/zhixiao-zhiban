from __future__ import annotations

import re
from typing import Any


DATE_PATTERN = re.compile(
    r"(20\d{2}[年/-]\d{1,2}[月/-]\d{1,2}[日]?|"
    r"\d{1,2}[月/-]\d{1,2}[日]?|今天|明天|本周|下周)"
)


def extract_action_items(text: str) -> dict[str, Any]:
    """从办公材料中提取待办线索，不把启发式结果冒充正式任务。"""
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    action_words = (
        "负责", "完成", "跟进", "提交", "确认", "整理", "准备",
        "发送", "联系", "审核", "更新", "安排", "处理", "推进",
    )
    items: list[dict[str, Any]] = []
    for line in lines:
        if line.startswith("#") or re.match(r"^(目标|约束|任务|说明)\s*[:：]", line):
            continue
        if not any(word in line for word in action_words):
            continue
        deadline = DATE_PATTERN.search(line)
        owner = None
        owner_match = re.search(
            r"(?:^|[：:，,、\s])([\u4e00-\u9fff]{2,4}?)\s*"
            r"(?=负责|跟进|确认|整理|提交|更新|准备|完成)",
            line,
        )
        if not owner_match:
            owner_match = re.search(r"(?:负责人|由|@)\s*([^\s，。,；;:：、]+)", line)
        if owner_match:
            owner = owner_match.group(1)
        items.append({
            "item": line[:200],
            "owner": owner or "待确认",
            "deadline": deadline.group(1) if deadline else "待确认",
            "status": "待确认",
            "source_line": lines.index(line) + 1,
        })
    return {
        "line_count": len(lines),
        "action_item_count": len(items),
        "items": items[:30],
        "needs_human_confirmation": True,
    }


def summarize_document(text: str) -> dict[str, Any]:
    """生成可审计的轻量文档摘要，保留原文线索而不虚构事实。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    headings = [
        line.lstrip("#").strip()
        for line in lines
        if line.startswith("#")
    ]
    content = [
        line for line in lines
        if not line.startswith("#") and len(line) >= 8
    ]
    return {
        "line_count": len(lines),
        "headings": headings[:20],
        "key_points": content[:8],
        "summary": "；".join(content[:4])[:600] if content else "未提取到足够正文。",
        "source_preserved": True,
        "needs_human_confirmation": True,
    }
