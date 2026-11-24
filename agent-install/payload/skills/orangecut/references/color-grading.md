## 调色顾问:让 Agent 给风格建议

传统剪辑软件给 200 个滤镜让人自己挑;这里由你先看片、再给 2–3 个**有理由的**候选,用户点头再套。三步:

1. **先量**:对主素材(或成片)跑 `oc media colorstats`,拿 `verdicts`。多段素材差异大时各量一次,按主体段落为准。
2. **按题材选候选,用测量修正**(风格 id 见 `oc canvas looks --json`,`--look <id>` 一条命令套上,`--intensity` 覆盖建议强度):

   | 题材 / 形态 | 首选 | 备选 | 建议强度 | 别用 |
   |---|---|---|---|---|
   | 人物氛围感、旅拍、穿搭 | `japanese-airy` 日系清透 | `teal-orange` 青橙电影 | 60–80 | `morandi`(肤色多时发灰)、强风格化 |
   | 口播、知识、访谈 | `clean-studio` 净白影棚 | `soft-boost` 柔和提升、`skin-soft` 柔肤 | 100(本就克制) | 一切强风格化;观众要的是"看不出调过" |
   | 探店、美食、种草、开箱 | `food-pop` 美食增艳 | `bright-pop` 明快 | 80–100 | 黑白、漂白 |
   | 夜景、室内昏暗、夜话 | `night-lift` 夜景提亮 | 叠 `cool-morning` 冷调清晨 | 100 | `deep-contrast`(把暗部压没) |
   | 回忆、年代感、家庭影像 | `vintage-wash` 复古水洗 | `warm-vintage` 暖调复古、`home-movie-8mm` | 80–100 | 冷调 |
   | 悬疑、剧情反转、开场压迫 | `deep-contrast` 深邃对比 | `mono-clean` 纯净黑白(只压回忆段) | 80–100 | 明快、美食 |
   | 家居、静物、高级感带货 | `morandi` 高级灰 | `muted-editorial` 杂志灰 | 100 | 增艳类 |
   | 电影解说 | 不调,跟原片走 | 非要调只用 `teal-orange` | ≤ 50 | 任何会盖过原片语言的风格 |
   | 综艺快剪、梗图、字卡密集 | `bright-pop` 明快 | `vhs-playback`、`editorial-halftone` 只做转场段 | 80 | 全片强风格化 |

   用测量修正:`lighting: dark|dim` → 先 `night-lift`,再叠题材风格;`temperature: cool` 且题材要温暖 → `warm-daylight` 或把冷调候选降强度;`saturation: vivid` → 增艳类降到 60 或换 `soft-boost`;`skin: prominent` → 避开 `morandi`/`bleach-bypass`,降低任何会偏绿偏灰的候选强度;`contrast: punchy` → 不再叠 `deep-contrast`。
3. **给用户看再套**:把候选连同一句理由("素材偏暗偏冷、肤色占三成,推荐夜景提亮 + 日系清透,不推荐漂白")报出来,用户选定后 `oc canvas grade --look <id>`。这是发布前的最后一步:先把拼接、剧情、字幕、组件全部做完,再上风格。

铁律:
- **一条片子一种风格**;分段换风格必须有叙事理由(回忆段黑白、幻想段偏暖),换段要有转场遮盖。
- 风格只调视频/图片素材,**字幕、贴纸、HTML 组件不受影响**——所以放心套,它们不会跟着变灰变黄;真要整片压色,导出后把 MP4 再导回来当素材套一遍。
- 建议强度低于目录默认值时说明为什么;口播类默认"几乎看不出来"才对。
- 用户自带 `.cube`(达芬奇/剪映导出的)用 `--lut <绝对路径>`;它假定输入是普通 Rec.709 画面,log 转 709 那种技术型 LUT 不要往普通素材上套。
- 预览与导出同一套着色器,不必导出验证;要看效果给用户截实时预览即可。
