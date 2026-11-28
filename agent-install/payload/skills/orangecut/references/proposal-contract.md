# ProposedChangeSet Contract

Use a proposal when the user wants to review candidate edits before changing the project. Supply a UTF-8 JSON object:

```text
oc proposal create --file <proposal.json> --json
oc proposal create --stdin --json
```

Minimum example:

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

Replace example IDs with current project entities. Follow the [request contract](request-contract.md) for exact rationals, half-open ranges, command names, revision checks, atomic linked A/V edits, and idempotency.

- Each item is one atomic, independently reviewable choice. Keep linked video and audio changes in the same item and CommandBatch fragment.
- `dependencies` and `conflictsWith` reference `itemId` values within the same proposal.
- The service overrides `actor` with the authenticated agent identity.
- Creating, deciding, rejecting, canceling, expiring, or previewing a proposal does not advance the project revision.
- Only a human in the GUI can decide and apply. An agent can list, inspect, watch, and cancel its own proposals.
- Fail closed on `stale` or `expired`. Read a fresh snapshot before creating a new proposal.
