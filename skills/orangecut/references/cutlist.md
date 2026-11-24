## 按剪单放置修剪好的片段

`oc timeline place --cutlist <file>` 在一个原子步骤里放置多个
精确修剪的片段。剪单是一份朴素的编辑决策清单——哪个 asset、
从源片何处起、落到哪个时间线帧、放多长:

```json
[
  {"assetId": "asset-import-…", "atFrame": 0,   "durationFrames": 146,
   "sourceStartUs": 23000000},
  {"assetId": "asset-import-…", "atFrame": 372, "durationFrames": 348,
   "sourceStartUs": 30400000}
]
```

**剪单里放什么由 Agent 决定**——不管你用什么证据选出这些时刻
(一份转写、一个理解引擎、你自己的眼睛),把选择翻译成这个
格式是你自己的事;命令只做确定性的放置。`sourceStartUs` 默认
为 0。读过探测到的源片末尾**一帧以内**会自动收边并给一条
`PLACE_CLAMPED_TO_SOURCE` 警告(VFR 素材的容器时长和帧率不自洽,
`ceil(duration×fps)` 常差 1 帧),超出一帧以上才拒绝并附上放得下
的最大值(`PLACE_SOURCE_EXHAUSTED`);同轨重叠在提交前就被拒绝
(`PLACE_OVERLAP`)。除非 `--track-id` 另有指定,片段落在一条
新轨上——**剪单全是音频就建音频轨**(BGM/配音可以直接 place),
全是画面就建视频轨且**插在字幕/贴纸轨之下**(不盖字幕),混着
两类则明确报错;一切在一个 CommandBatch 里——一步 undo 撤掉整次
放置。`--muted` 把每个放置片段的音频增益归零,用于被解说盖住
的素材。**绝不为了静音去 mute 视频轨**:引擎在编译期整轨跳过
muted 轨的节点,画面会跟声音一起消失——clip 级增益是让必须
保持可见的素材闭嘴的唯一办法。

边界例：源长 `241/30` 秒、`sourceStartUs=5000000`、`durationFrames=91`
恰好取到第 241 帧的半开区间终点，不应减成 90 帧。导入会优先采用与容器
时长相差不超过 1ms 的精确 stream ticks；不会用浮点秒计算剪单。旧工程若已
保存 `8.033333` 秒而非 `241/30`，仍保留原探测快照且可能返回收边警告，
需要重新导入素材取得精确时长；不要直接篡改工程文件或忽略 `placedFrames`。
