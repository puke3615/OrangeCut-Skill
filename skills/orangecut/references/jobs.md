## 导出与 Job 生命周期

**[社区版免费]** 默认使用 `<= 1080p` 横竖屏无水印 CPU（`libx264`）导出。**[Pro]** NVENC / GPU 硬编和 `> 1080p` 导出在设置参数前先查询 `oc license status --json`；社区版不主动请求 4K 或强制 GPU，不以失败重试试探授权。遵循 [统一 Skill 分级规则](../SKILL.md)，不改工程真值来绕过画幅边界。

- 启动:`oc export start --output <absolute-path.mp4> [--sequence-id <id>] [--preset publish|compact|preview] [--idempotency-key <key>] --json`。
- 以 Sequence 未按其创作的帧率或质量交付:加 `--fps`(整数如 `30`,或精确比值如 `30000/1001`,绝不是小数)、`--crf 0-63`(越低越好看也越重)或 `--bitrate-kbps`。各自独立,且都不编辑 Sequence,所以一次剪辑可以交付成好几种版本。渲染器会拒绝的设置在请求上就被拒绝,而不是让 Job 中途失败。画面尺寸、编码器和容器在本构建上不可覆盖:本地渲染器要求渲染尺寸等于合成尺寸,并直接拒绝编码器覆盖;输出路径被规范化为 `.mp4`。要交付另一个尺寸,就按那个画布创作 Sequence。
- 列出本 Agent 的 Job:`oc job list --json`。
- 编码设备通常沿用默认策略。必须指定 CPU 时加 `--no-gpu`；诊断性请求硬件编码用 `--gpu`。这只影响本次导出，实际后端看 Job 日志，不能把请求 GPU 当成已使用的证据；具体 codec、尺寸和容器仍不能覆盖。
- `oc job watch <job-id> --json` **默认等到终态**(此前要显式 `--until-terminal`,不带就只拍一张快照立即返回——调用方以为等完了、导出其实还在半路,真踩过;旧 flag 仍接受但已是空操作)。只想看一眼当前进度用 `--no-wait`。`--timeout-seconds` 缺省 300;比这更长的导出就循环调用它,收到 `JOB_WATCH_TIMEOUT` 再接着等——那个错误意味着"还在跑",不是失败。
- 等 Job,绝不等输出文件。文件只在最后一刻出现,所以轮询文件分不清"还在渲"和"服务死了、Job 已 `interrupted`"——崩掉的导出会让文件监视挂满整个超时。`oc job watch` 在 Job 变为 `interrupted`/`failed` 的那一刻返回,并携带错误。
- 取消一个活跃 Job:`oc job cancel <job-id> --json`,然后收取它的终态清理结果。
- 幂等收取:`oc job collect <job-id> --json`。成功的导出只暴露 `outputFileName`,绝无绝对路径。
- 只有当终态快照说失败可重试时才重试:选一个紧凑的 key,运行 `oc job retry <job-id> --idempotency-key <key> --json`。响应不确定,就用完全相同的源 Job/key 对重复;OrangeCut 返回同一个替换 Job,进程重开后也是。刚被打断的 Job 还没有恢复出来的 RenderPlan,返回 `JOB_RETRY_UNAVAILABLE`;从当前 Project 状态发起新导出。

- 导出有两条路线,由服务选择:只有视频 Clip 首尾相接的 Sequence 走拼接源文件的 FFmpeg 通道(实测:同一部 60s 片,逐帧浏览器渲染 132s,它 15.6s,保真持平或更好);其余情况逐帧在浏览器里渲染。没有请求 flag 能选路线,但普通的剪辑选择决定它。Job 快照会说明走了哪条——`route: "layered"|"classic"`,快车道谢绝时附上 `fallbackReason`——所以每当导出比预期慢,先读 `fallbackReason`。条件、修法与批量预算:[references/export-fast-lane.md](export-fast-lane.md)。

Job 进度与终态更新共享快照优先的 `oc event watch` 控制流。把重连快照的 `jobs` 列表当作规范。Agent 凭据只能看到并控制本 Agent 创建的 Job;Human GUI 能看到打开的 Project 里的所有 Job。
