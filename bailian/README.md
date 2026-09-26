# 职效智办接入百炼

截至 2026-09-26，华北2（北京）的“职效智办”Agent 2.0 应用已发布，使用 `qwen-plus`，并已挂载“职效智办办公分析”MCP 服务及 `analyze_workplace` 工具。公网演示地址为 https://zhixiao-zhiban.onrender.com/ 。应用 ID 为 `74b86b561a494d53ae34f30db0a931cd`；它不是密钥。

公网 `/capabilities` 已返回 `ai_agent_ready: true`，`POST /agent` 已实测返回百炼智能体结果。会议记录样例正确保留未注明年份和相对日期；CSV 样例正确识别 4 行记录、1 行重复、1 处负责人缺失、1 个工时候选异常值，并指出“全部已完成”与原始状态不符。以上是小样例验证，不代表所有办公文档和数据集的准确率。

下面保留复现与维护步骤：

1. 在百炼华北2（北京）检查所选模型的免费额度和到期日，开启“免费额度用完即停”。
2. 在 Flow Agent“应用管理”创建**新版智能体应用**，名称填“职效智办”，选择确有可用额度的模型。系统提示词参考 `system_prompt.md`。
3. 在“插件”创建自定义插件，名称“职效智办办公分析”，插件 URL 为 `https://zhixiao-zhiban.onrender.com`。新增工具：名称 `analyze_workplace`，路径 `/analyze`，方法 `POST`，提交方式 `application/json`。请求字段：

   | 字段 | 类型 | 必填 | 说明 |
   | --- | --- | --- | --- |
   | `request_text` | String | 是 | 用户希望完成的办公任务 |
   | `document_text` | String | 否 | 会议记录或办公材料原文 |
   | `data_csv` | String | 否 | CSV 文本，保持表头和换行 |
   | `report_text` | String | 否 | 待核验汇报草稿 |

   响应中的 `answer` 是主要分析报告，`status` 为执行状态。先在插件调试页运行测试，再将插件发布为 MCP 服务并挂载到智能体。创建插件前可用 `https://zhixiao-zhiban.onrender.com/health` 验证服务在线。
4. 在百炼应用测试窗输入两类样例，确认运行轨迹中**实际调用了** `analyze_workplace`，再发布应用。只得到模型自由生成的文字不算工具测试通过。
5. 在应用管理复制 APP ID，在百炼密钥管理创建同业务空间的 API Key。到 Render 的服务 `Environment` 添加 `BAILIAN_APP_ID` 和 `DASHSCOPE_API_KEY`；密钥不要放在 GitHub、截图或聊天里。
6. 打开 `https://zhixiao-zhiban.onrender.com/capabilities`，看到 `ai_agent_ready: true` 后，再打开根地址执行一次完整测试。确认网页标注“已连接百炼智能体”，且答案与插件原始数据一致。

百炼智能体 API、模型调用与插件都以控制台的实际可用状态为准。网页上的模型调用会消耗创建者的百炼额度；`qwen-plus` 的“免费额度用完即停”已由账号持有人开启，但仍应定期核对控制台状态。不要将密钥写入源码或截图。

官方参考：

- https://help.aliyun.com/zh/model-studio/new-single-agent-application
- https://help.aliyun.com/zh/model-studio/custom-plug-ins
- https://help.aliyun.com/zh/model-studio/new-agent-application-api-reference
- https://help.aliyun.com/zh/model-studio/new-free-quota
