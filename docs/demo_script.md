# 职效智办两到三分钟演示脚本

## 0:00—0:25：问题

展示一段周会材料和任务表，说明办公信息分散在纪要、表格和周报中，人工整理容易漏掉负责人、日期和数据问题。

## 0:25—0:50：输入

在项目根目录运行：

    python -m mozhi_yansuan agent --task examples/task.md --document examples/meeting_notes.md --data data/demo_workplace_tasks.csv --report examples/report.txt --output reports/agent_demo

说明本次输入包含用户需求、办公材料、CSV 任务表和周报草稿。

## 0:50—1:55：结果

打开 `reports/agent_demo/agent_answer.md`，依次展示：

1. 任务目标和限制条件；
2. 文档摘要和待办事项；
3. 负责人、截止时间和来源行；
4. 表格缺失值、重复行和候选异常提示；
5. 周报结论的依据提示；
6. 建议动作和人工确认事项。

再打开 `reports/agent_demo/agent_trace.json`，展示工具调用顺序和每一步的结构化输出。

## 1:55—2:30：扣子入口

展示扣子 Bot 的输入框和同一份返回结果，说明用户不需要记住工具名称，工作流会按实际提供的材料自动选择整理步骤。

## 2:30—3:00：边界

强调负责人、日期、完成状态和候选异常都需要人工确认；系统不会自动对外发送，也不接收不必要的个人敏感信息。正式参赛材料只使用已保存的测试记录和真实测得的指标。
