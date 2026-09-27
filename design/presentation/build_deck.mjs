import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const runtimeModules = process.env.RUNTIME_NODE_MODULES;
const skillDir = process.env.SKILL_DIR;
const runtimePython = process.env.RUNTIME_PYTHON;
if (![runtimeModules, skillDir, runtimePython].every(value => value && path.isAbsolute(value))) {
  throw new Error('Set RUNTIME_NODE_MODULES, SKILL_DIR and RUNTIME_PYTHON to supplied runtime paths');
}
const requireRuntime = createRequire(path.join(runtimeModules, '__runtime__.cjs'));
const { Presentation, PresentationFile, FileBlob } = await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const { resolvePresentationFont, finalizePresentation } = await import(pathToFileURL(path.join(skillDir, 'container_tools/artifact_tool_utils.mjs')).href);
const family = resolvePresentationFont({ fontFamily: 'Arial Unicode MS' });
const temporary = path.join(root, 'tmp/presentation-release');
const finalPath = path.join(root, 'output/presentation/harmony-ai-shell-product-design.pptx');
await fs.mkdir(temporary, { recursive: true });
await fs.mkdir(path.dirname(finalPath), { recursive: true });
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const colors = { ink: '#193348', muted: '#536A7B', blue: '#286B98', teal: '#317565', pale: '#F1F5F7', dark: '#0F1922', mint: '#A6D8C3' };
const slides = [];

function text(slide, value, left, top, width, height, size = 28, options = {}) {
  const shape = slide.shapes.add({
    geometry: 'textbox',
    name: options.name ?? `text-${slide.shapes.items?.length ?? left}-${top}`,
    position: { left, top, width, height },
    fill: 'none', line: { fill: 'none', width: 0 },
  });
  shape.text = value;
  shape.text.style = {
    typeface: family, fontSize: size, bold: options.bold ?? false,
    color: options.color ?? colors.ink, autoFit: 'none',
    verticalAlignment: 'top', insets: { left: 0, right: 0, top: 0, bottom: 0 },
  };
  return shape;
}

function addSlide(title, subtitle, sources, options = {}) {
  const slide = presentation.slides.add();
  slide.background.fill = options.dark ? colors.dark : '#FFFFFF';
  const number = slides.length + 1;
  if (title) text(slide, title, 56, 40, 1168, 70, 44, { bold: true, color: options.dark ? '#FFFFFF' : colors.ink, name: 'slide-title' });
  if (subtitle) text(slide, subtitle, 56, 119, 1168, 55, 24, { color: options.dark ? colors.mint : colors.muted });
  text(slide, String(number), 1185, 684, 40, 25, 16, { color: options.dark ? colors.mint : colors.muted, name: 'folio' });
  slide.speakerNotes.textFrame.setText(sources);
  slides.push(slide);
  return slide;
}

async function image(slide, relative, left, top, width, height, alt) {
  slide.images.add({ blob: new Uint8Array(await fs.readFile(path.join(root, relative))), contentType: 'image/png', fit: 'contain', position: { left, top, width, height }, alt });
}

function table(slide, values, widths, top = 198, rowHeight = 76, size = 25) {
  const native = slide.tables.add({ rows: values.length, columns: values[0].length, left: 56, top, width: 1168, height: values.length * rowHeight, values, columnWidths: widths });
  native.borders.assign({ style: 'solid', fill: '#D8E2E8', width: 0.8 });
  for (let row = 0; row < values.length; row += 1) {
    native.rows[row].height = rowHeight;
    for (let column = 0; column < values[row].length; column += 1) {
      const cell = native.getCell(row, column);
      cell.fill = row === 0 ? colors.ink : (row % 2 === 0 ? colors.pale : '#FFFFFF');
      cell.text.style = { typeface: family, fontSize: size, bold: row === 0, color: row === 0 ? '#FFFFFF' : colors.ink, verticalAlignment: 'middle', autoFit: 'none' };
    }
  }
  native.cells.block({ row: 0, column: 0, rowCount: values.length, columnCount: values[0].length }).assign({ margins: { left: 16, right: 16, top: 14, bottom: 14 } });
  return native;
}

const cover = addSlide('', '', '来源：PRODUCT_DESIGN.md 当前有效交互；PROJECT_ARCHIVE.md；DEVELOPMENT_GUIDE.md。项目仍处于设计与契约样例阶段，未进行目标设备产品验证。', { dark: true });
text(cover, 'Harmony 智能 Shell', 72, 190, 1120, 105, 66, { bold: true, color: '#FFFFFF' });
text(cover, '命令与开发环境助手', 76, 319, 1000, 66, 38, { color: colors.mint });
text(cover, '普通 Shell 操作习惯，配合可追溯的环境解决方案', 76, 415, 1120, 66, 27, { color: '#D6E3E9' });
text(cover, '产品体验与设计方案   2026.09', 76, 616, 1000, 32, 21, { color: '#A6BBC8' });

