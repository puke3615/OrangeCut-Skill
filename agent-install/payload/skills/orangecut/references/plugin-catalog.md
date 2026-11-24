## 可选能力插件(OCP)

## 统一 Skill 的分级路由

调用前先按 [Skill 版本感知规则](../SKILL.md) 执行 `oc license status --json`。`oc plugin ls` 只报告安装状态，不等于 Pro 资格。社区版不要盲装、盲调进阶插件；用户明确需要时说明「设置 → 授权管理」激活后即可使用同一套 Skill，不以 `PRO_REQUIRED` 重试探测授权。

| 授权 | registry 插件（共 21 个） | 使用边界 |
|---|---|---|
| [社区版免费] | `asr`、`fonts` | 内置离线中文 Paraformer 与开源字体；可直接用于字幕和剪辑 |
| [Pro] | `matting`、`segment`、`inpaint`、`vocal-sep`、`denoise`、`interp`、`upscale`、`tts`、`shots`、`faces`、`ocr`、`diarize`、`clip`、`clap`、`vl`、`douyin`、`fetch`、`product`、`gen-image` | 其余全部 19 个进阶 OCP 插件；安装、执行和缓存命中均受 Rust Pro 闸口约束 |

插件分级同样适用于封装它们的语义命令。`fetch` / `douyin` / `product` 涉及联网，`gen-image` 需要用户自己的上游配置与额度；不能把 Pro 描述为免费云服务。**[社区版免费]** 工程读写、预览、CLI 编排和 `<= 1080p` CPU 无水印导出不需要这些插件；**[Pro]** NVENC / GPU 编码和 `> 1080p` 导出另见[导出与任务](jobs.md)。


**契约先行**:凡本文档中打了 `【插件:xxx】` 标的能力,都**不随安装包**,按需装到本机。默认姿势是**懒调用**——直接调对应命令;若未安装,会得到结构化错误 `PLUGIN_NOT_INSTALLED`,其 `remediation` 就是安装命令(`oc plugin add xxx`),照做后重试即可。要预检就先 `oc plugin ls [name] --json`:它列出**全部**插件目录(不只是已装的),每项带一句话描述、类型(`local` 本地推理 / `tool` 工具资产 / `cloud` 云服务)、安装状态、本机是否支持、磁盘账。升级=再 `add`(幂等:断点续传/坏了补齐/有新版即升),卸载=`oc plugin rm <name>`。`oc capabilities` 里也有一行插件摘要。`ls` 行里 `status` 四值:`ready`/`not_installed`/`broken`(装过但自检失败,再 `add` 补齐)/`dev_override`;`installDir` 是装好后的绝对目录——工具资产型插件(字体这类)就靠它找文件。**平台账要先算**:跨平台的是 `asr`/`fonts` 两个资产包,以及 `gen-image` 两个**云插件**(纯 HTTPS 调用,注册表按平台各钉一份内嵌解释器,Mac 上直接 `add` 就能用,不必绕去 Windows 推图拉片);**其余全部只支持 Windows**(含 shots/ocr/diarize 这些 CPU 就能跑的——运行时是按 Windows 锁的),Mac 上 `ls` 会报 `supported: false` 并附 `unsupportedReason`,那时如实说要去 Windows 机器跑,别去试 `add`。模型型插件多需 NVIDIA GPU(哪项需要以 `ls` 的 `supported` 为准);安装动辄几百 MB 到几 GB,慢是正常的。**运行也慢得合理**:整部电影跑 `shots`/`speakers` 是几十分钟量级,CLI 对这两条已经等到 90 分钟(其他命令 15–30 分钟),不要再包一层自己的超时,也不要看它没回就当挂了;要拆就按素材拆,不要按时间切。GPU 插件(vl/tts/matting/inpaint/vocal-sep)与导出渲染抢同一块显存,**分时使用**,别并行。云端型(`cloud`)插件相反:安装秒级,但**先配密钥**——`oc plugin config <name> --set KEY=VALUE`(存本机、升级/`rm` 都保留,值绝不回显;`--unset KEY` 清除);没配时调用报 `PLUGIN_NEEDS_CONFIG`,`ls` 行里 `requiredSecrets`/`configured` 如实标注。凡打 `【插件:xxx·云·计费】` 标的能力,**每次调用都按量花钱**——批量跑之前把条数和大约成本先对用户报一声。

