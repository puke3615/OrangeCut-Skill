# CommandBatch Request Contract

Use this fallback only when no dedicated `oc` subcommand can express the requested edit. Supply a canonical OrangeCut `CommandBatch` as a UTF-8 JSON object:

```text
oc command apply --file <request.json> --json
oc command apply --file <request.json> --dry-run --json
```

The authenticated local service overrides `actor` with the authenticated agent identity, checks project, revision, and preconditions, then submits the batch through the same Host Gateway as the GUI. The CLI never writes project storage directly.

Minimum example:

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

- Read the current project and revision immediately before constructing a batch.
- Interpret sequence tracks by their unique numeric `Track.order`, never by array position.
- Put one user-visible intent in one atomic batch.
- Use reduced rational string pairs, e.g. `{ "num": "1001", "den": "30000" }`.
- Use half-open time ranges: `{ "start": Rational, "end": Rational }`.
- Use only semantic command names exposed by `oc capabilities --json`.
- Find the exact embedded A/V pair via `dev.orangecut.linked-av` and edit both roles in the same batch.
- Reuse an idempotency key only for an identical retry of the same logical request.
- A dry run does not authorize a stale commit. Recheck the revision before applying.

Stable success and failure envelopes:

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

Valid `error.stage` values: `decode`, `schema`, `preconditions`, `capability`, `command`, `validation`, `transaction`, `store`, `serialization`, `job`, `migration`. Treat any other value as a protocol serialization failure; do not infer a new retry strategy.

Never probe or expose hidden HTTP endpoints, credentials, descriptors, store or cache paths, or renderer objects.