const problem = addSlide('从开发者的一条命令开始', '目标是帮助用户完成环境任务，减少查找和判断适配路径的负担', '来源：PROJECT_DISCUSSIONS.md D-001、D-005；PRODUCT_DESIGN.md。社区资料分散属于项目提出的背景，不表示已完成生态量化调研。');
text(problem, 'brew install <工具>', 72, 214, 1100, 72, 44, { bold: true, color: colors.blue });
text(problem, '用户已经知道想做什么', 72, 337, 520, 55, 32, { bold: true });
text(problem, '安装工具或配置运行环境\n希望继续使用熟悉的命令', 72, 414, 520, 124, 29);
text(problem, '系统需要提供可用路径', 700, 337, 500, 55, 32, { bold: true });
text(problem, '识别真实环境与失败原因\n匹配有依据的适配方案', 700, 414, 500, 124, 29);
text(problem, '当前范围：命令与开发环境。工程业务实现和源码 bug 分析不在第一版范围内。', 72, 612, 1120, 54, 23, { color: colors.muted });

const division = addSlide('主 Shell 与 AI 侧栏各司其职', 'AI 帮助分析，用户保留命令提交权', '来源：PRODUCT_DESIGN.md D-008 至 D-010；SESSION_PROTOCOL.md 第 6 节。');
text(division, '主 Shell', 72, 212, 510, 65, 40, { bold: true, color: colors.blue });
text(division, '提示符、命令、原始输出\n保持普通终端的使用习惯\n建议只填入可编辑输入行', 72, 302, 520, 200, 30);
text(division, 'AI 侧栏', 700, 212, 500, 65, 40, { bold: true, color: colors.teal });
text(division, '询问、分析、依据与风险\n解释当前任务和验证状态\nEnter 只提交问题', 700, 302, 500, 200, 30);
text(division, '用户在主 Shell 按 Enter，命令才开始执行', 72, 571, 1120, 65, 36, { bold: true, color: colors.teal });

const failure = addSlide('失败后，建议直接回显', '侧栏解释依据和影响，主窗口等待用户 Enter', '来源：design/presentation/assets/tui-scene-02.png，来自既有 TUI 场景设计；PRODUCT_DESIGN.md 第 14 节。图中的 python3 检查结果仅为示例，不证明设备能力。');
await image(failure, 'design/presentation/assets/tui-scene-02.png', 56, 180, 1168, 470, '命令失败后，AI 侧栏给出说明，建议填入普通提示符，尚未执行');
text(failure, '场景示意。检查结果与命令均非目标设备实测。', 56, 660, 1100, 28, 18, { color: colors.muted });

const ask = addSlide('操作前，也可以先问', '用户可以询问能力、安装路径和命令影响', '来源：design/presentation/assets/tui-scene-01.png；PRODUCT_DESIGN.md 事前询问设计。具体快捷键与窄窗口布局仍待实现验证。');
await image(ask, 'design/presentation/assets/tui-scene-01.png', 56, 180, 1168, 470, '用户在 AI 侧栏进行事前询问，主 Shell 保持普通终端');
text(ask, '一般询问可以不带终端上下文。当前任务询问只读取本页授权材料。', 56, 660, 1120, 28, 18, { color: colors.muted });

const input = addSlide('执行后，结果仍在侧栏说明', '主窗口保留真实命令输出，AI 区分执行结果与验证结论', '来源：design/presentation/assets/tui-scene-04.png；PRODUCT_DESIGN.md。图中的创建与验证结果仅为场景示例，不代表目标设备实测。');
await image(input, 'design/presentation/assets/tui-scene-04.png', 56, 180, 1168, 470, '用户 Enter 执行后，主 Shell 返回提示符，AI 侧栏展示结果与影响');
text(input, '自动回显仅发生在可确认的空闲提示符。编辑器、REPL 和输入法组合态不注入。', 56, 660, 1130, 28, 18, { color: colors.muted });

const journey = addSlide('一次环境任务的完整体验', '从发现问题，到看到真实执行结果', '来源：DEVELOPMENT_GUIDE.md 第 6 节；API_CONTRACTS.md。此页描述目标体验，不表示全部已实现。');
table(journey, [['阶段', '用户看到什么', '系统承担什么'], ['发现', '真实命令结果或主动询问', '固定本页任务与上下文'], ['分析', '侧栏展示依据与限制', '检索适用配方，必要时补问'], ['建议', '命令进入普通输入行', '程序校验，保护现有草稿'], ['执行', '用户 Enter 后正常运行', '关联真实开始与结束事件'], ['验证', '侧栏说明结果与未知项', '不把回显或 exit 0 当作全部成功']], [180, 480, 508], 184, 75, 24);