**同一个问题只答一次**:确定性的插件调用(`shots`/`diarize`/`faces`/`ocr`/`segment`/`matting`/`inpaint`/`upscale`/`interp`/`denoise`/`vocal-sep`)会把答案按机器存下来,再问同一条就秒回,结果里多一个 `cached: true`(和 `cachedFromSeconds`,原来那次跑了多久)。**换会话不失效**——整部电影的 `shots` 跑过一次就不必再跑第二次。"同一条"认的是**内容**不是路径:素材改名、换目录都还是同一条;素材本身改了一个字节、参数变了、或者升级 oc 换了调用逻辑,都自动变成新的一条。产出文件的落点**不参与**认定,命中时按这次要的路径复制一份给你。**生成型的一律不缓存**——`gen-image`/`tts` 再问一次就是要一张新的,`fetch`/`product` 抓的是会变的线上内容。要看存了多少:`oc plugin cache --json`(条数、磁盘、按插件分账);**要强制重跑就 `oc plugin cache [name] --clear --json`**——这是唯一从 CLI 生效的开关。`OCP_NO_CACHE=1` 也能整体关掉,但它读的是**服务进程**的环境,在你自己的 shell 里设没用,除非服务是你带着这个变量起的。实测(180 帧样片):冷跑 9.2 秒,命中 0.15 秒;改一个字节的素材、改一个参数都会如实变成未命中。

插件能力的语义命令(都走服务,产物与错误面同其他命令一致):

