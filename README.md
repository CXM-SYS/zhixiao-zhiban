# 职效智办

面向会议、文档、表格和汇报材料的职场通用效能智能体 MVP，对应第三届北京市 AI 创新大赛职业发展赛的“职场通用效能智能体”赛题。

## 快速运行

在项目根目录执行：

    python -m mozhi_yansuan agent --task examples/task.md --document examples/meeting_notes.md --data data/demo_workplace_tasks.csv --report examples/report.txt --output reports/agent_demo

离线回放会依次完成需求理解、文档摘要、待办提取、表格检查、汇报依据核验和工作建议。结果位于：

- reports/agent_demo/agent_answer.md
- reports/agent_demo/agent_trace.json

如果要生成带哈希和 HTML 的结构化检查报告，可以执行：

    python -m mozhi_yansuan run --task examples/task.md --data data/demo_workplace_tasks.csv --report examples/report.txt --output reports/demo

## 测试

    python -m pytest -q

如果环境没有 pytest，也可以直接运行：

    python -m unittest discover -s tests

## 扣子接入

coze 目录提供 Bot 提示词、工作流配置和 OpenAPI 插件描述。先本地启动兼容服务：

    python -m mozhi_yansuan serve --host 127.0.0.1 --port 8787

再按 coze/README.md 部署到可公开访问的 HTTPS 地址并导入 coze/openapi.yaml。接口支持只提供需求，也支持附加办公材料、CSV 和汇报材料。

## 当前边界

MVP 优先保证本地、可复现、可追溯，不依赖外部模型 API。自动提取的负责人、日期、完成状态和风险都需要人工确认；正式参赛材料只填写已经实际测试的指标。