const ownership = addSlide('会话内部的能力归属', '每页独立管理上下文、任务和模型请求', '来源：SESSION_PROTOCOL.md D-014；AGENT_ENGINEERING.md 第 5 节。下表是逻辑归属，不规定线程或进程数量。');
table(ownership, [['对象', '职责'], ['ShellSession', '拥有终端事实和输入缓冲区'], ['AISession', '拥有本页上下文、授权和生命周期'], ['AISession 内的 Scheduler', '编排检索、有限工具调用、校验与取消'], ['会话内的 ModelService', '处理模型配置、推理请求与流式响应'], ['AIWorker', '承载和路由逻辑会话，不合并历史']], [430, 738], 184, 75, 25);

const shared = addSlide('多个页面可以共享 AI 进程', '共享宿主资源，每页仍保留独立逻辑会话', '来源：output/diagrams/session-architecture/03-shared-ai-process.png；SESSION_PROTOCOL.md 第 11、12 节。图为已整理的设计方案，具体 IPC 和部署默认值待目标设备验证。');
await image(shared, 'output/diagrams/session-architecture/03-shared-ai-process.png', 56, 177, 1168, 470, '多个 PageHost 对应独立 AISession，由同一 AIWorker 承载');
text(shared, 'AIWorker 故障不能连带结束外部普通 Shell。重建后拒绝旧绑定的迟到结果。', 56, 657, 1140, 35, 21, { color: colors.muted });

const workflow = addSlide('受控 Agent 的工作方式', '固定流程承担安全边界，模型处理歧义和证据选择', '来源：AGENT_ENGINEERING.md D-020；DEVELOPMENT_GUIDE.md。未声称多轮工具调用已带来实际准确率提升。');
const workflowRows = [['01', '环境事实', '采集当前任务需要的信息'], ['02', '证据与配方', '按系统、架构和适用条件过滤'], ['03', '有限补取', '信息不足时补证据或询问用户'], ['04', '程序校验', '检查参数、来源和当前输入状态'], ['05', '用户提交', '真实执行后再更新结果']];
workflowRows.forEach((row, index) => {
  const top = 202 + index * 84;
  text(workflow, row[0], 72, top, 95, 60, 39, { bold: true, color: colors.blue });
  text(workflow, row[1], 205, top + 3, 250, 58, 31, { bold: true });
  text(workflow, row[2], 530, top + 6, 660, 58, 28);
});

const knowledge = addSlide('知识包、证据与配方', '用可追溯的数据组织方案，用可信程序生成命令', '来源：KNOWLEDGE_CONTRACTS.md 与 KNOWLEDGE_INTEGRATION.md。三个名称是项目对象，不宣称属于同一行业标准。');
text(knowledge, '知识包', 64, 232, 350, 70, 41, { bold: true, color: colors.blue });
text(knowledge, '交付哪一版资料\n资源清单与文件摘要\n支持独立更新和撤回', 64, 329, 350, 190, 28);
text(knowledge, '证据', 466, 232, 350, 70, 41, { bold: true, color: colors.teal });
text(knowledge, '依据来自哪里\n原文、来源和适用范围\n区分陈述、观察与假设', 466, 329, 350, 190, 28);
text(knowledge, '配方', 868, 232, 350, 70, 41, { bold: true, color: colors.blue });
text(knowledge, '满足条件后做什么\n受限动作与验证要求\n引用固定版本的证据', 868, 329, 350, 190, 28);
text(knowledge, '本地知识包作为基础。向量检索和 MCP 根据实际需求增加。', 64, 603, 1140, 55, 27, { bold: true });

const context = addSlide('端侧与云侧共用上下文底座', '知识位置与模型位置可以独立选择', '来源：CONTEXT_OPTIMIZATION.md、KNOWLEDGE_INTEGRATION.md。所有预算仍须以具体模型和设备验证，未列未经实测的性能数字。');
table(context, [['设计项', '端侧路径', '云侧路径'], ['材料选择', '关键事实与小任务包', '经授权扩展相关证据'], ['历史管理', '结构化任务状态，按需补取', '同样保持本页隔离'], ['资源约束', '内存、并发与推理延迟', '输入限制、费用与网络'], ['隐私边界', '优先本地处理', '上传单独授权并脱敏'], ['执行权限', '程序校验，用户 Enter', '保持完全相同的执行边界']], [230, 440, 498], 184, 75, 24);

