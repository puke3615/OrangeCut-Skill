# 精密文字与通用画面编排

这些能力复用视觉操作，不绑定账号或某一期内容。临时流程图、设备状态卡等仍在作品内写 HTML，不自动加入产品预设。

## 通用视觉工具

Desktop：组件 → 局部放大窗 / 前后对照 / 桌面窗口 / 分层排版 / 描绘批注；添加后在检查器重开调整。
Agent：导入素材，再 `oc html visual <magnify|wipe|window|layers|markup> <config.json> --json`。
每项都是可编辑的 HTML 组件，经同一 Core 事务添加；支持 dry-run、base-revision、idempotency-key 与 undo/redo。

共同字段：`assetId`、`durationFrames`，可选 `startFrame`、`sourceStartFrame`（默认 0）、`color`（默认 #F28C28）。
帧数以序列帧率解释。图片源入点为 0，无 Probe 的图片需传 `sourceWidth/sourceHeight`。
视频静音，原声另放音轨。源完整等比显示，不将手机录屏拉宽。

```json
{"kind":"magnify","assetId":"<source>","durationFrames":150,"box":[300,400,500,160],"zoom":1.5,"xPercent":72,"yPercent":28}
```

`box` 为源像素 x,y,width,height；拖选要看的细节，副窗位置用画布百分比，范围越界会报错。
`wipe` 另给 `secondAssetId`、`secondStartFrame`，图片可给 `secondWidth/secondHeight`；
`wipeFrom/wipeTo` 默认 100/0，`wipeStartFrame/wipeEndFrame` 默认 15/75，须留在片段区间内。
`beforeLabel/afterLabel` 可编辑。请用同视角素材，不自动做图像配准。
`window` 可给 `title`、`widthPercent`（10–96）、`xPercent/yPercent`；保持源宽高比，背景透明。
`layers` 给 `alphaAssetId`、`alphaStartFrame`、必要时 `alphaWidth/alphaHeight`、精确 `alphaOffset`；
用现有 focus-cutout 制备对齐透明素材，检查轮廓后使用。`text`、`textX/textY`（源画面百分比）、`fontSize`（1–20，源画面宽百分比）控制被主体遮挡的文字。

```json
{"kind":"markup","assetId":"<source>","durationFrames":150,"showSource":true,"marks":[{"kind":"highlight","box":[300,420,600,64],"points":[],"color":"#F28C28","width":10,"startFrame":12,"drawFrames":20,"endFrame":150}]}
```

标记 kind：highlight/underline/circle/box/arrow/pen。box 是源像素区域；arrow/pen 还要至少两个源像素 `points:[[x,y],...]`。
每条有独立颜色、width 和本地 start/draw/end 帧，绘制后须保留至少一帧；最多 16 条标记，每路径最多 64 点。
荧光笔宽度由 box 高度决定；其他工具 width 是源像素笔宽。`showSource:false` 只放透明批注层。
批注固定在素材坐标，不自动跟随滚动、镜头或物体；页面变化应切段。通用分割和左裁仍受嵌套媒体限制。

## 文字贴纸

先 `oc sticker presets --json` 核对当前安装目录。新增 `cinema_clean`（极简标题）、`tech_label`（精密标识）、`editorial_note`（说明文字），默认常规字重、无描边。
`--enter` / `--exit` 可独立选择 `soft_rise`、`mask_reveal`、`focus`；`--letter-spacing` 使用画布像素，`--line-height-percent` 为 80–250，0 恢复自动行高。
新预设按帧率计算入退场长度；未手动指定时长时，短片段会按比例缩短动效并保留至少一帧静止画面。显式时长不自动改写，过短区间会报错。旧预设保持原帧数。
换预设默认保留原位置和动效；要采用新的动画应同时传相应参数或明确重置。

## 对象标注与录屏后期

Desktop 的「对象标注」可指定目标点、框、引线、文字位置。Agent 继续使用 `oc html add --preset hud-callout` / `hud-target`，不需为某种设备另造组件。
运动对象接 `oc timeline follow <overlay-clip> --target <video-clip> --box x,y,w,h --at-frame N` 生成可编辑关键帧；结果需抽帧复核，源镜头变速或改区间后需重新核对。

录屏输入是已经录好的视频：`oc html screen <absolute-recording-path> --at-frame 0 --json`。
Desktop「录屏聚焦」提供源入出点、框景、背景、裁切、手动聚焦和点击标记；CLI 参数以 `oc html screen --help` 为准。
焦点和点击由作者输入，不是自动识别；原片保持只读。选配原声为独立音轨，后续移动、修剪需分别调整。
新录屏与双画面片段允许整体移动、从右侧裁短；暂不支持通用切分或从左侧裁切，以免嵌入视频和聚焦动画重新起播。双画面可在窗口检查器改源入点；不同源区间的录屏需重新创建。

