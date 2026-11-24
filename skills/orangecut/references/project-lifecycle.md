## open 与 close 之外的 Project 生命周期

- `oc project rename <project-id> --title <title> --json` 给项目改标题。
- `oc project duplicate <project-id> --title <title> --json` 复制一个**已关闭**
  的项目，复制完整当前内容和媒体，起一个新标题；新工程从独立 revision 0 开始，不复制源工程的历史——想拿一条片当模板又不动原件时,
  这是老实的做法。
- `oc project trash <project-id> --json` 把一个**已关闭**的项目移入操作系统
  废纸篓。用户可以从废纸篓恢复它,这也是 OrangeCut 执行的唯一删除方式——
  绝不自己删项目目录。

三者都按 id 作用于某个项目，而不是隐式的当前工程；trash/duplicate 要求目标工程关闭，其他工程可以继续打开。
需要保留源窗口时用 [project fork](agent-operations.md)。实验会留下项目(单是一次往返
测试,每跑一次就留一个),`oc project list --json` 加 `trash`
就是你收拾自己摊子的方式。


## Project 生命周期

- 列出 Project:`oc project list --json`
- 创建(自动画布,跟随第一个 clip):`oc project create --title "..." --json`;显式格式:加 `--width 1080 --height 1920 --fps 30`
- 打开:`oc project open <project-id> --json`
- 关闭:`oc project close --json`(多开时带 `--project <id>`;不带且恰好一个开着就关那一个)

import 绝不自动把 Asset 加上时间线。import 之后,读返回的 `assetId`,再调用 `oc timeline add`。在 split、move、trim、remove 或定点放置之前,用 `oc timeline snapshot --json` 拿精确的 Clip 与 Track id。当请求的移动要换 Track、闭合空隙、ripple 后续 Clip,或组合更大范围的编辑时,用原始 CommandBatch;稳定捷径绝不推断这些策略。

CLI 自己发现应用私有的回环服务与凭据,必要时还会自己拉起服务。常规请求中不要提供 endpoint、端口、token、仓库路径或数据根目录;也不要自己去 spawn 服务进程——并发的多条 `oc` 由一把锁收敛成一次拉起,手工绕过它就会起出一堆立刻自杀的进程。

API 探索用 `oc docs --json` 打开离线 Swagger UI,附带短时效的同源交互会话。headless 或远程 shell 工作流用 `oc docs --url --json`,只打印只读文档 URL,不开浏览器也不创建会话。两种形式都不打印进程 token 或一次性会话票据。
