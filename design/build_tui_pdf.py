from pathlib import Path
import unicodedata

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
SCRATCH = ROOT / "tmp" / "pdfs"
OUTPUT.mkdir(parents=True, exist_ok=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

CJK_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
MONO_PATH = "/System/Library/Fonts/Menlo.ttc"
pdfmetrics.registerFont(TTFont("CJK", CJK_PATH))
pdfmetrics.registerFont(TTFont("Mono", MONO_PATH, subfontIndex=0))

SCALE = 2
WIDTH = 1168
HEIGHT = 548
SPLIT = 700
CELL = 8.4
LINE = 28
COLORS = {
    "background": "#101820",
    "bar": "#1C2935",
    "line": "#3B4D5E",
    "text": "#DBE5EE",
    "dim": "#9AAEBF",
    "green": "#9CD5B6",
    "cyan": "#94D1EF",
    "warn": "#F0BE92",
}
MONO = ImageFont.truetype(MONO_PATH, 16 * SCALE, index=0)
CJK = ImageFont.truetype(CJK_PATH, 16 * SCALE)


SCENES = [
    {
        "number": "01",
        "title": "主动询问：先了解能力，不必先遇到失败",
        "subtitle": "主窗口与普通 Shell 一致；所有能力介绍、询问与回答仅显示在右侧 AI 工作区。",
        "task": "general / 未附加日志",
        "shell": [
            ("developer@harmony:~/workspace$ pwd", "text"),
            ("/home/developer/workspace", "text"),
        ],
        "ai": [
            ("? 你能帮我做什么？", "cyan"),
            ("", "text"),
            ("可以解释命令、准备开发工具，", "text"),
            ("检查运行时、PATH 和依赖环境。", "text"),
            ("", "text"),
            ("具体软件是否可用，需结合设备", "text"),
            ("信息与配方验证，不能直接承诺。", "text"),
            ("", "text"),
            ("不做业务实现或源码 bug 修复。", "dim"),
        ],
        "draft": "",
        "ask": "安装 Python 前要检查什么？",
        "focus": "ai",
        "behavior": "AI 区的 Enter 只发送问题；Shell 区的 Enter 才提交命令。",
        "boundary": "一般询问默认不附加项目文件或命令日志，需要检查时再说明读取范围。",
        "state": "仅询问 / 无环境变更",
    },
    {
        "number": "02",
        "title": "命令失败：右侧解释，左侧只保留命令",
        "subtitle": "分析与建议全部留在 AI 侧栏；主提示符只承接可编辑的命令文本，不显示 AI 提示或标签。",
        "task": "session 01 / task 001",
        "shell": [
            ("developer@harmony:~/workspace$ python -m venv .venv", "text"),
            ("shell: command not found: python", "warn"),
        ],
        "ai": [
            ("观察  python 命令未找到。", "text"),
            ("检查  python3 可用（示例）。", "text"),
            ("", "text"),
            ("意图  创建项目虚拟环境。", "text"),
            ("建议  python3 -m venv .venv", "cyan"),
            ("", "text"),
            ("影响  写入当前目录 .venv。", "text"),
            ("      不更改系统默认 Python。", "text"),
            ("", "text"),
            ("命令已填入；请在左侧按 Enter。", "green"),
        ],
        "draft": "python3 -m venv .venv",
        "ask": "这条命令会改动哪里？",
        "focus": "shell",
        "behavior": "左侧没有 AI 消息、状态条或建议框；提示符内只保留命令，用户按 Enter 才执行。",
        "boundary": "仅向空闲 Shell 的输入缓冲区回显；不能向编辑器、REPL 或运行中的进程注入。",
        "state": "自动回显 / 等待 Enter",
    },
    {
        "number": "03",
        "title": "继续询问：调整条件后，更新待执行命令",
        "subtitle": "条件变更与旧建议撤回只在右侧说明；左侧只更新普通命令输入行，不追加解释日志。",
        "task": "session 01 / task 001",
        "shell": [
            ("developer@harmony:~/workspace$ python -m venv .venv", "text"),
            ("shell: command not found: python", "warn"),
        ],
        "ai": [
            ("? 用 .dev 作为环境目录可以吗？", "cyan"),
            ("", "text"),
            ("可以。目标目录改为 .dev。", "text"),
            ("原 .venv 建议撤回；未执行。", "dim"),
            ("", "text"),
            ("新命令：", "text"),
            ("python3 -m venv .dev", "cyan"),
            ("", "text"),
            ("已更新主提示符；不会自行执行。", "green"),
        ],
        "draft": "python3 -m venv .dev",
        "ask": "",
        "focus": "shell",
        "behavior": "对话可以改变方案；新建议只替换未被用户编辑的旧建议，不自动提交命令。",
        "boundary": "用户已经输入或修改草稿时，保留其文本；新建议另行显示，不强行覆盖。",
        "state": "条件更新 / 旧建议作废",
    },
    {
        "number": "04",
        "title": "按下 Enter：普通 Shell 执行，右侧同步结果",
        "subtitle": "命令成功且没有标准输出时，左侧直接返回提示符；退出状态、验证结果和后续建议仅在右侧。",
        "task": "session 01 / task 002",
        "shell": [
            ("developer@harmony:~/workspace$ python -m venv .venv", "text"),
            ("shell: command not found: python", "warn"),
            ("developer@harmony:~/workspace$ python3 -m venv .dev", "text"),
        ],
        "ai": [
            ("完成  项目虚拟环境 .dev 已创建。", "green"),
            ("退出  0；命令无标准输出。", "dim"),
            ("验证  解释器存在；最小检查通过。", "text"),
            ("影响  仅当前项目目录。", "text"),
            ("保留  系统默认 Python 未改变。", "text"),
            ("", "text"),
            ("没有重跑原来的失败命令，", "dim"),
            ("也没有继续安装其他依赖。", "dim"),
            ("", "text"),
            ("需要时可继续问如何使用环境。", "text"),
        ],
        "draft": "",
        "ask": "如何使用这个虚拟环境？",
        "focus": "shell",
        "behavior": "不在左侧插入“完成”“验证通过”等 AI 文案；原生标准输出为空时，界面也保持安静。",
        "boundary": "检查属于已授权方案的验证范围；不得自动重试部署、发布等有副作用的原命令。",
        "state": "用户已按 Enter / 验证完成",
    },
    {
        "number": "05",
        "title": "不想执行：Esc 清除建议，环境保持不变",
        "subtitle": "用户清除命令后，左侧只恢复普通空提示符；取消说明放在右侧，不往 Shell 输出提示消息。",
        "task": "session 01 / task 001",
        "shell": [
            ("developer@harmony:~/workspace$ python -m venv .venv", "text"),
            ("shell: command not found: python", "warn"),
        ],
        "ai": [
            ("状态  已取消这次建议。", "text"),
            ("", "text"),
            ("不会自动重新填入，也不会", "text"),
            ("因同一错误反复打断你。", "text"),
            ("", "text"),
            ("你可以继续输入自己的命令，", "text"),
            ("或在这里补充目标。", "text"),
            ("", "text"),
            ("取消建议不等于关闭 AI 助手。", "dim"),
        ],
        "draft": "",
        "ask": "",
        "focus": "shell",
        "behavior": "Esc 清除当前建议；直接编辑后，Enter 针对当前文本，而不是最初的 AI 建议。",
        "boundary": "生产实现中，用户修改后的文本仍需重新解析和检查；不能继承旧建议的风险判断。",
        "state": "用户按 Esc / 无变更",
    },
    {
        "number": "06",
        "title": "能力边界：没有依据时，不编造可执行命令",
        "subtitle": "能力说明与拒绝越界仅在右侧呈现；左侧保持原有命令记录和提示符，不打印 AI 状态。",
        "task": "general / 未附加源码",
        "shell": [
            ("developer@harmony:~/workspace$ pwd", "text"),
            ("/home/developer/workspace", "text"),
        ],
        "ai": [
            ("? 所有开发库都能直接安装吗？", "cyan"),
            ("不能这样承诺，需要匹配证据：", "text"),
            ("  已验证 / 待检查 / 暂无方案", "dim"),
            ("请先提供目标软件和版本要求。", "text"),
            ("", "text"),
            ("? 可以顺便修复业务代码 bug 吗？", "cyan"),
            ("这不属于本助手的范围。", "text"),
            ("可以检查运行时和依赖环境，", "text"),
            ("不会直接读取并修改业务源码。", "text"),
            ("", "text"),
            ("未生成命令；没有环境变更。", "green"),
        ],
        "draft": "",
        "ask": "",
        "focus": "ai",
        "behavior": "能力问答与真实支持情况分开；没有可靠路径时保留空提示符，而不是猜一条命令。",
        "boundary": "只处理命令与开发环境，不实现业务功能、不修复源码 bug、不静默转向远程执行。",
        "state": "明确范围 / 不回显虚假方案",
    },
]


def cells(text):
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


def terminal_image(scene):
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), COLORS["background"])
    draw = ImageDraw.Draw(image)

    def rectangle(bounds, color):
        draw.rectangle(tuple(round(value * SCALE) for value in bounds), fill=COLORS[color])

    def text(position, content, tone="text", max_width=None):
        start, top = position
        length = cells(content) * CELL
        if max_width is not None:
            assert length <= max_width, (scene["number"], content, length, max_width)
        for character in content:
            wide = unicodedata.east_asian_width(character) in "WF"
            font = CJK if ord(character) > 127 else MONO
            draw.text((round(start * SCALE), round((top + (1 if font is CJK else 0)) * SCALE)), character, font=font, fill=COLORS[tone])
            start += CELL * (2 if wide else 1)
        return start

    rectangle((0, 0, WIDTH, 38), "bar")
    rectangle((SPLIT, HEIGHT - 32, WIDTH, HEIGHT), "bar")
    rectangle((SPLIT, 38, SPLIT + 1, HEIGHT), "line")
    text((18, 7), "harmony-shell  /  ~/workspace", "green")
    text((WIDTH - 246, 7), "TUI  |  local  |  demo", "dim")
    text((SPLIT + 20, 50), "[2] AI / environment assistant", "dim")
    rectangle((SPLIT + 20, 79, WIDTH - 20, 80), "line")

    for index, (content, tone) in enumerate(scene["shell"]):
        assert not any(marker in content for marker in ("[ai]", "[verify]", "[task", "[shell]", "[input]"))
        text((20, 56 + index * LINE), content, tone, SPLIT - 42)
    text((SPLIT + 20, 90), scene["task"], "dim", WIDTH - SPLIT - 42)
    for index, (content, tone) in enumerate(scene["ai"]):
        text((SPLIT + 20, 122 + index * LINE), content, tone, WIDTH - SPLIT - 42)

    prompt_top = 56 + len(scene["shell"]) * LINE
    command_left = text((20, prompt_top), "developer@harmony:~/workspace$ ", "green")
    cursor = text((command_left, prompt_top), scene["draft"], "text", SPLIT - command_left - 22)
    if scene["focus"] == "shell":
        rectangle((cursor + 2, prompt_top, cursor + 10, prompt_top + 21), "green")

    rectangle((SPLIT + 16, 454, WIDTH - 16, 487), "bar")
    text((SPLIT + 22, 458), "?", "cyan")
    cursor = text((SPLIT + 46, 458), scene["ask"], "text", WIDTH - SPLIT - 74)
    if scene["focus"] == "ai":
        rectangle((cursor + 2, 458, cursor + 10, 479), "cyan")

    text((SPLIT + 20, 490), "Enter 仅发送问题，不执行命令", "dim")
    text((SPLIT + 20, HEIGHT - 26), scene["state"], "green", WIDTH - SPLIT - 42)
    path = SCRATCH / f"tui-scene-{scene['number']}.png"
    image.save(path)
    return path


