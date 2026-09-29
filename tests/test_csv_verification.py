from pathlib import Path

import pytest

from mozhi_yansuan.csv_verification import verified_office_csv


DEMO = Path(__file__).resolve().parents[1] / "examples" / "video_demo"


def test_video_demo_is_checked_from_all_raw_rows() -> None:
    result = verified_office_csv(
        (DEMO / "tasks.csv").read_text(encoding="utf-8"),
        (DEMO / "report.txt").read_text(encoding="utf-8"),
    )
    assert result is not None
    assert "6+8+5+3+4+6+2+3 = 37 小时" in result
    assert "登记工时合计 37 小时”：有数据支持" in result
    assert "进行中 5 条、未开始 1 条、已完成 2 条" in result
    assert "第 6 条与第 1 条相同" in result
    assert "负责人缺失 1 条" in result
    assert result.count("与数据不一致") == 3


def test_invalid_hours_cannot_be_silently_excluded_from_total() -> None:
    result = verified_office_csv(
        "任务,负责人,工时,状态\n甲,李宁,6,进行中\n乙,王芳,NaN,已完成\n",
        "登记工时合计 6 小时。",
    )
    assert result is not None
    assert "不能计算完整合计" in result
    assert "无法判定" in result


def test_other_schema_uses_the_existing_agent_route() -> None:
    assert verified_office_csv("borough,count\nQueens,9\n") is None


def test_malformed_csv_is_rejected() -> None:
    with pytest.raises(ValueError, match="列数"):
        verified_office_csv("任务,负责人,工时,状态\n甲,李宁,6\n")
