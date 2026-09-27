from pathlib import Path
import math
import os
import shutil
import subprocess
import zipfile

from pypdf import PdfReader
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "output" / "pdf"
FIGURE_DIR = ROOT / "output" / "diagrams" / "session-architecture"
SCRATCH = ROOT / "tmp" / "pdfs" / "session-report"
for directory in (PDF_DIR, FIGURE_DIR, SCRATCH):
    directory.mkdir(parents=True, exist_ok=True)

POPPLER = Path(os.environ.get("PDFTOPPM", shutil.which("pdftoppm") or "pdftoppm"))
pdfmetrics.registerFont(TTFont("ReportCJK", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"))
pdfmetrics.registerFont(TTFont("ReportMono", "/System/Library/Fonts/Menlo.ttc", subfontIndex=0))

WIDTH, HEIGHT = 1168, 540
PAGE_W, PAGE_H = 1280, 900
PALETTE = {
    "ink": "#193348", "muted": "#536A7B", "line": "#AEBFCD",
    "blue": "#286B98", "blue_fill": "#EDF5FB", "green": "#317565",
    "green_fill": "#EDF7F2", "amber": "#986622", "amber_fill": "#FBF4E7",
    "paper": "#FFFFFF", "gray_fill": "#F5F7FA", "red": "#9B4945",
}


def color(name):
    return HexColor(PALETTE.get(name, name))


def wrap(text, width, size=14, font="ReportCJK"):
    result = []
    for paragraph in text.split("\n"):
        current = ""
        for character in paragraph:
            if current and pdfmetrics.stringWidth(current + character, font, size) > width:
                result.append(current)
                current = character
            else:
                current += character
        result.append(current)
    return result


def add_text(drawing, left, top, text, size=14, tone="ink", width=None, leading=None, anchor="start"):
    lines = wrap(text, width, size) if width else text.split("\n")
    step = leading or size * 1.5
    for index, line in enumerate(lines):
        drawing.add(String(left, HEIGHT - top - size - index * step, line, fontName="ReportCJK", fontSize=size, fillColor=color(tone), textAnchor=anchor))
    return len(lines) * step


def frame(drawing, left, top, width, height, title, fill="gray_fill", stroke="line", dashed=False, size=15):
    assert left >= 0 and top >= 0 and left + width <= WIDTH and top + height <= HEIGHT
    drawing.add(Rect(left, HEIGHT - top - height, width, height, rx=5, ry=5, fillColor=color(fill), strokeColor=color(stroke), strokeWidth=1, strokeDashArray=[5, 4] if dashed else None))
    add_text(drawing, left + 14, top + 10, title, size=size, tone=stroke if stroke != "line" else "ink", width=width - 28)


def box(drawing, left, top, width, height, title, body="", fill="paper", stroke="line", size=15, body_size=12):
    frame(drawing, left, top, width, height, title, fill, stroke, size=size)
    if body:
        used = add_text(drawing, left + 14, top + 35, body, size=body_size, tone="muted", width=width - 28, leading=body_size * 1.55)
        assert 35 + used <= height + 2, (title, height, used)


def arrow(drawing, points, tone="blue", dashed=False, label=None, label_at=None):
    for start, end in zip(points, points[1:]):
        drawing.add(Line(start[0], HEIGHT - start[1], end[0], HEIGHT - end[1], strokeColor=color(tone), strokeWidth=1.5, strokeDashArray=[5, 4] if dashed else None))
    start, end = points[-2:]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    vertices = [(end[0], HEIGHT - end[1])]
    for offset in (-0.48, 0.48):
        vertices.append((end[0] - 8 * math.cos(angle + offset), HEIGHT - (end[1] - 8 * math.sin(angle + offset))))
    drawing.add(Polygon([coordinate for vertex in vertices for coordinate in vertex], fillColor=color(tone), strokeColor=color(tone)))
    if label and label_at:
        add_text(drawing, *label_at, label, size=11, tone=tone)


def new_figure(number, title, subtitle):
    drawing = Drawing(WIDTH, HEIGHT)
    drawing.add(Rect(0, 0, WIDTH, HEIGHT, fillColor=color("paper"), strokeColor=None))
    add_text(drawing, 20, 9, f"图 {number}  {title}", size=21)
    add_text(drawing, 20, 42, subtitle, size=12, tone="muted", width=1128)
    return drawing


def session_block(drawing, left, top, width, height, name):
    frame(drawing, left, top, width, height, name, "blue_fill", "blue")
    add_text(drawing, left + 14, top + 38, "私有上下文 / 协议端点", size=11, tone="muted")
    frame(drawing, left + 14, top + 64, width - 28, height - 78, "Scheduler", "paper", "blue", size=13)
    add_text(drawing, left + 28, top + 97, "本会话排队、取消与校验", size=11, tone="muted", width=width - 56)
    box(drawing, left + 28, top + height - 65, width - 56, 39, "ModelService", fill="green_fill", stroke="green", size=13)


def logical_figure():
    drawing = new_figure("01", "逻辑归属：模型服务在 AISession 内部", "嵌套框表示归属，箭头表示消息或调用；不表示一个框就对应一个进程或线程。")
    frame(drawing, 20, 92, 300, 365, "ShellSession", "gray_fill", "line")
    box(drawing, 40, 146, 260, 82, "Shell 状态与协议端点", "命令 / 输出 / 目录 / 输入版本")
    box(drawing, 40, 264, 260, 76, "普通命令输入行", "仅回显文本，不附带回车")
    box(drawing, 40, 375, 260, 62, "用户 Enter 后执行", "原始程序输出留在主 Shell", fill="green_fill", stroke="green")
    arrow(drawing, [(170, 340), (170, 375)], "green")
    frame(drawing, 400, 82, 748, 375, "AISession：唯一上下文、权限与生命周期所有者", "blue_fill", "blue")
    box(drawing, 420, 137, 220, 90, "ContextStore", "本页历史、事实、知识引用")
    box(drawing, 420, 280, 220, 80, "ProtocolEndpoint", "接收上下文 / 返回候选命令")
    frame(drawing, 672, 137, 456, 300, "Scheduler：本会话任务编排", "paper", "blue")
    box(drawing, 692, 183, 195, 77, "上下文 / 检索", "构建 Prompt 与配方候选", fill="gray_fill", size=13, body_size=11)
    box(drawing, 904, 183, 204, 77, "结果校验", "配方、参数、计划与证据", fill="gray_fill", size=13, body_size=11)
    box(drawing, 692, 307, 416, 102, "ModelService：只接受本会话调用", "模型配置、流式返回、超时与取消\n内部适配：本地后端 / 授权云端", fill="green_fill", stroke="green", size=14)
    arrow(drawing, [(790, 260), (790, 307)])
    arrow(drawing, [(1006, 307), (1006, 260)], "green")
    arrow(drawing, [(300, 183), (420, 183)], label="上下文", label_at=(340, 159))
    arrow(drawing, [(640, 319), (672, 319)])
    arrow(drawing, [(420, 320), (360, 320), (360, 301), (300, 301)], "green", label="候选命令", label_at=(326, 340))
    add_text(drawing, 20, 481, "关键边界：ModelService 不直接访问 PTY；Scheduler 不跨会话编排；命令回显仍由 Shell 侧校验。", size=13, width=1128)
    return drawing


def local_process_figure():
    drawing = new_figure("02", "进程模式 A：每页承载自己的 AI 执行单元", "虚线外框表示 OS 进程边界；真实 Shell 是子进程，AISession 是宿主中的逻辑对象。")
    box(drawing, 20, 77, 1128, 58, "UI / Supervisor 进程", "管理页面、创建绑定与路由；不合并 AI 历史", fill="gray_fill", body_size=11)
    for left, name in [(20, "A"), (613, "B")]:
        frame(drawing, left, 174, 535, 262, f"PageHost {name} 进程", "gray_fill", "line", True)
        box(drawing, left + 20, 221, 190, 68, f"ShellAdapter {name}", "PTY / 状态 / 回显校验", size=13, body_size=11)
        frame(drawing, left + 20, 335, 190, 76, f"真实 Shell {name}", "paper", "line", True, size=13)
        add_text(drawing, left + 34, 371, "用户命令子进程", size=11, tone="muted")
        arrow(drawing, [(left + 115, 289), (left + 115, 335)])
        session_block(drawing, left + 245, 218, 270, 199, f"AISession {name}")
        arrow(drawing, [(left + 210, 253), (left + 245, 253)])
        arrow(drawing, [(left + 245, 280), (left + 210, 280)], "green")
        arrow(drawing, [(left + 268, 135), (left + 268, 174)])
    frame(drawing, 340, 476, 488, 49, "可选底层算力后端：只处理推理请求", "green_fill", "green", True, size=14)
    arrow(drawing, [(400, 391), (400, 476)], "green", True)
    arrow(drawing, [(996, 391), (996, 458), (790, 458), (790, 476)], "green", True)
    add_text(drawing, 20, 480, "业务 ModelService 在会话内\n虚线调用仅指可选算力复用", size=11, tone="muted", width=300)
    return drawing


def shared_process_figure():
    drawing = new_figure("03", "进程模式 B：多个页面共享 AIWorker", "共享的是进程，不默认共享对话；每个 AISession 内仍有自己的 Scheduler 与 ModelService。")
    box(drawing, 20, 78, 1128, 56, "UI / Supervisor", "维护 page → shell_session → ai_session → worker 的可信绑定", fill="gray_fill", body_size=11)
    for top, name in [(180, "A"), (333, "B")]:
        frame(drawing, 20, top, 285, 108, f"PageHost {name} 进程", "gray_fill", "line", True)
        add_text(drawing, 34, top + 40, f"ShellAdapter {name} / 专属 IPC", size=12)
        add_text(drawing, 34, top + 66, f"真实 Shell {name} 子进程", size=12, tone="muted")
    frame(drawing, 370, 166, 778, 298, "共享 AIWorker 进程：只承载、注册与路由", "gray_fill", "line", True)
    session_block(drawing, 392, 231, 355, 215, "AISession A")
    session_block(drawing, 771, 231, 355, 215, "AISession B")
    arrow(drawing, [(305, 231), (340, 231), (340, 269), (392, 269)], label="A 通道", label_at=(312, 205))
    arrow(drawing, [(305, 390), (345, 390), (345, 456), (947, 456), (947, 446)], "green", label="B 通道：只路由至 B", label_at=(404, 478))
    arrow(drawing, [(161, 134), (161, 180)])
    arrow(drawing, [(820, 134), (820, 166)])
    add_text(drawing, 20, 499, "ModelService 各自选择本地或云端后端；共享 AIWorker 内不设置与 AISession 平级的业务调度器。", size=12, width=1128)
    return drawing


def thread_figure():
    drawing = new_figure("04", "线程与异步任务：状态由单一执行单元拥有", "这是推荐的执行模型，不是固定线程数量；同一线程可承载多个独立 Session actor。")
    frame(drawing, 20, 92, 300, 355, "Shell I/O 执行单元", "gray_fill", "line")
    box(drawing, 40, 146, 260, 85, "唯一状态所有者", "PTY / 前台进程 / cwd\n提示符代次 / 输入缓冲区")
    box(drawing, 40, 277, 260, 110, "串行检查与回显", "核对版本后原子填入\n只改文本，不调用提交\n不等待模型推理", fill="green_fill", stroke="green")
    frame(drawing, 372, 92, 450, 355, "AI 执行环境：事件循环 / actor", "gray_fill", "line")
    frame(drawing, 392, 139, 410, 288, "AISession A", "blue_fill", "blue")
    frame(drawing, 411, 190, 372, 216, "Scheduler A", "paper", "blue")
    box(drawing, 430, 236, 334, 70, "私有有界队列", "串行状态变更 / 预算 / 取消", size=14)
    box(drawing, 430, 334, 334, 54, "ModelService A", "异步请求 / 结果回调", fill="green_fill", stroke="green", size=13, body_size=10)
    frame(drawing, 872, 92, 276, 355, "可选算力 / 网络后端", "green_fill", "green", True)
    box(drawing, 892, 166, 236, 93, "推理执行", "本地模型进程\n或经授权云端请求", fill="paper", stroke="green")
    add_text(drawing, 892, 300, "每个请求独立身份与缓存。\n超时只取消相关请求，\n不阻塞普通 Shell。", size=13, width=230)
    arrow(drawing, [(320, 230), (372, 230)], label="消息", label_at=(330, 208))
    arrow(drawing, [(372, 321), (320, 321)], "green")
    arrow(drawing, [(783, 351), (872, 351)], label="异步调用", label_at=(810, 324))
    arrow(drawing, [(872, 390), (783, 390)], "green")
    add_text(drawing, 20, 474, "线程不是安全边界：同进程对象靠逻辑隔离；进程级故障按部署模式影响本页或多个 AI 会话。", size=13, width=1128)
    add_text(drawing, 20, 505, "不允许 AI 持有终端写入句柄；会话调度器不与其他会话共享任务队列或取消状态。", size=12, tone="muted", width=1128)
    return drawing


def sequence_figure():
    drawing = new_figure("05", "完整时序：回显不等于执行", "AI 相关三个参与者均在同一 AISession 的逻辑范围内；只有用户 Enter 能提交 Shell 命令。")
    frame(drawing, 468, 82, 680, 446, "AISession 内部", "blue_fill", "blue", size=12)
    participants = [(100, "用户"), (330, "ShellSession"), (575, "协议端点"), (805, "Scheduler"), (1060, "ModelService")]
    for center, label in participants:
        box(drawing, center - 77, 113, 154, 42, label, size=13)
        drawing.add(Line(center, HEIGHT - 155, center, HEIGHT - 517, strokeColor=color("line"), strokeDashArray=[3, 4]))
    steps = [
        (100, 330, "输入命令 + Enter", "blue"),
        (330, 575, "context / finished", "blue"),
        (575, 805, "构建本页分析任务", "blue"),
        (805, 1060, "上下文 + 模型请求", "blue"),
        (1060, 805, "完整候选方案", "green"),
        (805, 575, "校验后的命令建议", "green"),
        (575, 330, "command.propose", "green"),
        (330, 575, "stage_result：未执行", "blue"),
        (100, 330, "用户再次 Enter 才执行", "amber"),
        (330, 575, "started / finished", "blue"),
    ]
    for index, (start, end, label, tone) in enumerate(steps):
        top = 181 + index * 35
        arrow(drawing, [(start, top), (end, top)], tone)
        add_text(drawing, (start + end) / 2, top - 21, label, size=11, tone=tone, anchor="middle")
    return drawing


def isolation_figure():
    drawing = new_figure("06", "隔离边界：私有会话不共享，公共只读能力可复用", "默认按页面分区；共享 AIWorker 或模型权重，不代表共享聊天历史、授权与执行目标。")
    for left, name in [(20, "A"), (790, "B")]:
        frame(drawing, left, 99, 358, 337, f"页面 {name} 的私有命名空间", "blue_fill", "blue")
        content = ["Shell 历史 / 输出 / 输入草稿", "AI 对话 / 摘要 / 私有证据", "上下文快照 / 候选计划", "权限 / 取消令牌 / 请求版本", "模型上下文 / KV cache 槽位", "session 对 + binding_epoch"]
        for index, text in enumerate(content):
            add_text(drawing, left + 22, 159 + index * 37, text, size=13, width=315)
    box(drawing, 434, 181, 300, 216, "公共只读能力", "审核后的配方与文档索引\n模型权重 / 推理后端资源\n\n不包含其他页面的私有数据", fill="green_fill", stroke="green", size=16, body_size=13)
    add_text(drawing, 584, 114, "A 与 B 不交换私有上下文", size=13, tone="red", anchor="middle")
    arrow(drawing, [(434, 278), (378, 278)], "green")
    arrow(drawing, [(734, 278), (790, 278)], "green")
    add_text(drawing, 20, 466, "隔离承诺：应用层不串页、不串历史、不串授权。共享服务仍属于可信基础设施。", size=13, width=1128)
    add_text(drawing, 20, 500, "不是完整 OS 沙箱：两个 Shell 若能访问同一目录，仍可通过真实文件变化互相影响。", size=12, tone="muted", width=1128)
    return drawing


def lifecycle_figure():
    drawing = new_figure("07", "建议生命周期：取消、过期与恢复都不隐含执行", "状态归属本会话；重建后换 binding_epoch，旧结果和旧批准不得自动重放。")
    positions = [(20, "created", "收到上下文"), (250, "queued", "本会话排队"), (480, "analyzing", "模型与检索"), (710, "validated", "方案通过校验"), (940, "staged", "已回显 / 未执行")]
    for left, name, body in positions:
        box(drawing, left, 123, 208, 80, name, body, fill="blue_fill", stroke="blue", size=15)
    for left in (228, 458, 688, 918):
        arrow(drawing, [(left, 163), (left + 22, 163)])
    box(drawing, 250, 298, 208, 86, "cancelled", "取消本会话任务\n不撤销其他页请求", fill="gray_fill", size=15)
    box(drawing, 570, 298, 270, 86, "stale / rejected", "环境、草稿或绑定已变化\n不填入、不自动重试", fill="amber_fill", stroke="amber", size=15)
    box(drawing, 940, 298, 208, 80, "running", "用户已提交命令", fill="green_fill", stroke="green", size=15)
    box(drawing, 940, 434, 208, 80, "finished", "记录结果与验证\n不自动追加执行", fill="green_fill", stroke="green", size=15)
    arrow(drawing, [(354, 203), (354, 298)], "muted", label="取消请求", label_at=(365, 242))
    arrow(drawing, [(814, 203), (814, 253), (705, 253), (705, 298)], "amber", label="校验失败 / 变化", label_at=(573, 261))
    arrow(drawing, [(1044, 203), (1044, 298)], "amber", label="用户 Enter", label_at=(952, 241))
    arrow(drawing, [(1044, 378), (1044, 434)], "green")
    box(drawing, 20, 434, 820, 80, "关闭 / 清空 / 重建", "取消在途请求，清理本会话私有状态；重建时更新绑定代次。\n任何未执行建议都不能因恢复历史而被自动提交。", fill="gray_fill", body_size=12)
    add_text(drawing, 20, 84, "已回显的建议也可由用户清除；取消、过期不是执行成功或事务回滚。", size=12, tone="muted", width=1128)
    return drawing


FIGURES = [
    ("01-logical-ownership", "逻辑归属", logical_figure),
    ("02-page-local-processes", "按页部署的进程关系", local_process_figure),
    ("03-shared-ai-process", "共享 AIWorker 的进程关系", shared_process_figure),
    ("04-thread-and-task-model", "线程与异步任务关系", thread_figure),
    ("05-protocol-sequence", "协议调用与回显时序", sequence_figure),
    ("06-data-isolation", "数据隔离与共享边界", isolation_figure),
    ("07-proposal-lifecycle", "建议生命周期与故障恢复", lifecycle_figure),
]


def page_text(pdf, left, top, text, size=14, width=1168, tone="ink", leading=None):
    lines = wrap(text, width, size)
    step = leading or size * 1.65
    pdf.setFont("ReportCJK", size)
    pdf.setFillColor(color(tone))
    for index, line in enumerate(lines):
        pdf.drawString(left, PAGE_H - top - size - index * step, line)
    return top + len(lines) * step


def start_page(pdf, number, title, subtitle):
    pdf.setFillColor(color("paper"))
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    pdf.setFont("ReportMono", 11)
    pdf.setFillColor(color("blue"))
    pdf.drawString(56, PAGE_H - 40, f"HARMONY SHELL / SESSION ARCHITECTURE / {number:02d}")
    page_text(pdf, 56, 61, title, size=27)
    page_text(pdf, 56, 106, subtitle, size=13, tone="muted")
    pdf.setStrokeColor(color("line"))
    pdf.line(56, 62, 1224, 62)
    page_text(pdf, 56, 850, "2026-09-27  |  设计总结 v1.0  |  D-012 至 D-014  |  尚未进行目标 Harmony 设备验证", size=10, tone="muted")
    pdf.setFont("ReportMono", 10)
    pdf.drawRightString(1224, 35, f"{number:02d} / 10")


def table(pdf, left, top, widths, headers, rows, row_height=48, size=12):
    total = sum(widths)
    pdf.setFillColor(color("ink"))
    pdf.rect(left, PAGE_H - top - 37, total, 37, fill=1, stroke=0)
    current = left
    for width, label in zip(widths, headers):
        page_text(pdf, current + 12, top + 9, label, size=12, tone="paper", width=width - 24)
        current += width
    for index, row in enumerate(rows):
        row_top = top + 37 + index * row_height
        pdf.setFillColor(color("gray_fill" if index % 2 == 0 else "paper"))
        pdf.rect(left, PAGE_H - row_top - row_height, total, row_height, fill=1, stroke=0)
        current = left
        for width, value in zip(widths, row):
            used = len(wrap(value, width - 24, size)) * size * 1.55
            assert used <= row_height - 12, (value, used, row_height)
            page_text(pdf, current + 12, row_top + 8, value, size=size, width=width - 24, leading=size * 1.55)
            current += width
    return top + 37 + len(rows) * row_height


def summary_page(pdf):
    start_page(pdf, 1, "Shell Session、AI Session 与模型服务：设计总览", "把逻辑归属、物理进程和线程调度分开描述；共享进程不等于共享会话，回显不等于执行。")
    page_text(pdf, 56, 157, "已确认的五条约束", size=19)
    principles = [
        "01  主窗口保持普通 Shell；所有 AI 解释、建议说明和验证状态只在侧栏。",
        "02  每页默认绑定独立 Shell / AI Session，页面之间不交换私有上下文。",
        "03  支持多个页面共享 AI 宿主进程，但不默认合并逻辑对话。",
        "04  Scheduler 与 ModelService 从属于 AISession，不能与 Session 平级。",
        "05  纯命令文本可回显到空闲提示符；只有用户 Enter 才真正提交执行。",
    ]
    for index, line in enumerate(principles):
        page_text(pdf, 56, 199 + index * 37, line, size=15)
    page_text(pdf, 56, 407, "五个名称，五种职责", size=19)
    table(pdf, 56, 446, [230, 560, 378], ["对象", "负责什么", "不是什么"], [
        ("ShellSession", "终端状态、命令运行、输入缓冲区与最终回显校验", "不是模型，也不是 AI 对话历史"),
        ("AISession", "本页上下文、权限、协议端点与内部能力生命周期", "不等于一个 OS 进程"),
        ("Scheduler", "只编排所属会话的检索、模型调用、校验与取消", "不是跨 Session 的全局业务调度器"),
        ("ModelService", "所属会话的模型配置、请求、流式响应与超时", "不等于独占一份模型权重"),
        ("AIWorker", "承载、注册和路由一个或多个 AISession", "不是共享聊天历史或授权容器"),
    ], row_height=48)
    page_text(pdf, 56, 760, "阅读顺序：图 01 看归属；图 02-03 看进程；图 04 看线程；图 05-07 看协议、隔离与恢复。", size=13, tone="blue")
    page_text(pdf, 56, 789, "状态说明：上述产品边界已确认；具体进程部署、线程数、IPC 实现、模型后端和系统沙箱能力仍待验证。", size=12, tone="muted")
    pdf.showPage()


FIGURE_PAGES = [
    ("01 / 逻辑归属与调用方向", "AISession 是上下文和生命周期边界，内部 Scheduler 组织任务，ModelService 只提供推理能力。", [
        "对外协议只连接 ShellSession 与 AISession；调度器和模型服务不直接写终端。",
        "模型提出候选配方与参数，程序完成校验和命令生成；Shell 侧仍进行最终输入状态检查。",
        "此图描述所有权，不规定进程或线程数量。关闭会话时，其队列、模型请求和私有缓存随之清理。",
    ]),
    ("02 / 进程部署模式 A：按页承载", "保留早期每页 PageHost 的方案：同页 Shell 适配与 AI 编排同属一个宿主进程。", [
        "真实 Shell 是 PageHost 的子进程；AISession 内仍嵌套 Scheduler 与 ModelService。",
        "本页模型请求失败可以局部处理；若 PageHost 整体崩溃，本页终端控制可能一同受影响。",
        "不同页面宿主独立；是否增加更强 AI 故障隔离或系统沙箱，需要目标设备验证。",
    ]),
    ("03 / 进程部署模式 B：共享 AIWorker", "多个 PageHost 通过专属绑定连接共享 AI 进程，各 AISession 内的状态与内部服务保持独立。", [
        "可信路由表绑定 page_id、shell_session_id、ai_session_id、worker_id 与 binding_epoch。",
        "worker_id 只是部署地址；不能作为对话历史、上下文、授权或 KV cache 的唯一索引。",
        "共享 AIWorker 故障会影响多个 AI 会话，但不应连带结束外部 PageHost 或真实 Shell。",
    ]),
    ("04 / 线程关系与非阻塞边界", "Session 是逻辑对象，线程只是执行资源；推荐单一状态所有者加有界消息队列。", [
        "Shell I/O 负责真实输入状态和 PTY；AI 侧通过异步请求处理耗时检索和推理。",
        "每个 AISession 的 Scheduler 只管理自己的任务；宿主仅限制资源占用，不接管会话业务。",
        "检查输入版本与写入必须在同一串行控制点完成；不能先检查、稍后无条件覆盖用户草稿。",
    ]),
    ("05 / 上下文到命令回显的端到端协议", "上下文、模型响应、回显回执和执行事件属于不同阶段；协议中不提供 AI 可调用的 shell.execute。", [
        "AI 解释可流式显示在右侧；完整响应到齐并校验后，才允许生成 command.propose。",
        "stage_result=staged 仅表示文本已进入提示符，不代表命令执行或用户已经批准全部副作用。",
        "用户 Enter 后才产生 command.started；原始输出留在主 Shell，额外验证报告只显示在侧栏。",
    ]),
    ("06 / 数据隔离与共享资源边界", "页面之间不通信是默认会话策略；公共只读知识和底层算力复用需要与私有状态隔离。", [
        "每页隔离历史、上下文、草稿、计划、取消令牌与授权；所有返回结果固定绑定原请求。",
        "共享 AIWorker 中采用逻辑隔离，不等于独立 OS 地址空间；UI、路由和推理后端属于可信边界。",
        "如需要连文件访问都隔离，应另外设计系统沙箱与独立工作区；不能把 Session 隔离当成安全沙箱。",
    ]),
    ("07 / 生命周期、取消与故障恢复", "创建、清空、取消和销毁由 AISession 向下管理；恢复历史不恢复隐含执行权限。", [
        "取消只作用于所属会话的任务、模型请求和未执行建议；不触发其他页的取消或输入变化。",
        "上下文、提示符、输入或绑定变化都可使方案过期；晚到回复最多保留历史，不能强行回显。",
        "重启 PageHost 或 AIWorker 后更新绑定代次；同一 proposal 的重试必须幂等，不重放用户 Enter。",
    ]),
]


def diagram_page(pdf, page_number, drawing, specification):
    title, subtitle, notes = specification
    start_page(pdf, page_number, title, subtitle)
    renderPDF.draw(drawing, pdf, 56, 214)
    for index, note in enumerate(notes):
        page_text(pdf, 56, 707 + index * 37, f"{index + 1:02d}  {note}", size=13, width=1168)
    pdf.showPage()


def protocol_page(pdf):
    start_page(pdf, 9, "08 / 最小通信契约与回显检查", "逻辑协议在两种部署中保持一致；同进程可用类型化队列，跨进程使用受保护 IPC。")
    table(pdf, 56, 159, [345, 200, 623], ["消息", "方向", "语义"], [
        ("shell.context.snapshot", "Shell → AI", "本页最小事实快照；带上下文、提示符及输入版本"),
        ("shell.context.changed", "Shell → AI", "目录、环境或目标发生变化，使相关旧建议失效"),
        ("shell.command.finished", "Shell → AI", "关联命令、退出状态、限量输出与截断说明"),
        ("ai.context.request", "AI → Shell", "申请额外只读信息；仍需本页授权与范围检查"),
        ("ai.command.propose", "AI → Shell", "完整候选命令、配方版本、计划摘要与预期状态"),
        ("shell.command.stage_result", "Shell → AI", "已填入或拒绝原因；不表示已经执行"),
        ("shell.command.started", "Shell → AI", "用户提交后真实执行开始，不接受模型伪造"),
        ("request.cancel / session.close", "双向 / Supervisor", "撤销本页在途工作或关闭绑定，阻止晚到消息"),
    ], row_height=44, size=12)
    page_text(pdf, 56, 578, "消息必须绑定的身份", size=18)
    page_text(pdf, 56, 613, "page_id · shell_session_id · ai_session_id · binding_epoch · task_id · request_id · message_id", size=13, tone="blue")
    page_text(pdf, 56, 653, "回显检查", size=18)
    page_text(pdf, 56, 690, "绑定与实际通道一致 → 请求未取消 → 计划有效 → 上下文未过期 → 前台是空闲 Shell → 输入版本一致 → 命令完整安全转义。", size=13, width=1168)
    page_text(pdf, 56, 739, "拒绝路径", size=18)
    page_text(pdf, 56, 776, "INPUT_CHANGED / SHELL_BUSY / STALE_CONTEXT / BINDING_MISMATCH / INVALID_PROPOSAL；只在侧栏解释，不覆盖当前草稿。", size=12, width=1168)
    pdf.showPage()


def decision_page(pdf):
    start_page(pdf, 10, "09 / 验收清单、待决策事项与演进记录", "报告是已确认约束与候选实现的总结，不是 Harmony 平台兼容性认证，也不新增跨页授权。")
    page_text(pdf, 56, 158, "第一版必须验证", size=19)
    checks = [
        "A/B 请求并发和乱序响应，不串页、不改绑。",
        "用户编辑或开始下一条命令后，旧建议不可覆盖。",
        "编辑器、REPL、续行或输入法提交时不注入。",
        "回显不执行；AI 区的 Enter 只提交问题。",
        "重复 proposal、回执丢失不产生重复回显。",
        "取消或关闭 A，不影响 B 的历史、队列与输入。",
        "共享 AI 进程故障不结束外部普通 Shell。",
        "重建绑定后拒绝旧消息，不重放批准或 Enter。",
        "模型缓存与云端对话不泄漏另一页上下文。",
        "AI / verify 消息不污染主窗口原始输出。",
    ]
    for index, item in enumerate(checks):
        page_text(pdf, 56, 201 + index * 41, f"{index + 1:02d}  {item}", size=13, width=580)
    page_text(pdf, 710, 158, "尚待确定，不在本报告中定案", size=19, width=510)
    pending = [
        ("部署默认值", "模式 A 或共享 AIWorker；是否需要独立 AI 安全域。"),
        ("线程与 IPC", "具体运行时、线程数、队列预算、背压和连接实现。"),
        ("模型服务后端", "本地或云端、权重复用、私有缓存策略与上传授权。"),
        ("平台适配", "设备 / 系统 / Shell、PTY 与行编辑集成、系统权限。"),
        ("工作组模式", "多个 Shell 共用一个逻辑对话仍属备选，默认不开启。"),
    ]
    for index, (label, detail) in enumerate(pending):
        top = 205 + index * 76
        page_text(pdf, 710, top, label, size=14, tone="blue")
        page_text(pdf, 710, top + 25, detail, size=12, width=505, tone="muted")
    pdf.setStrokeColor(color("line"))
    pdf.line(56, PAGE_H - 640, 1224, PAGE_H - 640)
    page_text(pdf, 56, 663, "关键演进", size=18)
    page_text(pdf, 56, 700, "D-012：一页一对 Session 与统一协议；D-013：补充共享 AI 进程；D-014：调度器和模型服务下沉至 AISession 内部。", size=13, width=1168)
    page_text(pdf, 56, 741, "已替代：将全局业务调度器、模型网关与 AISession 平级。历史内容保留在讨论文档，不作为当前架构。", size=12, tone="muted", width=1168)
    page_text(pdf, 56, 779, "依据：SESSION_PROTOCOL.md v0.3、TECHNICAL_ARCHITECTURE.md v0.4、PROJECT_DISCUSSIONS.md（D-012 至 D-014）。", size=11, tone="muted", width=1168)
    pdf.showPage()


def main():
    drawings = []
    for filename, title, factory in FIGURES:
        drawing = factory()
        drawings.append(drawing)
        renderSVG.drawToFile(drawing, str(FIGURE_DIR / f"{filename}.svg"))
        temporary_pdf = SCRATCH / f"{filename}.pdf"
        renderPDF.drawToFile(drawing, str(temporary_pdf))
        subprocess.run([str(POPPLER), "-singlefile", "-scale-to", "2336", "-png", str(temporary_pdf), str(FIGURE_DIR / filename)], check=True, capture_output=True)
    destination = PDF_DIR / "harmony-shell-session-architecture.pdf"
    pdf = canvas.Canvas(str(destination), pagesize=(PAGE_W, PAGE_H))
    pdf.setTitle("Harmony Shell - Session、进程与模型服务架构总结")
    pdf.setAuthor("Harmony Shell 产品设计")
    pdf.setSubject("逻辑归属、两种进程部署、线程模型、通信协议、隔离与恢复")
    summary_page(pdf)
    for page_number, (drawing, specification) in enumerate(zip(drawings, FIGURE_PAGES), start=2):
        diagram_page(pdf, page_number, drawing, specification)
    protocol_page(pdf)
    decision_page(pdf)
    pdf.save()
    reader = PdfReader(destination)
    assert len(reader.pages) == 10
    for page_number, page in enumerate(reader.pages, start=1):
        assert len(page.extract_text()) > 200, page_number
    manifest = ["# Session 架构独立图解", "", "日期：2026-09-27。每张图分别保存为 PNG 和 SVG。PNG 可直接预览；SVG 为可编辑矢量版本，中文显示依赖查看器字体回退。", "", "所有图均已嵌入 harmony-shell-session-architecture.pdf。逻辑包含关系不等于进程或线程数量。", ""]
    for filename, title, factory in FIGURES:
        manifest.append(f"- `{filename}.png` / `{filename}.svg`：{title}。")
    manifest.extend(["", "已确认：Scheduler 与 ModelService 从属 AISession；主 Shell 只运行命令；默认按页隔离；用户 Enter 才执行。", "待定：进程部署默认值、线程数、IPC 库、本地/云端选择与系统沙箱。", "", "来源：SESSION_PROTOCOL.md v0.3、TECHNICAL_ARCHITECTURE.md v0.4，以及 D-012 至 D-014 的讨论记录。", ""])
    (FIGURE_DIR / "README.md").write_text("\n".join(manifest))
    archive = ROOT / "output" / "session-architecture-diagrams.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(FIGURE_DIR.iterdir()):
            if path.suffix in (".png", ".svg", ".md"):
                bundle.write(path, arcname=path.name)
    print(destination)
    print(archive)
    print("Validated 10 report pages, 7 standalone PNGs, and 7 standalone SVGs.")


if __name__ == "__main__":
    main()
