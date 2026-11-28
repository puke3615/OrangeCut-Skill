# Export routes and fast-lane eligibility

**Community:** Default to watermark-free CPU (`libx264`) exports at `<= 1080p`. **Pro:** Run `oc license status --json` before requesting NVENC, GPU encoding, or `> 1080p`. Do not force 4K or GPU encoding on Community, retry authorization errors, or work around the [license boundary](../SKILL.md) by changing the Project.

The service selects the route based on whether FFmpeg can faithfully reproduce the timeline. There is no request flag to select a route.

## Two routes

- **`layered`:** The fast lane. For a single video track with no overlays, FFmpeg trims and joins the source clips, then encodes the result without launching a browser.
- **`classic`:** The browser renders the canvas frame by frame, then the encoder writes the output. This covers the full timeline, at roughly 80 ms per frame on the tested 2019 Intel laptop.

Measured on that machine: nine clips placed end to end, 768 x 1376 at 24 fps, 1,435 frames (59.8s), `--preset publish --crf 26`:

| Route | Wall-clock time | SSIM against the original source |
|---|---|---|
| `layered` | **15.6s** | 0.9853 |
| `classic` | 132s | 0.9801 |

The fast lane skips a Chromium decode and screenshot pass. The outputs had matching frame counts, durations, canvas sizes, pixel formats, and BT.709 tags. Their audio bytes were identical because both used the same audio pipeline.

## Inspect the selected route

The export Job exposes its route from start to completion:

```bash
oc export start --output /abs/out.mp4 --preset publish --json
# → data.snapshot.route == "layered" | "classic"
#   data.snapshot.fallbackReason == "<why the fast lane declined>"  (classic only)
oc job watch <job-id> --json     # same two fields, all the way to terminal
```

If the export is unexpectedly slow, check `fallbackReason` first. It identifies the condition that ruled out the fast lane.

## Keep the timeline eligible

| Requirement | What breaks it | How to check or fix it |
|---|---|---|
| One continuous video track | A gap, even one frame | Use `oc timeline gap-remove` or use `oc timeline snapshot` to place the next Clip at the previous Clip's exact end frame. |
| No overlapping clips | Two video clips overlap on separate tracks | Keep one video track. `oc timeline add` opens another track if the target range is occupied, so read the snapshot afterward. |
| Full Sequence coverage | Video starts after frame 0 or ends before the Sequence ends | Start the first Clip at frame 0 and align the Sequence end with the track end. |
| Canvas-sized sources | A source needs scaling to fit the canvas | Create the Sequence with `oc project create --match <file>` or accept the classic route. |
| Matching frame rates | For example, 30 fps B-roll in a 24 fps Sequence | Normalize the outlier first (`ffmpeg -fps_mode cfr -r <rate> …`). |
| Frame-aligned cuts | A start or source offset falls between frames | Use `--at-frame` and `--start-frame`; do not calculate cut points in seconds by hand. |
| Unmodified source pixels | Retiming, reverse, freeze, transforms, scale, opacity, or filters | Use the classic route. |
| No extra visual layers | Captions, text stickers, shapes, or HTML components | See the overlay rules below. |

Trimmed clips remain eligible if their cut points fall on frame boundaries.

## Overlays and caching

Captions, stickers, shapes, and HTML components still need browser rendering. If the video track passes the same eligibility checks, the service compares the cost of rendering just the overlays against rendering the whole canvas. Browser startup can make layered export slower for short clips. Inspect `route` and `fallbackReason` on a comparable full Project before budgeting. `ORANGECUT_LAYERED_EXPORT=0/1` is an operations diagnostic and rollback switch, not a request flag.

Do not remove creative elements, split the Project, or premix audio to qualify. Complex picture-in-picture, mixed dimensions or frame rates, and sections filled with HTML can use `classic` without changing the edit.

On Windows, eligible full Publish exports automatically select calibrated NVENC and bounded parallelism. Confirm the actual encoder in the Job log. An MP4 at least 60 seconds long can reuse the full picture cache on a repeat export after a successful export in the same app version, provided the picture is unchanged. Loudness and volume-envelope changes that do not alter the picture still trigger an audio remix. Changes to captions, edits, sources, settings, or the app invalidate the picture cache conservatively. Check `ORANGECUT_PICTURE_CACHE` in the log for hits; this is not incremental rendering of arbitrary edited segments.

## Windows export reliability

- Full and range exports write frames to disk with streaming encode disabled. Do not enable streaming encode to troubleshoot crashes.
- CPU encoding, software browsers, low-memory mode, and jobs at least 1080 x 1920 and 30 seconds default to at most two workers. `ORANGECUT_RENDER_WORKERS=1..24` is an explicit process-environment override; it does not modify the Project.
- Recognized GPU, screenshot, evaluate, and EOF failures retry once after the original process tree exits, using one worker, CPU encoding, and a software browser with the same quality settings. Cancellation, source-structure errors, and deadline expiry do not retry. Fallback output is not stored in the GPU picture cache.
- `--output` accepts Chinese characters. Rendering and audio/video staging use a private ASCII-only temporary directory. The finished file is staged next to the destination for an atomic replacement. If system TEMP contains Chinese characters, OrangeCut tries a Windows-safe fallback; `ORANGECUT_RENDER_TEMP_ROOT` can specify an absolute, writable ASCII-only root. The workspace is cleaned up at completion or failure, and a failed export does not replace the previous file.

## Budgeting for bulk export

For 50 one-minute videos, the measurements above suggest roughly 15 minutes on the fast lane versus about two hours on `classic`. Check a representative Job's `fallbackReason` before optimizing the batch: one 30 fps clip in a 24 fps Sequence can send every export of it through the slower route.
