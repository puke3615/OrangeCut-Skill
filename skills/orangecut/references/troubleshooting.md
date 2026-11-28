# Troubleshooting and obsolete workarounds

Use the current commands rather than carrying forward these workarounds from before September 9, 2026.

| Issue or old workaround | Current behavior |
|---|---|
| `timeline speed` failed; freeze frames needed read, import, and placement | Use `speed --rate-percent/--freeze/--reverse`. Use `timeline freeze-frame` for an inserted hold. |
| Retry `PLACE_SOURCE_EXHAUSTED` with one frame less | Placement clamps an overrun of up to one frame and returns `PLACE_CLAMPED_TO_SOURCE`. |
| Run `track move --to-top` after creating a video track | Place/add creates video tracks below text tracks. |
| Trim crossing music or stickers before inserting a gap | Use `gap-insert --split-crossing`. |
| Hand-author four rational transforms for a grid | Use `timeline grid`; adjust one pane with `clip transform set` (partial update). |
| Recompress a compact export with FFmpeg for mobile review | Use `export start --preset preview`. |
| Delete orphan style components manually after removing imported SRT cues | Style components are cleaned up with their cues; remaining orphans generate warnings. |
| Restore tokens and emphases after `caption update --text` | Matching ranges are retained. Check `droppedTokens`/`droppedEmphases`; pass corrected `tokens` through the command contract when needed. |
| Reposition a sticker after `sticker update --preset` | Preset changes retain placement unless `--reset-placement` is explicit. |
| Find token misalignment only after rendering | Both shortcut and raw command reject `CAPTION_TOKENS_MISALIGNED`. |
| Poll `job watch` manually | It waits for a terminal state by default. `--no-wait` returns a snapshot; `--until-terminal` remains accepted for compatibility. |
| Place audio with `timeline add` to avoid incompatible tracks | An audio-only cut list creates an audio track. |
| One missing display glyph makes read fail | Built-in Noto supplies missing glyphs with a service warning. Read fails only when both fonts lack the glyph. |
| Treat `SERVICE_ENDPOINT_UNKNOWN` as the explanation for every 404 | An enveloped 404 reports the actual error, often `PROJECT_NOT_OPEN`. |
| Download, split, and place a reaction clip manually | `oc cutaway add <id> --at-frame N` offers 14 built-ins. It inserts into the main picture track by default; overlay and PiP are alternatives. |

`tokens` on caption update and `resetPlacement` on sticker update are optional additions. Positional text on caption/sticker add and the raw `caption.update` shape are unchanged.

## Handle command and service failures

- Choose fonts from `oc asset list --kind font --json` and pass the ID as `--font-asset-id` on caption add, add-batch, import-srt, or sticker add. The built-in sans family has Regular and Black, not intermediate weights. `caption add` defaults to `--font-weight` of `bold`, so without a real Bold face the browser can synthesize it from Regular. Install genuine intermediate sans weights, a serif Bold, or Kai-style fonts with `oc plugin add fonts`. `oc plugin ls fonts --json` reports `installDir`; files are under `installDir/fonts/`. Register other `.ttf/.otf/.ttc/.otc` faces with `oc asset import <font-file> --kind font` and pass the returned `assetId` (e.g. for Windows `%WINDIR%\Fonts\simsun.ttc`). Trust the installed build's asset list rather than assuming every display face is bundled.
- Retain `code`, `stage`, `message`, `retryable`, `currentRevision`, and `remediation` when reporting failures. On `REVISION_CONFLICT`, reread state and rebuild the intended edit. Never silently rebase.
- `REQUEST_TIMEOUT` means the client deadline elapsed (30 s by default, overridable with `OC_TIMEOUT_SECONDS`); the edit may have committed. The CLI automatically replays requests with an idempotency key. `error.details` carries `idempotencyKey`/`baseRevision` for an exact retry. For slow batches, raise the timeout instead of looping.
- After an uncertain transport result, retry only identical requests with their original supported identity: base revision and key for project writes, the full JSON and key for proposal creation, proposal ID for cancel, and source job plus key for `job retry`. Never change parameters under the same key.
- For `PROPOSAL_STALE` or `PROPOSAL_EXPIRED`, reread the timeline and create a new proposal. Do not silently reuse or renew the old one. On `LIVE_SESSION_AMBIGUOUS`, stop; do not select a window by title, recency, PID, or file order.
- For `EVENT_STREAM_CLOSED`, `EVENT_STREAM_TIMEOUT`, or another retryable stream error, pass `details.reconnectCursor` unchanged to `event watch`. The next snapshot replaces local state. If there is no cursor, reconnect without one.
- With `HTTP_RESPONSE_TOO_LARGE` or `EVENT_STREAM_ENVELOPE_TOO_LARGE`, do not keep or infer partial snapshots. Report the bounded interface's limitation; do not inspect private storage as a fallback.
- On `JOB_WATCH_TIMEOUT`, retain the opaque job ID to keep watching or explicitly cancel. Do not assume success or failure. On `CLI_REQUEST_FILE_TOO_LARGE` or `CLI_REQUEST_STDIN_TOO_LARGE`, split the work into smaller user-visible atomic edits or proposals; do not truncate JSON or split a linked A/V pair.
- On `LOW_DISK`, free space and start a new export. On `WORKER_INTERRUPTED`, collect terminal diagnostics and start over from the current Project state.
- `PROCESS_STARTUP_FAILED` (`MEDIA_PROCESS_STARTUP_FAILED` for derived media) means the OS rejected the subprocess during startup. It did not read the media. It reports `retryable: false`; do not change the cut or assets and retry. Restart the OrangeCut service; it can stand down after three failures in ten minutes so the host or `oc` can restart it. If failure persists, report an environment issue. For authorized diagnostics, `ORANGECUT_STANDDOWN=off` leaves the process available for handle, GDI, and memory inspection. Compare successful subprocess counts across restarts to investigate a leak.
- A rejected batch must leave the revision and project hash unchanged. Unsupported capabilities must fail explicitly.
- Record a workaround with `oc feedback "<what happened,your workaround>" [--repro <minimal reproduction>]`. It appends only to local `feedback.md` under the data root; it does not call the service. Record meaningful workarounds or retry loops while the evidence is available.