## 设备展示

`oc html device <config.json> --json` 把已导入录屏嵌入透明手机机身，保留其下的普通视频。
Desktop：组件 → 设备展示。示例：

```json
{"assetId":"<recording>","durationFrames":180,"startFrame":30,"sourceStartFrame":0,"color":"silver","pose":"front","cutout":"none","xPercent":20,"yPercent":50,"heightPercent":82,"shadow":60}
```

`color` 为 silver/black，`pose` 默认 front，left/right 为次级选项；位置与机身高度按画布百分比，阴影 0–100。
机身与屏幕使用固定 iPhone 14 Pro 比例；源录屏完整等比显示，比例不一致时留边，不会把手机压矮或拉宽。
开孔默认 none，island 会遮挡顶部内容，需人工检查。组件静音；原声可作为普通音轨独立放置。
源入点、展示时长以序列帧率解释，不能超出素材。整个设备为一个可编辑组件，可重新打开替换录屏或改外观。
`--dry-run`、`--base-revision` 与 `--idempotency-key` 同双画面；添加/更新通过 Core 事务并支持撤销。
已有点击聚焦的录屏包装保持在更多工具，此功能不生成点击提示。

## 目标聚焦

`oc html focus <config.json> --json` 将原画面、背景压暗和保留主体作为一个可编辑片段创建，整批可撤销；`--dry-run` 无写入。Desktop 入口为「目标聚焦」。默认不发光，主体保留原曝光。

```json
{"assetId":"<source>","mode":"region","shape":"rect","box":[300,200,400,250],"sourceWidth":1448,"sourceHeight":1086,"startFrame":150,"sourceStartFrame":0,"durationFrames":90,"enterFrames":12,"exitFrames":9,"dimPercent":65,"feather":8,"halo":0}
```

`box` 是原素材像素；源画面完整等比放入画布。视频从 `sourceStartFrame` 播放，帧数均按序列帧率。旧图片 Asset 无 Probe 时提供 `sourceWidth/sourceHeight`；不向 Asset 写伪造时长。区域可选 `rect/ellipse`。

对象使用 `mode:object` 和 `alphaAssetId`、`alphaStartFrame`；透明主体必须与原素材尺寸和内容对齐。透明 PNG 没有 Probe 时提供 `alphaWidth/alphaHeight`。主体和原片均静音，原声独立添加一次。

视频制备优先用 `--from-time numerator/denominator` 指定精确源秒数。将结果里的 Rational `alphaOffset` 原样放入 focus 配置，透明视频入点为 `alphaStartFrame / sequenceFps + alphaOffset`，防止不同帧率下错一帧。自动对象分割限恒定帧率单镜头；VFR 先规范帧率，或用区域聚焦，不能省略偏移后宣称同步。

制备轮廓：`oc media focus-cutout <source> --box x,y,w,h --output <new.png|new.webm> [--from-sec S --duration-sec D] --no-wait --json`。图片输出 PNG，视频输出 WebM；视频须给时长，只处理选定单镜头。需要现有 SAM 2.1 CUDA 插件。返回服务级 `jobId`，用 `oc media task watch/cancel` 观察、取消。此步骤不改 Project；检查 `framesWithoutObject` 和实际 alpha 边缘后，正常 `oc asset import` 再添加聚焦。不把空蒙版或跟踪失败宣称为成功。

新标注使用更粗主线、深色护边和稳定文字底板。已有 HTML 不自动改变；Desktop 标注表单重存或正常组件更新后采用新样式。手机缩小后仍须检查可见性。

## 双画面配置

先导入视频或图片，再执行 `oc html dual <config.json> --json`。示例：

```json
{
  "layout": "horizontal",
  "gapPx": 16,
  "splitPercent": 50,
  "panes": [
    {"assetId":"<已导入素材A>","sourceStartFrame":30,"startFrame":0,"durationFrames":90,"fit":"contain"},
    {"assetId":"<已导入素材B>","sourceStartFrame":60,"startFrame":15,"durationFrames":75,"fit":"cover","cropX":65,"cropY":50}
  ]
}
```

`horizontal` / `vertical` / `primary` 分别为左右、上下、主副，不推断叙事关系。
所有帧数以序列帧率解释；两个窗口独立选择源入点和时间线区间。`contain` 完整显示，`cover` 裁切填满，`cropX/cropY` 为 0–100 取景位置。图片源入点为 0。
每窗可用 `rect:{x,y,width,height}` 覆盖布局，单位为画布像素，须在画布内。
`audio:true` 将原声作为独立音轨同批添加，默认关闭；无原声的素材不能请求原声。
`--dry-run` 校验整个批次，不创建窗口。两个窗口同一事务添加和撤销，之后各自可编辑，不烘焙为视频。
