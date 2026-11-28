# Export and job lifecycle

**[Community]** Default to watermark-free CPU (`libx264`) export at `<= 1080p` in either aspect ratio. **[Pro]** Check `oc license status --json` before specifying NVENC, GPU encoding, or `> 1080p`. Do not request 4K or force GPU on Community, probe access by retrying failures, or modify the project to bypass an output limit. See the [Skill tier rules](../SKILL.md).

- Start: `oc export start --output <absolute-path.mp4> [--sequence-id <id>] [--preset publish|compact|preview] [--idempotency-key <key>] --json`.
- Output-only overrides: `--fps` (an integer such as `30` or an exact ratio such as `30000/1001`, not a decimal), `--crf 0-63` (lower means higher quality and cost), and `--bitrate-kbps`. These do not edit the Sequence. Unsupported settings fail before a job starts. This build does not allow overriding output dimensions, codec, or container. Output uses `.mp4`; author a Sequence at the desired canvas size for a different resolution.
- Use the default encoding policy unless CPU is required (`--no-gpu`) or testing hardware encoding (`--gpu`). Check the job log for the actual backend. A request for GPU is not proof of GPU use.
- List the Agent's jobs with `oc job list --json`. `oc job watch <job-id> --json` waits for a terminal state by default; `--until-terminal` is accepted for compatibility and does nothing. Use `--no-wait` for a snapshot. The default `--timeout-seconds` is 300; on `JOB_WATCH_TIMEOUT`, keep watching rather than treating it as a failed export.
- Watch the job, not the output path. The file appears only on completion, and a crashed process can leave no file. Watch returns the error on `interrupted` or `failed`.
- Cancel with `oc job cancel <job-id> --json` and collect the terminal cleanup result. `oc job collect <job-id> --json` is idempotent. A successful export exposes `outputFileName`, not an absolute path.
- Retry only a terminal failure marked retryable: `oc job retry <job-id> --idempotency-key <key> --json`. If the response is uncertain, repeat the same source job/key pair; it resolves to the same replacement, even after restart. If a recently interrupted job has no recoverable RenderPlan, `JOB_RETRY_UNAVAILABLE` means you must start a new export from the current Project.

The service selects the export route. A contiguous video-only Sequence can use FFmpeg; other cases can fall back to browser frame rendering. In one 60 s comparison, the routes took 15.6 s and 132 s, respectively, at comparable fidelity. No flag selects a route. Check the job snapshot's `route: "layered"|"classic"` and read `fallbackReason` first when an export is unexpectedly slow. See [Export fast lanes](export-fast-lane.md).

Progress and terminal updates use the snapshot-first `oc event watch` stream. Treat the reconnect snapshot's `jobs` list as authoritative. Agent credentials can see and control only jobs that Agent created; the desktop user can see all jobs for the open Project.
