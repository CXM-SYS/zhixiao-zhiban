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
