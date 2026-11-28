# Validate layout before export

Layout coordinates differ: caption `--x/--y` offset the `--position` anchor (portrait `bottom` is 76% down); sticker/shape `--x/--y` are pixels relative to the canvas center; presets may use canvas percentages. Do not copy offsets across systems.

`oc sticker add/update`, `oc shape add/update`, and `oc caption add/update/move/add-batch` return `data.layout` for the written element: `conflicts`, `safeZone`, `warningCount`, and `noticeCount`. Correct warnings now. If the checker fails, `data.layout.error` does not roll back the edit.

## Full or targeted checks

- Run `oc layout check --json` after moves and before **every** export, even for video and music only. Use `oc layout check --human` for a terminal summary. `oc layout list --json` lists estimated canvas-pixel bounds (`animated` identifies moving elements); use it to pick open space.
- `conflicts[].type`: `overlap` or `near`. `--near` defaults to 1.5% of the short side; `--near 0` disables proximity. `--min-overlap <ratio>` defaults to 0.12 of the smaller box. Text estimates can be 10–20% too narrow: inspect the reported `atFrame` with `oc read --at <frame converted to seconds>`.
- `--at-frame <frame>` inspects one frame; `--from-frame <a> --to-frame <b>` checks `[a, b)` in one request. Motion is sampled every half second, and `atFrame` is the worst sample. Muted tracks and disabled clips are excluded. Caption collisions are `warning`; intentional non-caption backplates can be `notice`.

## Transparent pixels and portrait captions

- `CAPTION_OVERLAP` reports `clipId`, `captionId`, half-open `frames`, `atFrame`, `overlapRect`, and fixes. For static PNG/WebP it uses tight `alpha > 16` bounds mapped through `visualFit`, translation, scale, and rotation. Transparent margins do not count. Decode once per asset per check; report only overlaps of at least 16 square pixels and 3 pixels in both axes.
- HTML checks statically locatable text/card regions, not full-frame transparent containers or background scrims. No remote fetch, transparent video, per-frame alpha inspection, or browser screenshot. Inspect `unverified` items, animated cases, and holes in an alpha box using `oc read --at`.
- Portrait `safeZone` reports intersections with feed UI: top ~11.5% of height, bottom ~20%, right ~15% of width; see e.g. `zones.bottom`. The default 76% caption position avoids those zones. `safeZone[].type == "PORTRAIT_CAPTION_SAFE_ZONE"` reserves 70–84% of height even when there are no captions. Time spans already reported as `CAPTION_OVERLAP` are not double-reported; adjacent non-conflicting spans may still receive a notice.

## Repair gaps, then inspect render

- Full checks report uncovered video over `[0, duration)` in `coverage`: `opening` (first frame black), `middle` (gap), or `tail` (picture ends early, possibly `audioDuringGap: true`). Cover frame zero and the tail, close middle gaps, or trim picture/audio/sequence consistently. Narrow post-write checks omit coverage. `EXPORT_VIDEO_LANE_GAP` from `oc export start` is the last warning, not a waiver.
- Move, shorten, or resize overlapping elements; check again. Use `oc read --at 0` to review the actual cover, including initial fades or initially transparent animations. Geometry is not playback review.