const safeguards = addSlide('命令进入提示符前的检查', '每一步检查都对应可复现的拒绝路径', '来源：API_CONTRACTS.md；ACCEPTANCE_MATRIX.md。校验只针对 AI 建议，不宣称拦截或保护所有用户自行输入的命令。');
table(safeguards, [['检查对象', '必须满足的条件'], ['身份与时效', '原页面、原请求、当前绑定代次，计划未过期'], ['知识与方案', '可信发布、配方适用、未撤回、参数有效'], ['终端与输入', '空闲提示符，输入版本匹配，不覆盖草稿'], ['命令与提交', '完整文本与正确转义，不附带回车']], [300, 868], 209, 84, 25);
text(safeguards, '无法确认时，建议留在侧栏并说明原因', 72, 645, 1100, 46, 27, { bold: true, color: colors.teal });

const roadmap = addSlide('从契约到目标设备验证', '先证明安全闭环，再接入模型和真实适配知识', '来源：IMPLEMENTATION_PLAN.md。里程碑没有承诺日期或人力，依赖目标平台与团队安排。');
table(roadmap, [['阶段', '主要交付', '退出条件'], ['M0', '平台与 Shell 输入桥验证', '明确支持能力与降级路径'], ['M1', '无模型安全回显链路', '不误执行、不覆盖、不串页'], ['M2', '知识与可信配方闭环', '证据可追溯，错误候选被拒绝'], ['M3', '模型与有限工具增强', '质量与资源代价可对照'], ['M4', '目标设备与发布验证', '真实任务和恢复流程可复现']], [135, 510, 523], 184, 75, 24);

const status = addSlide('当前交付与下一阶段', '设计和契约已经整理，产品实现与真机验证仍待推进', '来源：PROJECT_DISCUSSIONS.md D-022 至 D-024；DEVELOPMENT_GUIDE.md；design/knowledge/README.md。当前没有可安装终端程序或已验证社区配方。');
text(status, '当前交付', 72, 218, 520, 60, 38, { bold: true, color: colors.blue });
text(status, '产品与开发规格\nSession 和知识数据契约\n合成样例与校验工具\n用户体验图解与演示资料', 72, 313, 520, 228, 29);
text(status, '下一阶段', 704, 218, 500, 60, 38, { bold: true, color: colors.teal });
text(status, '确定目标设备和 Shell\n实现原子输入桥\n审核首批真实配方\n建立真机质量与资源基线', 704, 313, 500, 228, 29);
text(status, '对外展示的是设计方案。界面示意与合成数据不代表设备适配已经完成。', 72, 611, 1130, 56, 23, { color: colors.muted });

const close = addSlide('', '', '来源：DEVELOPMENT_GUIDE.md、IMPLEMENTATION_PLAN.md。此页为项目目标与下一阶段协作方向，不包含实测成效声明。', { dark: true });
text(close, '让开发者继续使用熟悉的 Shell', 72, 204, 1120, 102, 52, { bold: true, color: '#FFFFFF' });
text(close, '让每条环境建议都有依据和清晰的执行边界', 76, 355, 1110, 105, 34, { color: colors.mint });
text(close, '下一步：目标设备验证与首批可信配方', 76, 558, 1090, 70, 28, { color: '#D6E3E9' });

const candidate = path.join(temporary, 'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidate);
for (let index = 0; index < slides.length; index += 1) {
  const preview = await presentation.export({ slide: slides[index], format: 'png', scale: 1.5 });
  await fs.writeFile(path.join(temporary, `slide-${String(index + 1).padStart(2, '0')}.png`), new Uint8Array(await preview.arrayBuffer()));
  const layout = await slides[index].export({ format: 'layout' });
  await fs.writeFile(path.join(temporary, `slide-${String(index + 1).padStart(2, '0')}.layout.json`), await layout.text());
}
await fs.writeFile(path.join(temporary, 'build-summary.json'), JSON.stringify({ count: slides.length, font: family, candidate }, null, 2));

if (process.env.FINALIZE === '1') {
  await finalizePresentation({
    workspaceDir: root, candidatePath: candidate, finalPath,
    pythonExecutable: runtimePython,
    integrityValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--expected-slide-count', '16', '--validate-heading-fit', '--validate-bullet-geometry', ...[7, 8, 12, 13, 14].flatMap(number => ['--require-native-table-slide', String(number)])],
    requiredNativeTableOwnerSlides: [7, 8, 12, 13, 14],
    fontPolicy: { basis: 'design', families: [family] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(temporary, 'final-validation.json'),
  });
  const reopened = await PresentationFile.importPptx(await FileBlob.load(finalPath));
  const finalSlides = reopened.slides.items;
  for (let index = 0; index < finalSlides.length; index += 1) {
    const preview = await reopened.export({ slide: finalSlides[index], format: 'png', scale: 1.5 });
    await fs.writeFile(path.join(temporary, `final-${String(index + 1).padStart(2, '0')}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
  console.log(finalPath);
}
console.log(`Built ${slides.length} slides in ${temporary}`);
