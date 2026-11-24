## 标记结构:章节、节拍、审阅笔记

marker 是 sequence 上的一个具名点——剪辑师定下"第二幕从这里
开始"时落下的那个东西。它们承载长片需要的结构,而在此之前,
词汇表里没有任何东西能写下一个 marker,于是带标记的工程只能读,
不能重建。

- `oc marker list --json`——每个 marker 的 id、标签、帧和秒。
- `oc marker add "第一章" --at-frame <frame> --json`——在精确帧上
  落一个 marker;需要稳定 id 时用 `--marker-id` 钉住,否则自动
  生成一个。
- `oc marker update <marker-id> [--label <text>] [--at-frame <frame>] --json`——
  移动它、重命名它,或两者都做;两个都不传会被拒绝,而不是提交成
  一个空操作。
- `oc marker remove <marker-id> --json`。

marker 落在 sequence 上而非某条 track 上,且必须落在其内——落在
sequence 时长处或之后的 marker 会被拒绝,因为半开区间不包含自己
的终点。用它们在放章节卡之前规划章节:先把节拍定成 marker,读
回来,再放一个 `chapters` 列表与之相符的 `chapter-bar`。
