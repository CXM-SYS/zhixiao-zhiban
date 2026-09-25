# 职效智办部署说明

## 本地验证

在项目根目录执行：

    python -m pip install -e .
    python -m mozhi_yansuan serve --host 127.0.0.1 --port 8787

健康检查：`GET /health`。

交互式演示网页：`GET /`。网页可直接填写任务、粘贴办公材料或上传 CSV，调用本站 `POST /analyze`，无需扣子账号或额度。当前接口使用固定工具流程和规则核验，不调用生成式模型。

办公接口：`POST /analyze`，请求字段为：

- `request_text`：必填；
- `document_text`：可选；
- `data_csv`：可选；
- `report_text`：可选。

## Docker

项目根目录已有 `Dockerfile`。构建和启动：

    docker build -t zhixiao-zhiban .
    docker run --rm -e PORT=8080 -p 8080:8080 zhixiao-zhiban

部署平台需要把容器端口映射为公网 HTTPS 地址，并将 `/analyze` 路径暴露给扣子插件。

## 用 Render 部署

Render 官方支持从 Git 仓库读取 Dockerfile 创建 Web Service，并会通过 `PORT` 环境变量提供监听端口；项目已经提供 `render.yaml`，可以直接使用 Blueprint 创建服务。Web Service 必须监听 `0.0.0.0`，健康检查路径设置为 `/health`。

1. 把项目上传到 GitHub，确保仓库根目录包含 `Dockerfile`、`pyproject.toml` 和 `render.yaml`。
2. 登录 Render，选择 **New → Blueprint**，连接 GitHub 仓库并选择 `render.yaml`。
3. 检查服务名为 `zhixiao-zhiban`，计划可以先选择 Free，点击创建并等待部署完成。
4. 在 Render 的 Settings 中确认 Health Check Path 为 `/health`。
5. 打开 Render 分配的 `https://你的服务名.onrender.com/health`，看到 `status: ok` 后，再打开服务根地址 `/` 检查交互网页。插件地址仍是 `/analyze`。

Free 服务空闲一段时间后会休眠，第一次访问可能需要等待约一分钟；它适合参赛演示和测试，不适合生产服务。Render 的免费服务也使用临时文件系统，因此本项目只在请求期间处理文本，不把材料长期保存。

## 扣子配置

1. 把公网地址填入 `coze/openapi.yaml` 的 `servers.url`。
2. 导入 OpenAPI 插件。
3. 使用 `coze/bot_prompt.md` 创建 Bot 提示词。
4. 按 `coze/workflow_spec.md` 映射四个输入字段。
5. 用 `coze/demo_payload.json` 做一次完整回放。

## 上线前检查

- 使用 HTTPS；
- 配置平台鉴权或来源限制；
- 保留 8 MB 请求大小限制；
- 不把请求原文写入访问日志；
- 不接收不必要的个人敏感信息；
- 用三组 `validation/cases` 材料完成回放并保存结果。
