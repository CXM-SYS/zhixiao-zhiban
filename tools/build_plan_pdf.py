from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / ".deps"))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).parents[1]
OUT = ROOT / "output" / "pdf" / "职效智办参赛计划书.pdf"
FONT = Path("C:/Windows/Fonts/simhei.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/msyh.ttc")


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline(text: str) -> str:
    value = esc(text)
    value = re.sub(r"`([^`]+)`", r"<font name='ZH'>\1</font>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    return value


def on_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(colors.HexColor("#20354A"))
    canvas.setFont("ZH", 8.5)
    canvas.drawString(18 * mm, height - 12 * mm, "职效智办 | 职场通用效能智能体")
    canvas.setFillColor(colors.HexColor("#748399"))
    canvas.drawRightString(width - 18 * mm, 12 * mm, f"{doc.page}")
    canvas.restoreState()


def build() -> None:
    if not FONT.exists():
        raise FileNotFoundError(f"中文字体不存在：{FONT}")
    pdfmetrics.registerFont(TTFont("ZH", str(FONT)))
    # SimHei is used for all text so Chinese glyphs remain stable across viewers.
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", fontName="ZH", fontSize=25, leading=34,
        textColor=colors.HexColor("#17324D"), alignment=TA_CENTER,
        spaceAfter=10 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CoverSub", fontName="ZH", fontSize=13, leading=22,
        textColor=colors.HexColor("#4C637A"), alignment=TA_CENTER,
        spaceAfter=26 * mm,
    ))
    styles.add(ParagraphStyle(
        name="H1ZH", fontName="ZH", fontSize=15, leading=22,
        textColor=colors.HexColor("#17324D"), spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="H2ZH", fontName="ZH", fontSize=11.5, leading=17,
        textColor=colors.HexColor("#2C6285"), spaceBefore=3 * mm,
        spaceAfter=1.5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="BodyZH", fontName="ZH", fontSize=9.5, leading=16,
        textColor=colors.HexColor("#273746"), spaceAfter=2.2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="BulletZH", parent=styles["BodyZH"], leftIndent=5 * mm,
        firstLineIndent=-3 * mm, bulletIndent=1 * mm, spaceAfter=1.2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SmallZH", fontName="ZH", fontSize=8, leading=12,
        textColor=colors.HexColor("#58697A"), spaceAfter=1.5 * mm,
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame = Frame(18 * mm, 18 * mm, A4[0] - 36 * mm, A4[1] - 36 * mm, id="normal")
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=19 * mm, bottomMargin=18 * mm, title="职效智办参赛计划书",
        author="职效智办项目",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])

    story = []
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("职效智办", styles["CoverTitle"]))
    story.append(Paragraph("职场通用效能智能体参赛计划书", styles["CoverSub"]))
    cover_box = Table([
        [Paragraph("申报赛事", styles["SmallZH"]), Paragraph("第三届北京市 AI 创新大赛", styles["BodyZH"])],
        [Paragraph("申报赛道", styles["SmallZH"]), Paragraph("职业发展赛 · 智能体创新 · 赛题 1", styles["BodyZH"])],
        [Paragraph("演示场景", styles["SmallZH"]), Paragraph("周会材料整理与项目进度汇总", styles["BodyZH"])],
        [Paragraph("版本", styles["SmallZH"]), Paragraph("本地 MVP 参赛材料初稿", styles["BodyZH"])],
    ], colWidths=[32 * mm, 112 * mm])
    cover_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2F6")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B7CBD8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6E1E8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(cover_box)
    story.append(Spacer(1, 18 * mm))
    story.append(Paragraph("说明：本文件只把已经完成或已经有运行记录的内容写成现状，其余内容保留为后续工作。", styles["SmallZH"]))
    story.append(PageBreak())

    sections = [
        ("1. 项目摘要", [
            (None, "“职效智办”面向日常办公中的会议、文档、表格和汇报材料，帮助用户把自然语言需求转成可执行的工作清单。它可以提取任务目标，概括办公材料，识别待办、负责人和日期线索，检查 CSV 或 Excel 表格中的缺失、重复和异常，并把汇报材料中的结论与表格数值做初步关联。"),
            (None, "项目申报第三届北京市 AI 创新大赛职业发展赛的“职场通用效能智能体”赛题。核心定位是减少材料整理和交付前检查的时间，同时保留人工确认权，不自动替用户承诺完成状态或对外发送内容。"),
        ]),
        ("2. 用户痛点与应用场景", [
            (None, "办公任务通常分散在聊天记录、会议纪要、通知、任务表和周报中。人工整理容易漏掉负责人和截止时间，表格中的空值、重复记录和极端数值也常常在汇报后才被发现；当文字结论和数据表格分离时，复核者很难快速找到依据。"),
            (None, "首个演示场景是“周会材料整理与项目进度汇总”：用户输入一段需求，附上会议或任务材料、CSV 任务表和周报草稿，系统输出摘要、待办清单、数据风险、结论依据提示和下一步建议。"),
        ]),
        ("3. 产品功能与工作流程", [
            ("需求理解", "提取交付目标、限制条件和需要人工确认的内容。"),
            ("文档处理", "对会议纪要、通知和汇报材料提取标题、关键段落和摘要。"),
            ("待办提取", "识别“负责、完成、跟进、确认”等行动线索，输出负责人和日期候选，并保留来源行。"),
            ("表格检查", "检查字段类型、缺失值、完全重复行、数值摘要、候选异常值和单位标记。"),
            ("汇报核验", "把报告中的数值与表格进行初步匹配，提示没有数字或材料依据的结论。"),
            ("行动输出", "按“已识别线索、风险提示、建议动作、人工确认事项”组织一份可复核报告。"),
        ]),
        ("4. 技术实现方案", [
            (None, "系统采用扣子 Bot 作为交互入口，扣子工作流负责判断输入类型和编排工具，OpenAPI 插件连接本地 Python 服务。Python 服务使用只读规则工具完成文档摘要、待办提取、表格审查和依据提示；离线回放模式不依赖外部模型 API，便于先验证流程和保留运行记录。"),
            (None, "输入接口使用 request_text，并支持可选的 document_text、data_csv 和 report_text。请求大小限制为 8 MB，服务不把原文写入访问日志。当前版本只处理用户主动提供的内容，不执行用户上传的代码。"),
        ]),
        ("5. 创新点", [
            (None, "把通用办公智能体拆成可观察的需求、文档、待办、数据和依据工具，用户能看到结果来自哪一步。"),
            (None, "自动提取结果保留来源行和待确认状态，降低把推测当成事实的风险。"),
            (None, "文档整理和表格检查放在同一条交付流程中，减少在多个工具之间复制粘贴。"),
            (None, "扣子 Bot 适合自然语言使用，Python 插件适合稳定执行和保存可复核轨迹，方便从个人演示扩展到团队流程。"),
        ]),
        ("6. 测试设计与结果记录", [
            (None, "第一阶段准备三类公开或人工编造的脱敏案例：会议纪要转待办、任务表汇总、周报结论与表格核验。每类案例都保存输入版本、运行时间、工具轨迹和人工问题清单。测试指标包括需求要素提取覆盖率、待办识别准确率、字段问题识别准确率与召回率、结论依据关联率、报告生成时间和人工可读性评分。"),
            (None, "目前已完成三组内部脱敏案例回放：会议纪要转待办、任务表质量检查、任务表与周报结论联合核验。三组案例的预设检查项覆盖记录分别为 3/3、4/4、1/1，均为本地规则回放结果；平均单案例处理时间约为 0.010 秒。这些结果只说明当前固定案例通过，不能替代真实用户测试，也不能直接宣传为产品准确率或用户节省时间。"),
            (None, "申报材料只填写实际运行结果。正式数值必须绑定案例编号、测试次数、人工核验人和运行记录。"),
        ]),
        ("7. 应用价值与推广路径", [
            (None, "短期可服务于部门周报、会议纪要、项目进度和运营数据交付前检查；中期可接入企业知识库、表单系统和日程系统；长期可根据权限接入审批、提醒和版本管理。推广时坚持最小化采集、人工确认和可追溯记录，避免把助手输出直接视为正式业务决定。"),
        ]),
        ("8. 风险、限制与后续计划", [
            ("行动线索", "行动词识别可能把背景描述误判为待办，负责人和日期必须人工确认。"),
            ("数据提示", "IQR 等规则只能提示候选异常，不能直接判定业务错误。"),
            ("依据核验", "数值匹配不能替代原始系统复算，后续增加附件版本、图表位置和审批记录关联。"),
            ("隐私边界", "当前服务不执行上传代码，也不接收身份证号、手机号等不必要的个人信息。"),
            ("后续版本", "接入真实文件上传、Excel 解析、扣子云端部署和授权范围管理。"),
        ]),
        ("9. 参赛材料清单", [
            (None, "根据赛事页面准备：作品说明 PDF，控制在 3—10 页；2—3 分钟 MP4 演示视频；可运行的扣子 Bot 或其他平台智能体链接，并附使用说明；三类脱敏测试案例、指标表和人工核验记录；Bot、工作流、插件和本地服务截图；项目分工、软件工具和 AI 使用说明；数据来源、授权、原创性和隐私合规说明。"),
        ]),
        ("10. 倒计时安排", [
            (None, "赛事页面显示，职业发展赛智能体创新作品申报截止时间为 2026 年 10 月 23 日，线上评审为 10 月 30 日，最终结果在 11 月公布。"),
            ("现在开始", "完成扣子 Bot、工作流和公网 HTTPS 插件，复核三组案例并补充人工记录。"),
            ("提交前", "录制 2—3 分钟演示，完成 PDF、截图、数据授权和 AI 使用说明，核对报名系统字段并保存提交凭证。"),
        ]),
    ]

    for title, items in sections:
        story.append(Paragraph(inline(title), styles["H1ZH"]))
        for label, text in items:
            if label:
                story.append(Paragraph(f"<b>{inline(label)}</b>：{inline(text)}", styles["BulletZH"], bulletText="•"))
            else:
                story.append(Paragraph(inline(text), styles["BodyZH"]))
        if title in {"4. 技术实现方案", "6. 测试设计与结果记录"}:
            story.append(Spacer(1, 1.5 * mm))

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
