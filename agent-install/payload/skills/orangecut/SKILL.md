---
name: orangecut
description: Edit OrangeCut projects with the installed oc CLI. Use for media import, timeline and caption edits, proposals, previews, export, and standalone media analysis or download.
---

# OrangeCut Edit

Choose the edits yourself; OrangeCut executes, validates, previews, and exports them. Load only the references needed for the task.

## Check entitlement before Pro operations

Use this single Skill for both editions. Community includes project editing, live preview, CLI/Agent control, offline Chinese `asr` (Paraformer), open-source `fonts`, and watermark-free CPU (`libx264`) export up to `max(w,h) <= 1920 && min(w,h) <= 1080`. Pro adds all 19 advanced [OCP plugins](references/plugin-catalog.md) except the always-free `asr` and `fonts`, GPU/NVENC encoding, and export above 1080p.

1. Before installing or invoking a Pro plugin (including semantic commands, `plugin run`, and cached results), using GPU encoding, or exporting above 1080p, run `oc license status --json` and read `data.tier` and `data.capabilities`. Use `oc --no-autostart license status --json` to inspect an existing service only. This is a read-only local Rust check, not activation, lease refresh, or an edit. Recheck after activation, unlinking, or a service change. Installation and `oc capabilities` do not prove entitlement.
2. On Community, default to CPU export up to 1080p. Prefer export overrides to changing the project canvas. Do not install or invoke Pro features speculatively. If the request requires Pro, explain the limit and offer a Community path without silently downgrading the deliverable. Activate under Settings → License; no Skill reinstall is needed.
3. On Pro, still verify plugin installation, hardware, runtime requirements, and any upstream charges. If the check fails, the tier is unknown, or the CLI is too old, stop only the Pro operation. On `PRO_REQUIRED`, retain the error, recheck the tier, and point to activation; do not retry the Pro operation or bypass the gate.

Example `data`: `{"tier":"community","capabilities":{"advancedOcpPlugins":false,"gpuEncoding":false,"exportAbove1080p":false,"cpuExportUpTo1080p":true}}`.

The official site is the source for prices, support, and downloads. Do not guess or cache them: pricing `https://orangecut.timor419.com/pricing?lang=en` (Chinese: `https://orangecut.timor419.com/pricing`), support `https://orangecut.timor419.com/pricing#contact`, downloads `https://orangecut.timor419.com/desktop`.

## Find the project, inspect, edit, verify

1. Run `oc status --json` and inspect `openProjects`. With multiple projects, pass `--project <id>` or set `ORANGECUT_PROJECT`; verify the response's top-level `projectId`. Never guess or open a second writer. `oc` can start a headless service when none is active; use `--no-autostart` for an existence check. See [recovery](references/troubleshooting.md) for distinct service, project, and ambiguity errors.
2. Use `oc project current --json`, then `oc timeline inspect --id <id> --json`, `--text <text>`, or `--from-frame N --to-frame M` for local scope; use `oc timeline snapshot` for full topology. `inspect` omits effects, animation, and dependencies by default. Use `--full` and read dependent assets, fonts, and components before replacing entities; never reconstruct one from a summary. Read [operation boundaries](references/agent-operations.md) before compound edits. If preflight rejects a path, preserve the edit rather than deleting effects.
3. Read `oc <group> --help`, `oc <group> <action> --help`, and `oc capabilities --command <name> --json` before building a raw batch (e.g. `timeline.edit`, `clip.add`). Apply clearly authorized edits directly; use a proposal for review-first requests. Verify the returned revision and actual state; preview where needed. Exit code alone is not proof.
4. For standalone jobs, no project is needed: `oc media task list`, `oc media task watch <jobId>`, `oc media task cancel <jobId>`, and `oc audio enhance-presets --json`.

## Invariants and recovery

