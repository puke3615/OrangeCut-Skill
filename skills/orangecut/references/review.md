## Proposal 审阅与事件

- 创建:`oc proposal create --file <proposal.json> --json`,或用 `--stdin` 恰好管入一个 JSON 对象。
- 只列出本 Agent 的活跃 proposal:`oc proposal list --json`。
- 查看:`oc proposal status <proposal-id> --json`。
- 应用前取消:`oc proposal cancel <proposal-id> --json`。
- 观察规范的快照优先流:`oc event watch --count <n> --timeout-seconds <seconds> --json`。timeout 是总期限,不因 keepalive 延长。重连时 `--cursor <last-id>` 仅作建议性游标;永远把下一个快照当作规范。若可重试的流故障发生在部分进展之后,只复用 `error.details.reconnectCursor`;`receivedEvents` 报告故障前到达了多少个完整信封。累计响应体积超限失败时,请求更少的更新。绝不从事件内容推断游标。

在首次 create 之前,就为 proposal JSON 选好紧凑的 `idempotencyKey`。响应不确定后,用完全相同的 JSON 重试;活跃状态、Project 重开、进程重开三种情况下的重试都返回同一个 `proposalId`,不产生新的 Store 世代或 Event。key 复用但 proposal 内容有任何变化,以 `IDEMPOTENCY_CONFLICT` 失败。`list` 与 `status` 无副作用,除非它们发现了真实的过期/失效转变。对同一个已终态的 proposal 重复 `cancel`,返回同一状态,不产生新的世代、Event 或活动记录,包括 Project/进程重开后、有界 TTL 墓碑仍在的期间。

Agent 不能接受、拒绝或应用 proposal。请用户在 OrangeCut GUI 里审阅幽灵编辑与条目决定。应用被接受的条目是一次原子语义事务;被拒绝的条目绝不进入 Project 历史。


## 看见自己的成果

任何东西导出之前,你就能看编辑后的 Sequence。`oc read` 合成当前
时间线——clip、caption、贴纸、形状、HTML 组件,全部——并返回
一张图。

- 单帧:`oc read --at <seconds> --json`
- 若干精确帧,按你给的顺序:`oc read --frames 0,90,480 --json`
- 一段范围,均匀采样:`oc read --range 0:30 --count 9 --json`
- 一段范围,每 N 帧一张:`oc read --range 0:30 --every 15 --json`
- 编辑结构定义出的有意义瞬间:`oc read --at-edits --json`,可用
  `--range <start>:<end>` 收窄

每次 read 恰好返回一个图片路径,绝不是一目录静帧:范围 read 被
平铺成一张 contact sheet,格子按阅读顺序排列,格子 `i` 对应同一
响应里的 `frames[i]`。响应还带 `layout`(列数、行数、格子尺寸),
所以你不用量图就能点名某个格子。

同一张网格有两档保真:

- `--detail thumbnail`(默认)把整张 sheet 塞进一个宽度预算。够
  便宜,可当作检查一段区域发生了什么的常规手段。
- `--detail full` 每格保留合成本身的像素。等第一遍 read 已经告诉
  你哪个瞬间值得细看时再用。

用 `--output <path>` 把 sheet 写到想要的位置;不传则落在一个临时
文件,路径在响应里。read 绝不改动 Project,绝不进历史。它读的是
预览保真——可能画在代理素材上,所以把它当作关于剪辑的证据,而
不是关于发布文件的证明。

一次 read 至多解析 256 帧。要得更多会带着你要的数字失败,而不是
悄悄返回一个前缀——那会被你读成完整覆盖。
