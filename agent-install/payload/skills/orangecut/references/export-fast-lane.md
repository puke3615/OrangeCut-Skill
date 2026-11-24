# 参考:导出快车道,以及怎么留在上面

**[社区版免费]** 默认使用 `<= 1080p` 横竖屏无水印 CPU（`libx264`）导出。**[Pro]** NVENC / GPU 硬编和 `> 1080p` 导出在设置参数前先查询 `oc license status --json`；社区版不主动请求 4K 或强制 GPU，不以失败重试试探授权。遵循 [统一 Skill 分级规则](../SKILL.md)，不改工程真值来绕过画幅边界。

导出走两条路线之一。由服务来选;没有请求 flag 能指定路线,也不该有——
选择取决于 ffmpeg 能否精确复现画面,这是时间线的属性,不是偏好。
Agent 能控制的是时间线,平常的剪辑选择决定路线。本页讲怎么读这个
决定,以及怎么避免一次编辑无意间丢掉快车道资格。

## 两条路线

**`layered`** — 快车道。时间线只有一条视频 lane,再没有别的东西作画,
所以每个输出像素都已存在于源文件中:ffmpeg 从各自的源里切出每个 Clip,
拼接后一次编码。不启动浏览器。

**`classic`** — 浏览器逐帧渲染并截屏,再编码。它能复现编辑器可表达的
一切,代价是在 2019 款 Intel 笔记本上每帧固定约 80ms,与画面内容无关。

单机实测,9 个 Clip 首尾相接,768×1376 / 24fps,1435 帧(59.8s),
`--preset publish --crf 26`:

| 路线 | 墙钟耗时 | 对未动源片的 SSIM |
|---|---|---|
| `layered` | **15.6s** | 0.9853 |
| `classic` | 132s | 0.9801 |

快车道不是画质妥协:它反而*更接近*源片,因为 classic 路线要多付
一轮 Chromium 解码/截屏。帧数、时长、画布、像素格式与 BT.709 标记
完全一致,两条路线的音频逐字节相同(两边都由同一个音频收尾环节产出)。

## 读出一次导出走了哪条路线

每个导出 Job 的快照都带着它,从 `oc export start` 起就有:

```bash
oc export start --output /abs/out.mp4 --preset publish --json
# → data.snapshot.route == "layered" | "classic"
#   data.snapshot.fallbackReason == "<why the fast lane declined>"  (classic only)
oc job watch <job-id> --json     # same two fields, all the way to terminal
```

导出比预期慢时,第一个要读的就是 `fallbackReason`。它点名未满足的
确切条件,而下面每个条件都对应一个可改的编辑。

## 什么让时间线留在快车道

| 要求 | 什么会破坏它 | 应该怎么做 |
|---|---|---|
| 一条视频 lane,Clip 首尾相接 | 两个 Clip 之间有 gap——哪怕一帧 | 补上它(`oc timeline gap-remove`),或按 `oc timeline snapshot` 把下一个 Clip 放在上一个 Clip 的精确结束帧 |
| Clip 不得重叠 | 两个视频 Clip 覆盖同一时刻(出现第二条视频 Track) | 只保留一条视频 Track;目标区间被占时 `oc timeline add` 会开新 Track,所以添加后要读 snapshot |
| lane 覆盖整条 Sequence | 视频不从 0 开始,或在 Sequence 时长之前结束 | 第一个 Clip 从第 0 帧开始;Sequence 的时长就是 lane 的终点 |
| 每个源都是画布尺寸 1:1 | 某个 Clip 的文件不是精确的画布尺寸(需要缩放器) | 按源尺寸建 Sequence(`oc project create --match <file>`),或接受 classic 路线 |
| 每个源的帧率等于 Sequence 帧率 | 往 24fps Sequence 里混 30fps b-roll | 先归一化那个例外文件(`ffmpeg -fps_mode cfr -r <rate> …`) |
| 剪切点落在帧网格上 | 某个 Clip 的起点或媒体偏移不是整帧 | 用基于帧的命令(`--at-frame`、`--start-frame`),绝不手算秒数 |
| 源像素原样使用 | 变速、倒放、定格、变换、缩放、透明度、滤镜 | 这些必须走 classic 路线;没有绕开的办法 |
| 上层什么都不画 | 字幕、文字贴纸、形状、HTML 组件 | 见下文 |

掐头没有问题:从源中段开始的 Clip 仍在快车道上,只要裁点落在帧边界。

## 叠加层

带字幕、贴纸、形状或 HTML 组件的 Sequence 是另一种形态:这些层仍得由
浏览器渲染,快车道只能省下"画整个画布"与"只画叠加层"之间的差额。
这个变体已按成本自动路由：先通过同一条视频车道白名单，再比较叠加层的实际截图量。
短片的启动成本可能使它比 classic 更慢，不能用“有字幕”直接推断路线。
读取本次 Job 的 `route` 和 `fallbackReason`，按本机同类完整工程实测做预算。
`ORANGECUT_LAYERED_EXPORT=0/1` 是运维诊断与回退开关，不是请求 flag。

不要为取得快车道资格删改作品内容、拆成辅助工程或预混音。复杂画中画、混合尺寸/帧率素材
及由 HTML 画面填充的区间，可以继续使用 classic；性能改进应保留这份创作结果。

Windows 已验证的完整 Publish 配置会自动选择校准 NVENC 与有界并行；以 Job 日志中的实际编码器为准。
至少 60 秒的完整 MP4 在同一程序版本成功导出一次后，画面身份完全不变的重导可命中完整画面缓存。
响度或不改变画面源码的音量包络修改仍会重新混音；修改字幕、镜头、素材、参数或程序会保守失效。
`ORANGECUT_PICTURE_CACHE` 日志明确报告命中；不要把它理解为任意局部剪辑都已支持分段增量渲染。

## Windows 稳定导出

完整与区间导出均关闭 streaming-encode，使用磁盘落帧；不以启用 streaming 排查崩溃。
CPU 编码、软件浏览器、低内存模式，以及至少 1080×1920 且 30 秒的任务默认至多两个 worker。
运维可用 `ORANGECUT_RENDER_WORKERS=1..24` 显式覆盖；它是进程环境，不是 Project 修改。
可识别的 GPU / 截图 / evaluate / EOF 失败只在原进程树退出后自动重试一次：单 worker、
CPU 编码、软件浏览器，保留质量参数。取消、源结构错误与总期限不重试；回退画面不发布为 GPU 缓存。

用户 `--output` 可含中文；渲染与音画中间文件始终位于独占 ASCII 临时目录，成品才复制到
目标旁的 staging 并原子替换。系统 TEMP 含中文时自动尝试 Windows 安全回退目录；也可设置
`ORANGECUT_RENDER_TEMP_ROOT` 为可写绝对 ASCII 根目录。任务结束或失败后清理工作区，失败不覆盖旧成片。

## 给批量任务做预算

对批量交付,这个差距就是可行性本身:50 条一分钟的片子,快车道约
15 分钟导完,classic 路线约 2 小时。批量跑得慢时,先查一个 Job 的
`fallbackReason` 再谈其他优化——24fps Sequence 里混进一个 30fps Clip,
就会把整批的每次导出都推上慢路线。
