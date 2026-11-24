# 原始 CommandBatch 契约

仅当没有专门的 `oc` 子命令能表达所需的语义编辑时,才用本参考。

写一个 UTF-8 JSON 对象,内含一份规范的、与 OrangeCut 兼容的 `CommandBatch`,然后调用:

```text
oc command apply --file <request.json> --json
oc command apply --file <request.json> --dry-run --json
```

CLI 把 Batch 发给已认证的本地 HTTP 服务。服务会用已认证的 Agent 身份覆盖线上送来的 actor,校验 project/revision/preconditions,再把 Batch 送进与 GUI 相同的 Host Gateway。CLI 从不直接写 Project 存储。

最小形态:

```json
{
  "commandId": "agent-edit-001",
  "idempotencyKey": "agent-edit-001",
  "projectId": "project-from-oc-project-current",
  "baseRevision": 7,
  "actor": { "type": "agent", "id": "orangecut-skill" },
  "intent": "Move the selected clip to exactly five seconds.",
  "preconditions": [],
  "mode": "commit",
  "commands": [
    {
      "type": "clip.move",
      "payload": {
        "sequenceId": "sequence-main",
        "clipId": "clip-1",
        "targetTrackId": "track-1",
        "timelineStart": { "num": "5", "den": "1" }
      }
    }
  ]
}
```

规则:

- 组 Batch 之前,先即时读取当前 Project 与 revision。
- 解读一个 Sequence 的 Track 时按唯一的数字 `Track.order`,永远不要按数组位置。
- 一个用户可见的意图,放进一个原子 Batch。
- Rational 值是已约分的字符串对,如 `{ "num": "1001", "den": "30000" }`。
- 时间范围是半开区间 `{ "start": Rational, "end": Rational }`。
- 只用 `oc capabilities --json` 暴露的语义命令名。
- 对内嵌 A/V,通过 `dev.orangecut.linked-av` 找到确切的配对方,并在同一个 Batch 里同时改两个角色。
- 幂等键只在对同一逻辑请求做完全一致的重试时复用。
- dry-run 不为之后的过期提交授权。应用前重新核对 revision。

成功与失败都是稳定的信封结构:

```json
{ "schemaVersion": "1", "ok": true, "data": {} }
```

```json
{
  "schemaVersion": "1",
  "ok": false,
  "error": {
    "code": "REVISION_CONFLICT",
    "stage": "preconditions",
    "message": "...",
    "details": {},
    "retryable": true,
    "currentRevision": 8,
    "remediation": "..."
  }
}
```

`error.stage` 只会是 `decode`、`schema`、`preconditions`、`capability`、`command`、
`validation`、`transaction`、`store`、`serialization`、`job`、`migration` 之一。出现任何
其他取值都按协议序列化失败处理;不要据此推断新的重试策略。

永远不要暴露或探查隐藏的 HTTP 端点、凭据、descriptor、Store 路径、缓存路径或渲染器对象。
