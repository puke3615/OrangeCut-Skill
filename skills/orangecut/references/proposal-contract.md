# ProposedChangeSet 契约

当用户想在任何 Project 变更之前先检视候选编辑时,用 proposal。写一个 UTF-8 JSON 对象,然后调用:

```text
oc proposal create --file <proposal.json> --json
oc proposal create --stdin --json
```

最小形态:

```json
{
  "commandId": "proposal-edit-001",
  "idempotencyKey": "proposal-edit-001",
  "projectId": "project-from-oc-project-current",
  "baseRevision": 7,
  "actor": { "type": "agent", "id": "orangecut-skill" },
  "intent": "Let the user review two candidate cuts.",
  "preconditions": [],
  "items": [
    {
      "itemId": "cut-intro",
      "kind": "timeline_cut",
      "summary": "Move the selected clip to exactly two seconds.",
      "commands": [
        {
          "type": "clip.move",
          "payload": {
            "sequenceId": "sequence-main",
            "clipId": "clip-1",
            "targetTrackId": "track-1",
            "timelineStart": { "num": "2", "den": "1" }
          }
        }
      ],
      "affectedEntities": [],
      "affectedRanges": [
        { "start": { "num": "0", "den": "1" }, "end": { "num": "2", "den": "1" } }
      ],
      "dependencies": [],
      "conflictsWith": []
    }
  ]
}
```

把示例 id 换成当前 Project 的实体。精确 Rational 值、半开区间、命令名、revision 校验、联动 A/V 原子性与幂等,遵循 [request-contract.md](request-contract.md)。

规则:

- 一个 item 是人可评审的最小原子选择。联动的画面/音频操作属于同一个 item、同一个 CommandBatch 片段。
- dependencies 与 conflicts 引用同一 proposal 内的 `itemId` 值。
- 服务端会用已认证的 Agent 身份覆盖线上传来的 actor。
- 创建、决定、拒绝、取消、过期或预览 proposal 都不推进 Project revision。
- 只有人工 GUI 能决定并应用。Agent 可以列出、检视、观察并取消自己的 proposal。
- `stale` 与 `expired` 一律 fail closed。读取新快照,再创建新的 proposal。
