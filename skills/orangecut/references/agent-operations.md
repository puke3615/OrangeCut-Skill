# 定点查询、复合编辑、版本与核验

这些入口只接收明确编辑意图。素材选择、自然语言理解和审美判断仍由上层 Agent 完成。
先 `oc <group> <action> --help` 查参数；`oc capabilities --command timeline.edit --json` 返回该入口的准确请求 schema，
也支持 `timeline.inspect`、`project.fork`、`project.diff` 和原始语义命令名（例如 `clip.add`）。

## 只读相关对象

```text
oc timeline inspect --text "需要修改的字幕文字" --kind caption --json
oc timeline inspect --id clip-a --id clip-b --json
oc timeline inspect --from-frame 300 --to-frame 600 --json
oc timeline inspect --external-ref "shot:opening" --full --json
```

响应包含 `projectId`、`revision`、精确范围、源区间、关联音画 ID；`--full` 才返回实体全部字段。
`projection` 明确指出摘要省略项及依赖未包含。完整实体仍不等于完整组件、字体或派生素材依赖，复杂修改需继续读取依赖；不能用摘要替换原实体。
默认上限200，最大1000，超过返回错误，绝不冒充已经读取全部。范围为半开区间且不裁短查询结果。
文本匹配只查询素材名称和字幕文字，不做语义搜索。使用外部引用时先从查询结果确认唯一实体；不要猜 ID。

## 一个计划，一个撤销单元

将明确操作写入 UTF-8 JSON，再执行：

```text
oc timeline edit --file <plan.json> --dry-run --json
oc timeline edit --file <plan.json> --json
```

```json
{
  "baseRevision": 7,
  "idempotencyKey": "replace-approved-take-01",
  "intent": "Replace the selected clip and preserve its placement and effects.",
  "operations": [
    {"op": "replace-source", "clipId": "clip-a", "assetId": "asset-new", "timing": "preserve"}
  ],
  "constraints": {"unchangedIds": ["clip-ending"]}
}
```

从真实查询填入 ID 和 revision。预检与正式提交使用同一份文件；结果不确定时也重试这份文件。
计划绑定完整输入及约束，不能在同一 key 下修改参数。过期 revision 明确失败，不自动套到新状态。
响应包含正式 `transaction` 和简明 `summary`；检查 `committed` 与新 revision，再按需要预览。

### 操作

- `replace-source`：匹配媒体种类，保留片段 ID、变换、效果与音画关联；`sourceStart` 为精确 Rational，默认0。
  `timing: preserve` 保持原时间槽和速度；`fit` 将剩余新素材适配原槽，明确会改变速度；
  `resize` 按新素材可用时长和原速度调整本片段尾部，不移动后续内容，可给 `durationFrames`；
  `ripple` 必须给 `durationFrames`，同时调整后续内容。源不够、发生重叠或无法保留效果时失败。
- `replace-narration`：输入独立音频 `clipId`、新 `assetId`、`captionTrackId`、要替换的 `captionIds` 与 `captions`。
  每条新 cue 是 `{text, sourceRange, tokens?}`，时间位于新录音的源时间轴；服务按起点、播放速度映射到时间线。
  一对一或文字唯一对应时继承原字幕的样式、说话人、强调色、动画及扩展；可用 `inheritFrom` 明确对应的旧字幕ID。
  多条字幕样式不同、强调词已不在新文本中、带动画但时长改变时，服务拒绝不明确的继承。
  可为cue提供完整 `presentation: {speaker, styleRef, emphases, motion, extensions}` 明确替换这些字段（可空字段填null；空数组/对象表示明确清除），不与inheritFrom同时使用。
  操作级 `styleRef` 可显式覆盖样式。其他字幕不变。timing 与 replace-source 相同，可用 `atFrame` 同时调整新旁白和字幕起点（不与 ripple 同用）。
- `audio-envelope`：`clipId` 指向声音片段，`points` 为 `[["局部时间分子/分母","线性增益分子/分母"], ...]`，时间严格递增且位于片段内。
  `interpolation` 默认 linear，也可 hold。只替换 gain 曲线，保留原 mix 的 pan、fade 等参数；无 mix 时创建一项。
  例如 `[["0/1","1/2"],["1/1","1/1"]]` 在第0秒半增益、第1秒原增益。输入使用精确分数字符串，项目真值仍为规范 Rational。
- `insert`：输入 `assetId`、明确的 `trackId`、`atFrame`、`durationFrames`，可给 `sourceStart`、`muted`。
  服务先在候选状态切分横跨位置的片段，再打开全轨空隙并放入素材，视频原声按规范联动。
  横跨位置的字幕、锁轨或不支持的映射会阻止整次修改，不会留下半次插入。
