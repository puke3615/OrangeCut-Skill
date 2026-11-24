# HTML Component:编写内置组件表达不了的 DOM

OrangeCut 通过 HyperFrames 渲染,合成在 Chromium 里完成。当文字、贴纸、
形状和字幕都不够用时——信息卡、表格、内联 SVG 图示、图表类排版、CSS
动画浮层——`dev.orangecut.html` Component 就是把你自己的 DOM 放上
时间线的方式。

三条入口,按投入从低到高排列:

- `oc html presets --json`,再 `oc html add --preset <id> --set <slot>=<value>`
  ——与编辑器组件库里同一套现成组件。从这里开始。
- `oc html add <fragment.html> --at-frame <frame> --duration-frames <frames>` ——
  你自己的标记写成文件,解析为下文的类型化子树。
- 通过 `oc command apply` 提交一个普通的 `component.add` + `clip.add` 批次,
  用于这次放置需要并入更大的原子编辑或一份 proposal 的场合。

## 跨画布的尺寸

要在画布切换后仍然成立的 preset,会在自己的根节点上声明
`container-type: size`,内部一切尺寸都用容器查询单位:字号用 `cqmin`,
留白用 `cqw`。`cqmin` 让字号在 1080x1920 与 1920x1080 下完全一致,在 4K
下翻倍——这是固定 `px` 做不到、`vw`/`vh` 会做错的事:编辑器把预览画在
一个缩放过的面板里,视口单位会与导出结果不一致。

容器单位只能出现在声明了 `container-type` 的元素的**后代**上。Component
的根节点就是 Clip 自己的节点,写在根上的单位会按视口而不是 Clip 盒子
解析。把内容包进一层内部元素,尺寸定在那一层。

也不要在根元素上做 `transform` 或 `opacity` 动画:这两项属于 Clip 本身,
Component 若对它们做动画,会覆盖而不是叠加 Clip 的运动。动画放在内部
元素上。

## 数据形态

```json
{
  "id": "component-quote-card",
  "componentType": "dev.orangecut.html",
  "capabilityRequirements": ["dev.orangecut.component.html"],
  "properties": {
    "root": { "tag": "div", "classes": ["card"], "children": [] },
    "stylesheet": "@keyframes rise{from{transform:translateY(40px);opacity:0}to{transform:none;opacity:1}}.card{animation:rise .6s ease-out both;animation-delay:calc(var(--oc-clip-start, 0s) + 0s)}"
  }
}
```

`root` 是一棵**类型化节点子树**,不是标记字符串。每个节点接受:

| 字段 | 含义 |
|---|---|
| `tag` | 元素名,取自下文的允许列表 |
| `namespace` | `html`(默认)或 `svg` |
| `text` | 文本内容 |
| `classes` | 类名,用来挂接样式表 |
| `attributes` | 普通属性,如 `viewBox`、`role`、`aria-*` |
| `styles` | 内联 CSS 声明,以映射形式给出 |
| `assetId` | 支撑 `img` / `video` / `audio` / `source` / `use` 的 Project Asset |
| `children` | 嵌套子节点 |

Clip 自己的元素会成为这棵子树的根,所以时间、轨道与变换照常来自 Clip。
根节点用 `width` / `height` 的 `100%` 定尺寸,布局在其内部展开。

## 动画

用**限定作用域的 CSS** 做动画,包括 `@keyframes`。HyperFrames 对 CSS
动画做逐帧精确 seek,关键帧动画每次渲染的结果完全一致。作用域用你写进
`classes` 的类名来限定;样式表会加到整个合成上,前缀要取得有辨识度。

这件事不需要——也不能用——JavaScript。

**非零起点必须补偿动画时钟**：CSS 动画使用合成的全局时间，不会因为 Clip
在 `atFrame` 才显示就重新开始。编译器在片段根节点注入 `--oc-clip-start`
（秒），内部动画的 `animation-delay` 必须写成
`calc(var(--oc-clip-start, 0s) + <局部延迟>)`，不要只写 `0s` 或局部延迟。
例如片段放在 30fps 的第 150 帧、希望出场后 0.2 秒入场：

```css
.quote-body {
  animation: quote-rise .8s ease-out both;
  animation-delay: calc(var(--oc-clip-start, 0s) + .2s);
}
```

这里实际延迟为 5.2 秒；若漏掉 Clip 起点，0.8 秒动画在片段显示前已经播完。
`animation-delay` 写在 `animation` 简写之后，避免被简写重置。起点为零也沿用
同一写法。本文示例的所有动画都遵循此规则。

