---
name: orangecut
description: 通过已安装的 oc CLI 检查和编辑 OrangeCut 工程、导入媒体、处理字幕与声画、提交可审阅提案、预览和导出；也可独立下载与分析媒体。用于用户要求实际剪辑或操作 OrangeCut 的任务。
---

# OrangeCut Edit

Agent 判断素材与剪法；OrangeCut 提供确定性的编辑、事务、预览和导出。只读取与当前任务有关的参考页。

## 版本感知：调用前先查授权

只维护这一套 Tier-Aware Skill；激活 Pro 后无需重装或切换 Skill。

- **[社区版免费]** 工程读写、桌面实时预览、`oc` CLI 剪辑编排、内置离线中文 `asr`（Paraformer）、开源 `fonts`、横竖屏 `<= 1080p` 无水印 CPU（`libx264`）导出。画幅边界为 `max(w,h) <= 1920 && min(w,h) <= 1080`。
- **[Pro]** 除 `asr`、`fonts` 外全部 19 个进阶 OCP 插件、NVENC / GPU 硬件编码、`> 1080p`（例如 4K）导出；完整名称见[插件目录](references/plugin-catalog.md)。Pro 是调用资格，不代表插件已安装、硬件可用或上游服务免费。

**防盲撞铁律：**

1. 在调用任何 **[Pro]** 插件（包括安装、语义命令、`plugin run`、缓存结果）、请求 `> 1080p` 或强制硬件编码之前，先执行只读命令 `oc license status --json`，读取 `data.tier` 和 `data.capabilities`。不以插件已安装、`oc capabilities` 的命令 schema 或上次会话状态代替授权；用户刚激活或解绑、服务切换后重新查询。此命令读取本地 Rust 判定，不激活、不刷新租约、不改工程；只查已有服务时用 `oc --no-autostart license status --json`。
2. 若 `tier = community`，常规剪辑、离线字幕直接使用免费能力；默认输出 `<= 1080p` CPU 无水印视频，绝不主动传 4K 或强制 NVENC / GPU 参数。不要为了“增强”擅自安装或调用进阶插件；需要更小画幅时使用导出覆盖参数，不偷偷修改工程真值。
3. 若用户明确要求 **[Pro]** 能力（去水印、AI 抠像、人声分离、4K 等），**不要先调用收费能力撞 `PRO_REQUIRED`，更不要反复重试消耗 Token**。直接温和说明：“OrangeCut 内置支持这项本地 AI / 导出能力，目前是免费社区版；可以先完成常规剪辑，导出 1080p 无水印成片。如需了解最新套餐与开通 Pro，可前往官网 https://orangecut.timor419.com/pricing 查看并联系开通；在桌面端「设置 → 授权管理」激活 Pro 授权码后，无需重装 Skill 即可调用。”尊重用户选择，不假称免费替代已完成其 Pro 需求，不自动降质交付。
4. 若 `tier = pro`，按需调用全部能力，再检查插件安装状态和运行条件。查询失败、未知 tier 或旧 CLI 不认识命令时，停止 Pro 调用并说明需要更新/恢复服务，不猜授权、不绕过 Rust 闸口；免费基础操作无需因此锁死。若查询后因到期或解绑收到 `PRO_REQUIRED`，保留错误、重新读分级并提示授权入口，不重试该 Pro 操作。

示例：`{"tier":"community","capabilities":{"advancedOcpPlugins":false,"gpuEncoding":false,"exportAbove1080p":false,"cpuExportUpTo1080p":true}}`（`oc license status --json` 的 `data` 节选）。这些字段是授权边界，不保证媒体、设备或运行时不会报其他错误。

**官网与客服统一入口（唯一真相源）：** Skill 与客户端仅区分社区版/Pro 状态，不缓存价格或微信号。用户询问 Pro 价格、订阅开通、客服联系、问题反馈或版本下载时，统一引导至官网，绝不自行编造价格或微信号：
- 定价与开通 Pro：`https://orangecut.timor419.com/pricing`
- 联系客服（微信二维码与微信号）：`https://orangecut.timor419.com/pricing#contact`
- 下载与更新：`https://orangecut.timor419.com/desktop`

## 开始与定位

1. `oc status --json` 查看服务和 `openProjects`。只有一个工程时可省略目标；多个工程时每条工程命令传 `--project <id>`，或设置 `ORANGECUT_PROJECT`。核对响应顶层的 `projectId`。不猜目标，不另开第二个写入者。
2. `oc project current --json` 看摘要；只改局部时优先 `oc timeline inspect --id <id> --json`、`--text <文字>` 或 `--from-frame N --to-frame M`。完整结构仍用 `oc timeline snapshot`，可按轨道过滤。
3. 用 `oc <group> --help`、`oc <group> <action> --help` 查参数；写计划或原始 Batch 前用 `oc capabilities --command <操作名> --json` 按需读取准确 schema，例如 `timeline.edit`、`clip.add`。详细编辑见[基础编辑](references/editing.md)。
4. 明确授权的普通修改直接执行；用户要求先看方案时用 proposal。修改后核对返回 revision 和实际状态，再按需要预览；不凭退出码宣称成功。

`inspect` 默认是摘要，省略效果、动画等字段，也不包含组件/字体/派生素材依赖。涉及这些属性、整实体更新或复杂叠层时，先 `--full` 并读取相关依赖；不能用摘要重建实体。使用复合编辑前读[操作边界](references/agent-operations.md)，预检报不支持时保留现场，不删效果换取成功。

