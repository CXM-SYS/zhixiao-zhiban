from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .agent import ToolCallingResearchAgent, write_agent_outputs
from .core import TraceableResearchAgent, write_outputs
from .service import serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mozhi-yansuan",
        description="职效智办：可复核的职场通用效能智能体",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="运行一次任务、数据和证据核验")
    run.add_argument("--task", required=True, type=Path, help="任务说明文本文件")
    run.add_argument("--data", required=True, type=Path, help="CSV、TSV 或 Excel 数据文件")
    run.add_argument("--report", type=Path, help="可选：分析报告或结果说明文本")
    run.add_argument("--code", type=Path, help="可选：分析代码文件，仅用于建立输入指纹")
    run.add_argument("--output", required=True, type=Path, help="输出目录")
    run.add_argument("--json-only", action="store_true", help="只在终端打印JSON，不写报告文件")
    agent = sub.add_parser("agent", help="运行通用办公工具调用智能体")
    agent.add_argument("--task", required=True, type=Path, help="用户需求文本文件")
    agent.add_argument("--document", type=Path, help="可选：会议记录、通知或其他办公材料")
    agent.add_argument("--data", type=Path, help="可选：CSV、TSV 或 Excel 数据文件")
    agent.add_argument("--report", type=Path, help="可选：需要核验的汇报材料")
    agent.add_argument("--output", required=True, type=Path, help="输出目录")
    agent.add_argument("--mode", choices=("mock", "openai"), default="mock", help="mock离线回放或openai真实模型")
    agent.add_argument("--model", default="gpt-5", help="Responses API模型名")
    agent.add_argument("--max-turns", type=int, default=6, help="最大工具调用轮数")
    service = sub.add_parser("serve", help="启动扣子插件兼容的本地HTTP服务")
    service.add_argument("--host", default="127.0.0.1")
    service.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8787")),
        help="监听端口；云平台会通过PORT环境变量注入",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "agent":
        for supplied in (args.task, args.document, args.data, args.report):
            if supplied and not supplied.exists():
                raise SystemExit(f"输入文件不存在：{supplied}")
        agent = ToolCallingResearchAgent(Path.cwd(), args.model, args.max_turns)
        result = agent.run(
            args.task,
            args.data,
            args.report,
            args.mode,
            document_path=args.document,
        )
        outputs = write_agent_outputs(result, args.output)
        print(json.dumps({"status": result["status"], "outputs": outputs, "mode": result["mode"]}, ensure_ascii=False, indent=2))
        return
    if args.command == "serve":
        serve(args.host, args.port)
        return
    if args.command != "run":
        return
    for required in (args.task, args.data):
        if not required.exists():
            raise SystemExit(f"输入文件不存在：{required}")
    agent = TraceableResearchAgent(args.task, args.data, args.report, args.code)
    result = agent.run()
    if args.json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    outputs = write_outputs(result, args.output, agent)
    print(json.dumps(
        {
            "status": result["status"],
            "outputs": outputs,
            "finding_count": len(result["findings"]),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
