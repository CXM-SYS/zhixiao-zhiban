import json
from io import BytesIO
from unittest.mock import patch

import pytest

from mozhi_yansuan.bailian import ask_agent, is_configured


def test_bailian_is_disabled_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("BAILIAN_APP_ID", raising=False)
    assert not is_configured()
    with pytest.raises(RuntimeError, match="尚未配置"):
        ask_agent({"request_text": "整理会议"})


def test_bailian_uses_published_agent_and_keeps_key_in_header(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-secret")
    monkeypatch.setenv("BAILIAN_APP_ID", "test-app")
    response = BytesIO(json.dumps({"output": {"text": "已核对来源"}}).encode())
    with patch("mozhi_yansuan.bailian.urlopen", return_value=response) as open_mock:
        result = ask_agent({"request_text": "核验汇报", "data_csv": "count\n20"})

    request = open_mock.call_args.args[0]
    assert request.full_url == "https://dashscope.aliyuncs.com/api/v1/apps/test-app/completion"
    assert request.get_header("Authorization") == "Bearer test-secret"
    assert "test-secret" not in request.data.decode()
    prompt = json.loads(request.data.decode())["input"]["prompt"]
    assert json.loads(prompt.split("\n", 1)[1])["CSV数据"] == "count\n20"
    assert result["answer"] == "已核对来源"


def test_office_csv_still_calls_agent_without_using_model_arithmetic(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-secret")
    monkeypatch.setenv("BAILIAN_APP_ID", "test-app")
    data = "任务,负责人,工时,状态\n甲,李宁,6,进行中\n甲,李宁,6,进行中\n"
    response = BytesIO(json.dumps({"output": {"text": "请确认重复记录是否应保留。"}}).encode())
    with patch("mozhi_yansuan.bailian.urlopen", return_value=response) as open_mock:
        result = ask_agent({
            "request_text": "核验汇报",
            "data_csv": data,
            "report_text": "登记工时合计 12 小时，没有重复记录。",
        })
    open_mock.assert_called_once()
    assert "6+6 = 12 小时" in result["answer"]
    assert "完全重复 1 条" in result["answer"]
    assert "请确认重复记录是否应保留" in result["answer"]


def test_wrong_model_numbers_are_excluded_from_checked_csv(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-secret")
    monkeypatch.setenv("BAILIAN_APP_ID", "test-app")
    response = BytesIO(json.dumps({"output": {"text": "实际只有 6 小时。"}}).encode())
    with patch("mozhi_yansuan.bailian.urlopen", return_value=response):
        result = ask_agent({
            "request_text": "核验汇报",
            "data_csv": "任务,负责人,工时,状态\n甲,李宁,6,进行中\n乙,王芳,8,已完成\n",
            "report_text": "登记工时合计 14 小时。",
        })
    assert "6+8 = 14 小时" in result["answer"]
    assert "实际只有 6 小时" not in result["answer"]


def test_document_model_cannot_recount_office_csv(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-secret")
    monkeypatch.setenv("BAILIAN_APP_ID", "test-app")
    response = BytesIO(json.dumps({"output": {"text": "李宁负责整理材料。"}}).encode())
    with patch("mozhi_yansuan.bailian.urlopen", return_value=response) as open_mock:
        result = ask_agent({
            "request_text": "整理会议并核验汇报",
            "document_text": "李宁负责整理材料。",
            "data_csv": "任务,负责人,工时,状态\n甲,李宁,6,进行中\n",
            "report_text": "登记工时合计 6 小时。",
        })
    prompt = json.loads(open_mock.call_args.args[0].data.decode())["input"]["prompt"]
    assert json.loads(prompt.split("\n", 1)[1])["CSV数据"] == ""
    assert "李宁负责整理材料" in result["answer"]
    assert "原始合计：6 = 6 小时" in result["answer"]