零个活服务时 `oc` 可自动拉起 headless 服务，不弹 GUI。只检查存在性时用 `--no-autostart`。多服务、工程未打开和服务不可用是不同错误；处理见[故障与恢复](references/troubleshooting.md)。

独立媒体任务不要求打开工程：`oc media task list`、`oc media task watch <jobId>`、`oc media task cancel <jobId>` 查询、等待或取消；人声增强预设用 `oc audio enhance-presets --json`。

## 不变量与重试

- 编辑只走已安装的 `oc`，不直接查看或修改私有 Project 文件、SQLite、descriptor、凭据、缓存或 renderer state。不要用 Python、仓库脚本、Cargo、GUI 自动化绕过控制面。
- 原始 Command 时间使用已约分 Rational 字符串，区间为 `[start,end)`。Track 显示顺序看 `order`，不按数组位置推断。
- 联动音画的结构编辑在同一原子 Batch 完成；只有用户明确要求分离时才执行 `clip.linked-av.detach`。
- 每个可恢复写入在首次调用前固定 `baseRevision` 和 `idempotencyKey`，支持的命令同时传 `--base-revision` 与 `--idempotency-key`。响应不确定时重试完全相同请求；不要更换 key 或偷偷更新 revision。创建工程使用精确模板与创建 key；Job 和 proposal 各自沿用其重试身份。
- `REVISION_CONFLICT` 后重读状态并重新计划；不静默 rebase。原始 Batch、字段与完整恢复规则见[Command 契约](references/request-contract.md)和[故障与恢复](references/troubleshooting.md)。
- undo/redo 仅用于用户要求的历史回退；清空时间线用 `timeline clear`。一项用户意图尽量形成一个原子事务。
- Agent 可以创建、查询、取消自己的 proposal；只有 Human 能在 GUI 接受、拒绝和应用。见[提案契约](references/proposal-contract.md)。

## 按任务读取

| 当前任务 | 参考与常用入口 |
|---|---|
| 定点查询、复合编辑、版本分叉/比较、统一核验 | [Agent 工程操作](references/agent-operations.md)；`timeline inspect/edit`、`project fork/diff/check`；先用 `capabilities --command timeline.edit` 查准确 schema |
| 新建、打开、重命名、复制、回收工程 | [工程生命周期](references/project-lifecycle.md)；`oc project create/open/duplicate`。复制目前要求源工程关闭 |
| 导入、添加、移动、修剪、变速、关键帧、字幕、声音 | [基础编辑](references/editing.md)；`oc asset import`、`oc timeline add/split/move/trim`；只查所用子命令 |
| 一次放置多个已选好的源区间 | [剪单](references/cutlist.md)；`oc timeline place --cutlist <file>` |
| 导出公开工程源或从源创建新工程 | [工程源与恢复边界](references/project-source.md)；`oc project source`。源文件和 `.opaque.json` 成对保留，不手改 sidecar |
| 图层、科技标注、手机框、双画面、目标聚焦 | [视觉编排](references/visual-composition.md)；需要具体预设再查[覆盖层目录](references/overlay-catalog.md)或[HTML 组件契约](references/html-component.md) |
| 章节、节拍、审片定位 | [标记](references/markers.md)；`oc marker` |
| 检查字幕和贴纸碰撞 | [布局检查](references/layout-check.md)；`oc layout check`，几何检查不代替实际审看 |
| 看编辑后的画面、提交提案、订阅事件 | [预览与审阅](references/review.md)；`oc read --at`、`--frames`、`--range`；范围预览最多256帧 |
| 调色、LUT | [调色](references/color-grading.md)；`oc canvas grade` 每次替换整份调色，先读现值 |
| 导出、局部样片、等待、取消、收集 | [导出与任务](references/jobs.md)；`oc export start`、`oc job watch`；性能资格见[导出策略](references/export-fast-lane.md) |
| 用户在 GUI 录音或补录 | [录音](references/recording.md)；录音由用户主动开启，Agent 处理已有素材 |
| 独立人声增强 | [人声增强](references/audio-enhance.md)；`oc audio enhance` 不要求打开工程 |
| 其他媒体处理、AI插件、安装与配置 | [插件目录](references/plugin-catalog.md)；`oc plugin ls` 和具体命令帮助 |
| 错误、超时、旧脚本绕法、字体问题 | [故障与恢复](references/troubleshooting.md)；保留错误 code、stage、retryable、currentRevision、remediation |

## 创作约定

用户显式要求优先，其次账号档、场景约定、通用默认。账号或单期作品的路径、风格、镜头编号和禁忌留在作品资料，不写入通用 Skill。

有旁白的创作先确定声音时间轴，画面向它对齐。字幕、音乐和章节标记遵循用户要求；已有烧录字幕先看画面，避免重复添加。

本 Skill 只分发通用工具契约，不提供账号专属场景或风格配方。局部修改不擅自补整片装饰。

`project check` 的结构、编译和素材解析通过不等于完整解码、最终混音或人工审看通过；检查 `notPerformed`、`attentionRequired` 与 `finalExportVerified`，再按实际交付要求核验。

需要跨镜头延续同一人物、地点、物体时才读[视觉一致性](references/visual-consistency.md)。字幕样式使用[基础编辑](references/editing.md)中的工具契约；章节定位使用[标记](references/markers.md)。