## 引用媒体

永远不要写 `src`。把 Project Asset 的 ID 放进 `assetId`;编译器会经授权
注册表解析它,并在渲染时重新校验指纹。裸 URL 根本取不到:合成运行在
`default-src 'none'; connect-src 'none'` 之下。

```json
{ "tag": "img", "assetId": "asset-logo", "styles": { "width": "120px" } }
```

## 什么会被拒,为什么

下列内容会让批次以结构化错误失败,而不是渲染出与你要求不同的东西:

| 被拒项 | 原因 |
|---|---|
| `script`、`iframe`、`object`、`embed`、`form`、`a`、`canvas`、`template` | 能执行、导航或嵌入外来文档 |
| `on*` 属性 | 事件处理器只是换了个写法的脚本 |
| `id`、`class`、`style`、`src`、`data-start`、`data-hf-*`、`data-oc-*` | 归编译器所有;改用专用字段 |
| CSS 里的 `url(...)`、`@import` | 会触达授权 Asset 注册表之外 |
| 内联样式值里的 `;` | 会终止当前声明并另起一条 |
| `javascript:`、`vbscript:`、`data:text/html` 值 | 可执行载荷 |
| 没有 `assetId` 的 `img` / `video` / `audio` | 将不得不凭空发明一个来源 |

边界:512 个节点、32 层深、单个文本节点 64 KiB、样式表 128 KiB。

## 允许的标签

结构与文本:`div span p section article header footer main aside nav
h1..h6 ul ol li dl dt dd blockquote figure figcaption hr br pre code em strong
b i u s small sub sup mark time abbr table thead tbody tfoot tr th td caption
colgroup col ruby rt rp bdi bdo wbr`

Project 媒体:`img video audio picture source`

内联矢量:`svg g path rect circle ellipse line polyline polygon text tspan
defs linearGradient radialGradient stop clipPath mask filter feGaussianBlur
feOffset feBlend feColorMatrix feComposite feMerge feMergeNode use symbol marker
pattern foreignObject`

## 完整示例

```bash
cat <<'JSON' | oc command apply --stdin
{
  "commandId": "add-quote-card",
  "projectId": "<from `oc project current --json`>",
  "baseRevision": <current revision>,
  "intent": "Add an animated quote card over the intro.",
  "commands": [
    {
      "type": "component.add",
      "payload": {
        "component": {
          "id": "component-quote-card",
          "componentType": "dev.orangecut.html",
          "capabilityRequirements": ["dev.orangecut.component.html"],
          "properties": {
            "root": {
              "tag": "div",
              "classes": ["quote-card"],
              "styles": { "width": "100%", "height": "100%", "display": "flex",
                          "align-items": "center", "justify-content": "center" },
              "children": [
                { "tag": "blockquote", "classes": ["quote-body"],
                  "text": "先把风险讲清楚，再谈收益。",
                  "styles": { "color": "#f5f5f7", "font-size": "72px",
                              "max-width": "80%", "text-align": "center" } }
              ]
            },
            "stylesheet": "@keyframes quote-rise{from{transform:translateY(48px);opacity:0}to{transform:none;opacity:1}}.quote-card{background:linear-gradient(160deg,#101014,#1d1d24)}.quote-body{animation:quote-rise .8s cubic-bezier(.2,.8,.2,1) both;animation-delay:calc(var(--oc-clip-start, 0s) + 0s)}"
          }
        }
      }
    },
    {
      "type": "clip.add",
      "payload": {
        "sequenceId": "sequence-main",
        "trackId": "track-component",
        "clip": {
          "id": "clip-quote-card",
          "enabled": true,
          "timelineRange": { "start": {"num":"0","den":"1"}, "end": {"num":"3","den":"1"} },
          "source": { "type": "component", "componentId": "component-quote-card" },
          "playback": { "rate": {"num":"1","den":"1"}, "reverse": false, "freeze": false },
          "effects": [],
          "extensions": {}
        }
      }
    }
  ]
}
JSON
```

组批次之前,先从 `oc capabilities --json` 读取准确的命令类型名与 payload
形态;不要从本页复制 revision 号或 ID。

## 应用前先审阅

本页的一切同样可以走 `oc proposal create`——在用户没有要求改动立即落地
时,这是更安全的默认。Desktop 时间线随后会把这张卡显示为待定项,用户
可以预览后接受或拒绝。
