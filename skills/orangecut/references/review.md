# Review proposals and events

- Create: `oc proposal create --file <proposal.json> --json`, or pass exactly one JSON object with `--stdin`.
- List this Agent's active proposals: `oc proposal list --json`.
- Inspect: `oc proposal status <proposal-id> --json`.
- Cancel before apply: `oc proposal cancel <proposal-id> --json`.
- Watch the snapshot-first stream: `oc event watch --count <n> --timeout-seconds <seconds> --json`. The deadline is total; keepalives do not extend it. On reconnect, `--cursor <last-id>` is advisory; the next snapshot is authoritative. After a retryable failure with partial progress, use only `error.details.reconnectCursor`; `receivedEvents` counts complete envelopes received before failure. Request fewer events if the response exceeds its size limit. Never infer a cursor from event content.

Set a compact `idempotencyKey` in the proposal before creating it. If the response is uncertain, retry identical JSON. The same `proposalId` returns while active or after project or process restart, without another store generation or event. Reusing a key with changed content fails with `IDEMPOTENCY_CONFLICT`. `list` and `status` only write when they discover a real expiry or invalidation. Repeated `cancel` on a terminal proposal returns its existing state without new generations, events, or activity records, including after restart while its bounded TTL tombstone exists.

The Agent cannot accept, reject, or apply proposals. Ask the user to review ghost edits and decide in the desktop UI. Accepted edits apply in one semantic transaction; rejected edits never enter history.

## Inspect the current edit

`oc read` renders the current Sequence, including clips, captions, stickers, shapes, and HTML components, without exporting it.

- One frame by time: `oc read --at <seconds> --json`.
- Exact frames in requested order: `oc read --frames 0,90,480 --json`.
- Even samples over a range: `oc read --range 0:30 --count 9 --json`.
- Every Nth frame in a range: `oc read --range 0:30 --every 15 --json`.
- Edit boundaries: `oc read --at-edits --json`; narrow with `--range <start>:<end>`.

Each call returns one image path. Multi-frame reads make a contact sheet in requested order; cell i corresponds to `frames[i]`. The `layout` gives rows, columns, and cell size. `--detail thumbnail` (default) fits the sheet to a width budget for routine checks; `--detail full` keeps composited pixels at full size per cell. Use `--output <path>` to choose the output; otherwise it is temporary. Reads do not change the Project or history and may use proxies. They are edit evidence, not final export verification. A read allows at most 256 frames and rejects larger requests instead of silently truncating them.