- Use the installed CLI. Do not inspect or modify private project files, SQLite, descriptors, credentials, caches, or renderer state; no Python, Cargo, repo scripts, or GUI automation as bypasses.
- Commands use reduced Rational strings and half-open `[start,end)` ranges. Track display order comes from `order`. Edit linked audio/video atomically; use `clip.linked-av.detach` only on explicit request.
- Fix `baseRevision` and `idempotencyKey` before a recoverable write. Pass `--base-revision` and `--idempotency-key` where supported. For unknown outcomes, resubmit the exact request with the same identity, including creation template/key or job/proposal identity. On `REVISION_CONFLICT`, reread and replan; never silently rebase. See [request contract](references/request-contract.md).
- Use undo/redo for requested history changes, not to clear a timeline (`timeline clear`). Prefer one transaction per intent. Agents can create, read, and cancel their own proposals; only a human can accept, reject, and apply them in the GUI. See [proposal contract](references/proposal-contract.md).

## Find the right reference

| Task | Reference / entry point |
|---|---|
| Inspect, compound edits, fork, diff, check | [Agent operations](references/agent-operations.md): `timeline inspect/edit`, `project fork/diff/check`, `capabilities --command timeline.edit` |
| Create, open, rename, duplicate, trash | [Project lifecycle](references/project-lifecycle.md): `oc project create/open/duplicate`; close source before duplication |
| Import, add, split, move, trim, retime, keyframe, caption, mix | [Editing](references/editing.md): `oc asset import`, `oc timeline add/split/move/trim` |
| Place selected source ranges | [Cut lists](references/cutlist.md): `oc timeline place --cutlist <file>` |
| Export or import project source | [Project source](references/project-source.md): `oc project source`; keep source and `.opaque.json` paired and do not edit the sidecar |
| Compose overlays, visual tools, presenter PiP | [Composition](references/visual-composition.md), [overlay catalog](references/overlay-catalog.md), [HTML](references/html-component.md) |
| Talking-head hooks, pacing, visual choreography | [Talking-head](references/scenarios/talking-head.md): 5s hooks, subject sandwich, mid-section rhythm |
| Mark chapters, beats, review points | [Markers](references/markers.md): `oc marker` |
| Check overlay collisions, caption safe zones, black gaps | [Layout](references/layout-check.md): `oc layout check` before export and after moves |
| Preview, proposals, events | [Review](references/review.md): `oc read --at`, `--frames`, `--range` (range preview: up to 256 frames) |
| Grade and LUT | [Grading](references/color-grading.md): `oc canvas grade` replaces the entire grade; read it first |
| Export, test segment, cancel, collect | [Jobs](references/jobs.md): `oc export start`, `oc job watch`; [export routing](references/export-fast-lane.md) for fast-lane eligibility |
| Record or pick up narration | [Recording](references/recording.md): user starts recording; Agent handles existing media |
| Enhance voice independently | [Voice enhancement](references/audio-enhance.md): `oc audio enhance` requires no project |
| Install, configure, run other plugins | [Plugin catalog](references/plugin-catalog.md): `oc plugin ls`, command-specific help |
| Recover, diagnose, handle fonts | [Troubleshooting](references/troubleshooting.md): retain `code`, `stage`, `retryable`, `currentRevision`, and `remediation` |

## High-impact rules

- **Still images:** Never pre-render a pan/zoom with FFmpeg `zoompan`. Import the high-resolution original and animate subpixel `scale` / `position` using `oc keyframe upsert`. Integer crop steps cause jitter that magnifiers exaggerate.
- **CinemaKit:** Discover by style and use case with `oc html presets --pack cinema --category data --json`; inspect only the selected ID. Hand-authored HTML remains fully available through `oc html add <fragment.html>` under the same native safety contract.
- **Presenter:** `oc html presenter` builds editable picture-in-picture. Real position changes default to `wind-swoosh` one frame early; see the [composition guide](references/visual-composition.md#presenter-picture-in-picture) for timing and the four cinematic micro-SFX options.
- **Caption collisions:** `oc layout check` uses alpha-aware image bounds for `CAPTION_OVERLAP`, ignores transparent margins, and checks the lower portrait caption reservation even without captions. Read warnings and verify the frame; geometric checks are not playback review.
- User direction > account profile > scene conventions > general defaults. Keep account-specific paths and style rules outside this Skill. Anchor narrated edits to the voice track. Inspect burned-in captions before adding another layer. No unrelated decoration on a local edit. Use [visual consistency](references/visual-consistency.md) only for cross-shot subject continuity.
- `project check` is structural verification, not a decode test, final mix, or human review. Inspect `notPerformed`, `attentionRequired`, and `finalExportVerified` before reporting acceptance.
