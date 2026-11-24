## 近期行为变化(带着旧记忆的会话先读这节)

SKILL.md 其余部分只描述"现在是什么"。如果你的记忆或脚本里存着下面这些
**旧绕法,它们已经过时,请主动清理**——继续用不会坏,但全是白费的功:

| 旧绕法 / 旧行为(2026-09-09 前) | 现在 |
|---|---|
| `timeline speed` 崩溃,定格靠 read 抽帧 + import + place 拼 | 直接 `speed --rate-percent/--freeze/--reverse`;插入式定格用 `timeline freeze-frame` |
| place 报 `PLACE_SOURCE_EXHAUSTED` 后减 1 帧重试 | 一帧以内自动收边,带 `PLACE_CLAMPED_TO_SOURCE` 警告 |
| 每次建完轨跑 `track move --to-top` 保住字幕 | place/add 新建视频轨自动垫到文字类轨道之下 |
| gap-insert 前手动收缩横跨的 BGM/贴纸再还原 | `gap-insert --split-crossing` |
| 宫格手拼 4 条全字段 rational transform | `timeline grid`;单格微调 `clip transform set`(部分更新) |
| compact 导出后外部 ffmpeg 二压给手机 | `export start --preset preview` |
| 删光 import-srt 的 cue 后项目拒渲,从 migrationReport 抠 id 手动删组件 | 已修:样式组件级联回收,孤儿只降级为警告 |
| `caption update --text` 后重挂 tokens/emphases | 对得上就保留;丢了响应里有 `droppedTokens`/`droppedEmphases` 回执,协议可直接传 `tokens` 写回 |
| `sticker update --preset` 后重新摆位置 | preset 只换看相不动排位;要重置排位显式 `--reset-placement` |
| tokens 与文本对不上时静默不高亮,渲染后靠肉眼发现 | 写入时直接拒 `CAPTION_TOKENS_MISALIGNED`(捷径端点与裸 command apply 都拦) |
| `job watch` 要自己轮询(不带 flag 只返回一张快照) | 默认等到终态;`--no-wait` 拍快照,`--until-terminal` 兼容保留 |
| 音频资产 place 报 incompatible,绕去 `timeline add` | 纯音频剪单自动建音频轨 |
| 展示字体缺一个字形整个 read 失败 | 内置 Noto 兜底接住 + 服务日志警告,两边都缺才失败 |
| 404 报 `SERVICE_ENDPOINT_UNKNOWN` 就去怀疑服务版本 | 带信封的 404 现在报真实错误(常见其实是 `PROJECT_NOT_OPEN`) |
| 想插一段反应梗:自己去抖音搜、下载、import、split、gap-insert、place、调音量 | `oc cutaway add <id> --at-frame N`,十四条内置,默认串联插进主画面轨;overlay/pip 是叠层选项 |

协议层面这轮只有**新增可选字段**(captions/update 的 `tokens`、
stickers/update 的 `resetPlacement`),无破坏性变更;caption/sticker add
的位置参数文本、裸 caption.update 的命令形状在这之前就是如此。


## 失败处理

