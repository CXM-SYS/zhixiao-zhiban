# 本地材料生成工具

`build_plan_pdf.py` 用于重新生成参赛计划书 PDF。若需要重新生成，先安装：

    python -m pip install reportlab pillow

再执行：

    python tools/build_plan_pdf.py

生成文件位于 `output/pdf/职效智办参赛计划书.pdf`。当前提交包已经包含生成后的 PDF，因此不需要为了运行智能体额外安装 reportlab。