def wrapped_text(pdf, text, x_pos, y_pos, width, font_size=13, line_height=20, color="#4A596B"):
    pdf.setFont("CJK", font_size)
    pdf.setFillColor(color)
    current = ""
    for character in text:
        if pdfmetrics.stringWidth(current + character, "CJK", font_size) > width:
            pdf.drawString(x_pos, y_pos, current)
            y_pos -= line_height
            current = character
        else:
            current += character
    if current:
        pdf.drawString(x_pos, y_pos, current)
    return y_pos


def build():
    destination = OUTPUT / "harmony-shell-tui-scenarios.pdf"
    pdf = canvas.Canvas(str(destination), pagesize=(1280, 850))
    pdf.setTitle("Harmony Shell - TUI 用户体验场景")
    pdf.setAuthor("Harmony Shell 产品设计")
    pdf.setSubject("直接回显建议命令，由用户在 Shell 中按 Enter 执行")
    for scene in SCENES:
        image = terminal_image(scene)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.rect(0, 0, 1280, 850, fill=1, stroke=0)
        pdf.setFont("Mono", 11)
        pdf.setFillColor("#4A647B")
        pdf.drawString(56, 815, f"HARMONY SHELL / TUI EXPERIENCE / SCENE {scene['number']}")
        pdf.setFont("CJK", 25)
        pdf.setFillColor("#14293C")
        pdf.drawString(56, 770, scene["title"])
        wrapped_text(pdf, scene["subtitle"], 56, 740, 1168, 13)
        pdf.drawImage(str(image), 56, 170, width=1168, height=548)
        wrapped_text(pdf, "交互  " + scene["behavior"], 56, 140, 1168, 13, color="#243E53")
        wrapped_text(pdf, "边界  " + scene["boundary"], 56, 108, 1168, 12)
        pdf.setStrokeColor("#D6DEE6")
        pdf.line(56, 67, 1224, 67)
        pdf.setFont("CJK", 10)
        pdf.setFillColor("#647586")
        pdf.drawString(56, 44, "2026-09-27  |  界面场景图，不代表目标设备已具备相应能力；所有检查与执行结果均为示例。")
        pdf.setFont("Mono", 10)
        pdf.drawRightString(1224, 44, f"{scene['number']} / 06")
        pdf.showPage()
    pdf.save()
    reader = PdfReader(destination)
    assert len(reader.pages) == len(SCENES)
    for page, scene in zip(reader.pages, SCENES):
        assert scene["title"] in page.extract_text()
    print(destination)
    print(f"Validated {len(reader.pages)} pages; terminal text fits all pane bounds.")


if __name__ == "__main__":
    build()