- `copy-range`：同一工程内给 `fromFrame`、`toFrame`、`atFrame`，可选 `trackIds` 与 `ripple`。
  复制所选轨道内片段和字幕，保留源区间、样式及关联关系；音画两端必须同时包含。组件和字幕样式创建独立副本，动画关键帧分配新身份。
  线性素材片段的部分区间通过 Core 修剪候选生成副本，源工程不被裁剪；字幕边界需完整。
  增益曲线按原片段的局部时间精确插值、截取并重定位，音频gain允许恰好位于副本终点的控制点，媒体区间仍为半开区间。
  若边界切入淡入/淡出或其他效果的局部关键帧无法等价保留，会明确拒绝；不近似重建效果。
  不支持的部分组件/变速映射和区间外转场依赖会明确失败。素材引用来自本工程，不在此入口自动跨工程导入。
- `external-ref`：`{op:"external-ref", id:"clip-a", value:"shot:opening"}` 设置通用稳定外部引用；单个 Sequence 内不能重名。
  引用用于连接上层镜头或脚本，不放路径、token、账号专用字段；复制时不沿用唯一引用。
- `commands`：仅在高层操作不足时提供既有强类型 `commands` 数组，可与其他操作放在同一计划中，共用预检、约束与撤销。

复杂速度映射、派生蒙版/脱敏与不兼容音画需要先确认支持范围；不要借此接口删除效果来换取成功。
换源同时检查音画双方的效果；已有增强音频、retime、蒙版、脱敏等源依赖处理时拒绝复用旧派生结果，需要通过相应处理入口明确重建。

### 明确约束

`constraints.duration` 固定所选 Sequence 的精确总时长；`unchangedIds` 指定必须保持的已有实体；
`allowedChangedIds` 限定全部可变 ID（包括新增、移除、时长变化涉及的 Sequence 等）。
先预检取得生成的 ID，再增加范围约束；添加约束不改变生成 ID，但正式请求必须使用新的 key，不能复用已提交 key。
约束在候选状态上检查；失败零写入。相同媒体指纹的比较归一化不会放宽这些严格的对象约束。
片段/字幕在轨道内的顺序也属于比较和约束；回执的fieldChanges提供JSON路径及前后值，大字段显示摘要并标记省略，需读取完整实体核验。

## 下一版本与差异

```text
oc project fork <source-id> --revision <revision> --title "Next cut" --idempotency-key <key> --json
oc project diff <source-id> --against <next-id> --json
oc project diff <id> --from-revision 7 --to-revision 8 --json
```

fork 不关闭或编辑源工程，新工程先保持关闭，不额外弹窗口。来源 revision/hash 和原始标题随新工程持久化；
精确重试返回同一个新工程。源 revision 不可恢复或源媒体缺失时失败，不发布残缺工程。
已有 `project duplicate` 的关闭源工程契约不变。

diff 可比较打开或关闭工程。输出变化对象、字段、源/文本/时段摘要和前后总时长；稳定 ID 用于定位。
唯一且相同的媒体指纹用于归一化导入 ID，项目相对文件位置不计作剪辑差异；普通文本不做全局字符串替换。
它是领域结构比较，不证明两部视频逐像素相同，也不自动合并版本。

## 一份核验报告

```text
oc project check --json
oc project check --layout --from-frame 300 --to-frame 600 --read-frames 300,450,599 --output <report.json> --json
oc project check --audio-clip <voice-clip-id> --json
```

默认检查领域结构、素材源边界、字幕词级对齐、所有composition的实际编译依赖和当前素材绑定。必需的媒体/字体/派生素材不可解析会失败；未使用的离线库素材单独列为需关注。
`--layout` 复用几何碰撞检查；`--read-frames` 生成真实合成抽帧（指定报告路径时 PNG 放旁边）；
`--audio-clip` 可重复，测量明确片段，不代表最终整片混音或人耳试听。

报告固定工程 ID 和起始 revision，结束时再次核对；中途工程变化或任一明确请求的步骤失败会返回非零退出码。
`finalExportVerified: false` 表示没有据此验证最终成片；不能把结构/编译通过当作整片验收。
有 `--output` 时失败也保留已得到的证据。布局和离线素材提醒见 `attentionRequired`。
`notPerformed` 明确列出未做的完整解码、整片混音响度或人工审看。抽帧生成成功不等于已经审看了画面。
