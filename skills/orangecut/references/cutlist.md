# Place trimmed clips from a cut list

`oc timeline place --cutlist <file>` places multiple precisely trimmed clips in one atomic edit. For each clip, specify its asset, source in-point, timeline start frame, and duration:

```json
[
  {"assetId": "asset-import-…", "atFrame": 0,   "durationFrames": 146,
   "sourceStartUs": 23000000},
  {"assetId": "asset-import-…", "atFrame": 372, "durationFrames": 348,
   "sourceStartUs": 30400000}
]
```

Choose the cuts using a transcript, media analysis, or your own review. The CLI places them deterministically; it does not choose the shots.

- `sourceStartUs` defaults to 0. An overrun of at most one frame is clamped with `PLACE_CLAMPED_TO_SOURCE`, since a VFR container duration and `ceil(duration×fps)` can disagree by one frame. A larger overrun fails with `PLACE_SOURCE_EXHAUSTED` and reports the maximum that fits. Same-track overlaps fail before commit with `PLACE_OVERLAP`.
- Unless `--track-id` is supplied, audio-only lists create an audio track, and picture-only lists create a video track below captions and stickers. Mixed lists fail explicitly. One CommandBatch places the whole list, and one undo removes the placement.
- `--muted` zeros the audio gain of each placed clip. Do not mute the video track to silence the footage: the compiler skips muted tracks altogether, including their picture.

Boundary example: `241/30` seconds of source, `sourceStartUs=5000000`, and `durationFrames=91` reach exactly the exclusive endpoint at frame 241. Do not shorten the clip to 90 frames. Import prefers exact stream ticks if they are within 1 ms of the container duration; placement does not use floating-point seconds. An older project that recorded `8.033333` rather than `241/30` can still warn using its original probe snapshot. Reimport to recover precise timing. Never edit project files directly or ignore `placedFrames`.