- [Pro] 【插件:shots】`oc media shots <file> [--threshold] [--min-scene-frames] --json`:TransNetV2 镜头切分,出 `scenes/cuts`;长素材拆解与对标分析的第一步,CPU 秒级。
- [Pro] 【插件:faces】`oc media people <file> [--every-n-frames] [--similarity] [--max-frames] --json`:人脸检测+身份聚类,出 person-N 出场时间线;电影解说"找主角所有镜头"的检索底座。
- [Pro] 【插件:clip】`oc media search-index <file> --index <x.npz>` 先建帧向量索引,再 `oc media search "<中文描述>" --index <x.npz> [--top-k]` 秒查候选镜头;粗筛交给它,精看交给 vl。
- [Pro] 【插件:vl】`oc media describe --prompt "<问题>" --video <file> --frame <n> | --image <img> --json`:Qwen2.5-VL 看一帧答一题(内容/质量/构图/有没有人脸)。显存 ~8GB,与渲染分时使用。
- [Pro] 【插件:ocr】`oc media ocr --image <img> | --video <file> --frame <n> --json`:PP-OCR 读出画面里的文字(字幕/字卡/水印),对标拆解的文案抓取主力;CPU 秒级。
- [Pro] 【插件:upscale】`oc media upscale <file> --output <out> [--scale 2|3|4] [--model photo|anime] [--still] --json`:Real-ESRGAN 超分救活低清素材;photo 固定 x4,anime 系列可选倍数,GPU 快速。
- [Pro] 【插件:interp】`oc media interp <file> --output <out.mp4> [--factor 2|4] --json`:RIFE 光流插帧出丝滑慢动作。变速曲线本身能用,但它没有帧插值,慢放到 30% 以下靠重复帧、看得出顿挫;要真正丝滑的慢动作先用这条把素材补到高帧率,再放慢。
- [Pro] 【插件:vocal-sep】`oc audio separate <file> --output-dir <dir> [--mode two|four] --json`:Demucs 人声/伴奏(或四轨)分离;压台词保环境音、从对标视频扒 BGM 都靠它。
- [Pro] 【插件:diarize】`oc audio speakers <file> [--num-speakers N] [--threshold] --json`:说话人分离出 speaker_N 时间线——电影解说的角色台词归属,配合 people 可拼"画面上谁在开口";CPU 即可。
- [Pro] 【插件:denoise】`oc audio denoise <in> --output <out> --json`:DeepFilterNet 清理口播底噪/嘶声/房间混响,CPU 实时级;真人录音进剪辑链前先过一遍。
- [Pro] 【插件:douyin】`oc media douyin-works <作品/作者主页分享链接|抖音号|sec_uid> [--limit 20] [--cursor <nextCursor>] --json`:作品链接先从该作品详情解析作者;也可直接查询公开作者并列作品,返回 `creator`(含 `profileUrl`)、`videos[]`、`nextCursor`、`hasMore` 与 `partial`;每条作品带 `awemeId`、`description`、`createTime`、`durationMs`、`coverUrl`、公开互动数和可继续交给下载器的 `shareUrl`。要下一页就把上次的 `nextCursor` 原样传回 `--cursor`;单次最多 200 条。它只负责**发现素材**,不下载、不做点赞/私信/关注;会话由程序自动续期并加密保存;要文件就把选中的 `shareUrl` 交给下条 `oc media fetch`。插件用系统 Chrome/Edge 访问公开页,可复用已授权的受保护会话,同机查询强制串行以降低验证/限流概率;直接给抖音号要多走一次站内公开搜索,若搜索触发验证,改贴作者主页分享链接可绕过搜索。遇 `DOUYIN_VERIFICATION_REQUIRED` 或 `DOUYIN_RATE_LIMITED` 就按错误提示等待,不要开并行重试风暴。
- [Pro] 【插件:fetch】`oc media fetch <url> [--output <file>] [--cookies <jar>] [--audio-only] [--format <表达式>] [--url-only] --json`:yt-dlp 按 URL 下载源片/对标片/BGM(社区维护的千站解析,含抖音)。默认挑**无水印 muxed h264**(下游 import/render 都更吃 h264;代价是站点的 h264 阶梯可能低于 h265 一档,要最高清晰度就显式给 `--format`);**选中的格式没有音轨而源站明明提供音频时,删产物直接失败**(`FETCH_SILENT_PICK`——"看起来正常的无声文件比失败更糟",实测抖音 DASH 分轨就长这样),真无声的源照常通过、结果带 `hasAudio:false`。**抖音不用给 cookie,短链 `v.douyin.com/...` 直接给**:插件自己起一个无头系统 Chrome/Edge 匿名打开一次页面(约 10 秒),把页面自己带签名请求到的 detail 应答截下来,从中挑混流 h264、最大画幅的一档,yt-dlp 只当下载器(结果带 `cookies: "warmed-up"`、`extractor: "DouyinPageDetail"`、`formatId` 是抖音的 gear 名,如 `normal_1080_0`);不要自己去裸跑 yt-dlp——它调抖音接口过不了签名,报 `Fresh cookies are needed` 是死路,手工导出的 jar 几小时也就过期。给了 `--format` 就回到 yt-dlp 自己的提取器(表达式只有它认得),抖音上目前大概率失败;传了 `--cookies` 而它已过期时也会自动换成新鲜 cookie 重试一次。其他登录墙站点报 `FETCH_NEEDS_COOKIES`,把登录过的浏览器导出的 Netscape jar 传给 `--cookies`。升级 yt-dlp = registry 换一行钉的 url+sha256 + 再 `add`。
- [Pro] 【插件:product】`oc media product <url> --output-dir <目录> [--cookies <jar>] [--max-images N] --json`:把一个**公开商品页**(先支持抖店 haohuo H5)快照成「商品包」——`images/`(主图+详情图原图)、`product.json`(标题/店铺/结构化参数表/图片清单)、`raw-api.json`(接口原始响应留证)。**只出事实不出判断**:哪个卖点上画面是调用方的事(带货视频场景的输入端,见垂直场景);匿名 headless Chrome/Edge 驱动,**不管理任何登录态**——遇登录墙报 `PRODUCT_NEEDS_COOKIES` 收 Netscape jar(同 fetch 的姿势);H5 端拿不到的价格如实报 `priceAvailable: false`,不要去猜。页面改版时结构化核心(参数/详情图)走的是页面自己的 XHR JSON,比 DOM 稳;认不出时报 `PRODUCT_PAGE_UNRECOGNIZED` 并落一份 page-snapshot.html 供排查。实测一件商品 5 主图+20 详情图+20 项参数约 10 秒。
- [Pro] 【插件:clap】`oc audio index <素材目录> --index <x.npz>` 一次索引整座音效/BGM 库,再 `oc audio find "<英文描述>" --index <x.npz> [--top-k]` 毫秒级搜声音——**查询词用英文**(中文意图先自行翻译);本机的手工分目录音乐库从此可语义检索。
- [Pro] 【插件:tts】`oc tts say "<文本>" --ref <voice.wav> --output <out.wav> [--lang zh] [--duration-factor] --json`:IndexTTS-2.5 克隆参考音色合成配音;首跑会额外下载辅助模型(需网络)。
- [Pro] 【插件:gen-image】`oc media genimage "<prompt>" --output <out.png> [--model <model-id>] [--size 1024x1024] [--image <reference>...] --json`: OpenAI Images compatible generation (`images/generations`) and reference editing (`images/edits`, multipart). Configure `oc plugin config gen-image --set IMAGE_API_BASE_URL=<api-base> --set IMAGE_API_KEY=<key>` in the private local configuration, optionally `IMAGE_API_MODEL`. Models and accepted sizes depend on the provider; charges go to that provider. Never echo configured keys.
- [Pro] 【插件:inpaint】**没有语义命令,走逃生口**:`oc plugin run inpaint --request <req.json> --timeout 5400`,请求是 `{"video": "<绝对路径>", "outputPath": "<out.mp4>", "box": [x, y, w, h]}`(固定矩形,像素坐标,用 `oc media ocr` 的文字框或 `oc read` 抽帧量出来)**或** `"maskVideo": "<掩膜视频>"`(白=要抹掉的区域,随时间移动的水印/贴脸字幕用它;`oc media segment` 的输出正好是这个形状),二选一,同给或都不给都拒。ProPainter 光流修补:抹水印、台标、别人烧死的字幕,结果 `outputPath`/`seconds`。显存 ~8GB、逐帧慢,**只喂需要的那一段**(先 split/trim 或 ffmpeg 裁出区间再送),整部电影别整片送;**输出不带音轨**,回到时间线时用原片的声音。盒上实测 box 模式 72 帧出片。
- [Pro] 【插件:segment】`oc media segment <file> --output <mask.mp4> (--box x,y,w,h | --point x,y [--point neg:x,y ...]) [--frame N] [--alpha <out.webm>] [--mask-png <out.png>] --json`:SAM 2.1 可提示分割+全片跟踪——在提示帧上用一个框或几个点指定**任意目标**(道具/动物/衣服/移动水印,不限于人),掩膜自动传播到整段(提示帧可以不是第 0 帧,双向传播)。主产物白底黑字掩膜视频,正好是 `inpaint` 的 `maskVideo` 形状(抹移动水印:segment 圈住 → inpaint 抹掉);`--alpha` 顺手合成 VP9 透明抠像(转场情绪视频的道具层,压在时间线上层用);`--mask-png` 存提示帧掩膜(matting 链的首帧掩膜形状)。GPU ~6GB,量级同 matting(约 0.2-0.5 秒/帧);默认拒收超过 3000 帧的素材——先裁出需要的区间再送。目标全片只认第一个提示对象,多个目标分多次跑;`framesWithoutObject` 大于 0 说明有些帧目标丢了(出画/被完全遮挡),用前抽查那些段。**跨镜头剪切不保证目标身份**——硬切后它会咬住新镜头里长得像的东西继续跟(实测跨切镜后干净地跟上了另一个人物),所以先 `media shots` 切镜、按单镜头段送。
- [社区版免费] 【插件:asr】`oc plugin add asr`——`oc media transcribe` 的模型包(见上文转写条目),跨平台。
- [社区版免费] 【插件:fonts】`oc plugin add fonts`——内置两款盖不到的字面:LXGW 文楷三字重(Regular/Light/Medium,开源楷体,给 editorial/抒情/古风语域),以及**内置 Regular 与 Black 之间缺的那几档字重**(思源/Noto 黑体 Light/Medium/Bold、宋体 Bold)。内置只有最轻和最重两档,中间没有——标题和字幕真正想要的是 Bold 那一档,这个插件补的就是它。跨平台,约 250MB。装完 `oc plugin ls fonts --json` 读 `installDir`,文件在 `<installDir>/fonts/` 下,再 `oc asset import <文件> --kind font` 注册进 Project 才能当 `--font-asset-id` 用——插件只落文件,不自动进任何工程。
- 逃生口:`oc plugin run <name> --request <req.json> [--timeout 秒]`——语义命令没覆盖的新能力,按各插件 entry 的请求格式直接调(默认等 30 分钟,长任务自己给 `--timeout`)。

**按任务找插件**(装之前先想清楚这一步在链上的位置,别为了一个 2 秒片段装 13GB):

- 素材**进场清洗**:字幕轨(`media subtitles`,零插件)→ 硬字幕/水印 `ocr` 定位 → `inpaint` 抹除(位置会动的先 `segment` 跟踪出掩膜);真人录音先 `denoise`;低清源 `upscale`。
- 素材**理解与检索**:`shots` 骨架 → `people`(谁在画面里)/ `speakers`(谁在说话)→ 「把镜头聚成叙事场景」配方;按描述找镜头 `search-index`/`search` 粗筛 + `describe` 精看;拿画面文字 `ocr`。
- **生产内容**:配音 `tts`(先合成一句给用户听音色,认可了再批量);封面/字卡 `genimage`;B-roll/video assets are prepared independently and imported;从对标片扒 BGM / 压台词留环境音 `separate`;找音效 `index`/`find`。
- **后处理**:慢动作 `interp`;文字被人遮挡 `matte --quality high`。
