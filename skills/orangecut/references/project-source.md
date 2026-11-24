## 一眼看全工程,以及从文件重建一个

一条 `oc` 命令一条地读工程,做单次编辑够用,做整片判断则无望。
`oc project source --output <file>.oc.yaml` 把打开的工程写成一份
可读文档:画布、asset、按序的 track、每个 clip 以十进制秒记的
`at`/`duration`、每条 caption 的文本与 emphases,以及每个组件来自
哪个 preset。它是一个**刻意的子集**——引擎自己的结果(变换
矩阵、编译出的组件 DOM/CSS、关键帧曲线、探测结果)和每层带命名
空间的 `extensions`(联动画面/声音配对、track 来源、音效链接)
以 `@opaque:<digest>` 引用出现,其负载放在旁边写出的
`.opaque.json` sidecar 里。读 yaml 来推理;绝不手改 sidecar,也
绝不把 yaml 不带 sidecar 交出去——sidecar 才是重建工程时不变量
的保障(未配对的 A/V clip 会把画面从声音上拖走)。

`oc project create --from-source <file>.oc.yaml --media-root <dir>`
从这样的文件构建一个**全新**工程:`--media-root` 下的素材文件
经服务导入(新工程因此自含,asset id 重新分配),然后整个结构
作为一个 CommandBatch 落地。它只会创建新工程——绝不向已有工程
做调和,所以没有 diff、没有身份匹配、没有可丢的东西。标题来自
文件,除非 `--title` 另有指定。

两者合起来就是导出/导入对。验收测试拿重建的工程与**原始快照**
比,而不是与第二次导出比——比两次导出会在双方丢掉同一样东西时
照样通过,联动 A/V 扩展就是这样丢过一次的。在一条真实的 46 秒片
上实测:9 个 asset、59 个 clip、20 条 caption、36 个组件、45 个
extension 块,每个源区间完全一致(asset id 与内置 asset 池除外)。
用它们把整个剪辑交给别人、在 git 里存一份可 diff 的副本,或拿
一条片当模板做另一条。

版本分叉写入的 `dev.orangecut.lineage` v1 来源记录可以随公开源重建，由正式的
`project.lineage.set` Command 恢复；未知根扩展仍明确拒绝。只想复制当前开放版本时优先
`project fork`，只想比较两个版本时用 `project diff`，见[Agent 工程操作](agent-operations.md)。