- 排版要指定字体时,先 `oc asset list --kind font --json` 拿 id,再传给 `--font-asset-id`(caption add / add-batch / import-srt / sticker add 四条都要它)。**内置底座是黑体族**:Regular 走正文、Black 走字幕标题——**这两档之间没有中间字重**,想要 Bold 那一档要装插件。这不是锦上添花:`caption add` 的 `--font-weight` **默认就是 bold**,而字库里没有真正的 Bold 面,浏览器只能**合成假粗体**(把 Regular 的笔画描粗一圈,拐角会糊)。装了 fonts 插件后拿真 Bold 当 `--font-asset-id`,同一行字的笔画量实测 Light 68% / Regular 100% / **Bold 150%** / Black 175%,是一条干净的字重阶梯,而合成出来的那一档卡在 Bold 附近但形不对。发行构建另带六款展示体,各占一个语域:得意黑(爆点标题)、站酷庆科黄油体(圆体)、站酷快乐体(手写)、Noto Serif CJK SC(宋体)、站酷小薇(标题宋)、马善政楷书(毛笔)——它们按构建期取件,源码树里没取过就不在列表里,**以 `asset list` 的实际输出为准,别照本文档报菜名**。要楷体或缺的中间字重(黑体 Light/Medium/Bold、宋体 Bold)就 `oc plugin add fonts`【插件:fonts】(文件在 `oc plugin ls fonts --json` 的 `installDir/fonts/` 下);要别的字体就 `oc asset import <字体文件> --kind font`,认 `.ttf/.otf/.ttc/.otc`,返回的 `assetId` 直接当 `--font-asset-id` 用(系统字体也可以,例如 Windows 的 `%WINDIR%\Fonts\simsun.ttc`)。
- 报告失败时,保留 `code`、`stage`、`message`、`retryable`、`currentRevision` 和 `remediation`。
- 遇 `REVISION_CONFLICT`,重读当前状态并重建预期的编辑。绝不静默 rebase。
- 遇 `REQUEST_TIMEOUT`,请求超过了客户端超时(默认 30s,`OC_TIMEOUT_SECONDS` 可覆盖)——变更可能已经提交。CLI 已自动重放带幂等 key 的请求;`error.details` 携带 `idempotencyKey`/`baseRevision`,供手动重试完全相同的命令;慢的批量操作应调高 `OC_TIMEOUT_SECONDS`,而不是循环。
- 传输层不确定结果之后,只重试已固定其受支持重试身份的完全相同请求:Project 写入用 base revision + key,proposal create 用完整 proposal JSON + key,cancel 用 proposal ID,`job retry` 用源 Job + key。绝不在同一 key 下改参数。
- 遇 `PROPOSAL_STALE` 或 `PROPOSAL_EXPIRED`,重读时间线并新建 proposal。绝不静默复用或续期旧的。
- 遇 `LIVE_SESSION_AMBIGUOUS`,停下;不要按标题、新近程度、PID 或文件系统顺序选窗口。
- 遇 `EVENT_STREAM_CLOSED`、`EVENT_STREAM_TIMEOUT` 或其他可重试的流内故障,读安全的 `details.reconnectCursor`,原样传给下一次 `event watch`;下一个快照替换本地流状态。没有游标就裸重连。
- 遇 `HTTP_RESPONSE_TOO_LARGE` 或 `EVENT_STREAM_ENVELOPE_TOO_LARGE`,不要推断或保留部分快照。报告有界控制的局限;绝不以查看私有存储作为退路。
- 遇 `JOB_WATCH_TIMEOUT`,留着不透明的 Job ID,要么继续 watch,要么显式取消;不要假设失败或成功。
- 遇 `CLI_REQUEST_FILE_TOO_LARGE` 或 `CLI_REQUEST_STDIN_TOO_LARGE`,把工作重组成更小的原子级用户可见意图或 proposal;绝不截断 JSON,也绝不拆开联动的 A/V 对。
- 遇 `LOW_DISK`,清出空间并发起新导出。遇 `WORKER_INTERRUPTED`,收取终态诊断,从当前 Project 状态重新开始。
- 遇 `PROCESS_STARTUP_FAILED`(派生任务上是 `MEDIA_PROCESS_STARTUP_FAILED`),停下,不要改素材也不要改剪单:媒体子进程在加载阶段就被系统拒了,根本没跑起来,和素材、时长、骨架槽位一律无关。它 `retryable: false`,重试多少次都是同一个结果。唯一有效的动作是重启 OrangeCut 服务(10 分钟内攒够 3 次,服务会自己退场,交给宿主或 `oc` 自动拉起);重启后依旧如此,就报告这台机器有问题。要查根因就别让它自动退场:设 `ORANGECUT_STANDDOWN=off` 复现,趁那个半死进程还活着抓 handle/GDI 计数和内存 dump——退场日志里那句"跑成过多少个媒体子进程"跨重启比对稳定,就说明底下在按任务泄漏。曾经因为它被报成"媒体进程执行失败",有人往素材方向查了一个多小时,还白白劣化了四条成片。
- 失败的 Batch 必须让 revision 与 Project 哈希保持不变。不支持的能力必须闭合失败。
- **被迫绕过产品缺陷时,当场记一笔**:`oc feedback "<发生了什么,你改用了什么绕法>" [--repro <最小复现>]`。纯本地追加(数据根的 `feedback.md`),不碰服务,一秒钟的事。判断标准:凡是让你写出 workaround、重试循环、或"下次记得先 X"这类记忆的,都值得记。产品方定期收割这个文件——2026-09 那轮 22 条反馈全部变成了修复,源头正是一份这样的清单;你顺手一笔,下一个场景的 Agent 就不用再踩。
