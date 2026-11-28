# Text and visual composition tools

These are reusable controls, not account- or episode-specific presets. Create one-off flowcharts, device status cards, and other bespoke visuals for the Project rather than adding them to the preset catalog.

## Visual tools

In Desktop, use the Component tools for magnify, wipe, window, layers, or markup. From an Agent, import the source first, then run `oc html visual <magnify|wipe|window|layers|markup> <config.json> --json`. Each tool creates an editable HTML component via Core and supports dry runs, revision guards, idempotency, and undo/redo.

Common fields: `assetId`, `durationFrames`, optional `startFrame`, `sourceStartFrame` (default 0), and `color` (default `#F28C28`). Frames use the Sequence frame rate. For stills, use source frame 0 and provide `sourceWidth/sourceHeight` if probe dimensions are unavailable. Components are silent; keep original audio on its own track. The source keeps its aspect ratio.

```json
{"kind":"magnify","assetId":"<source>","durationFrames":150,"box":[300,400,500,160],"zoom":1.5,"xPercent":72,"yPercent":28}
```

- `box` uses source-pixel `x, y, width, height`. Choose the detail in source coordinates and place the window in canvas percentages. Out-of-bounds ranges fail.
- `wipe` uses `secondAssetId`, `secondStartFrame`, and `secondWidth/secondHeight` if needed for a still. `wipeFrom/wipeTo` default to 100/0; `wipeStartFrame/wipeEndFrame` default to 15/75 and must be within the clip. `beforeLabel/afterLabel` are editable. Match the camera angle yourself; the tool does not register the images.
- `window` supports `title`, `widthPercent` (10–96), and `xPercent/yPercent`. It preserves aspect ratio and uses a transparent background.
- `layers` uses `alphaAssetId`, `alphaStartFrame`, plus `alphaWidth/alphaHeight` or `alphaOffset` when needed. Align the transparent cutout and inspect its edges. `text`, `textX/textY` (source-relative percentages), and `fontSize` (1–20% of source width) control text behind the subject.

```json
{"kind":"markup","assetId":"<source>","durationFrames":150,"showSource":true,"marks":[{"kind":"highlight","box":[300,420,600,64],"points":[],"color":"#F28C28","width":10,"startFrame":12,"drawFrames":20,"endFrame":150}]}
```

`kind` can be `highlight`, `underline`, `circle`, `box`, `arrow`, or `pen`. `box` is in source pixels; arrows and pen strokes need at least two source-pixel points (`points:[[x,y],...]`). Each mark has its own color, width, and clip-local start, draw, and end times. Keep it visible after its draw animation. Use up to 16 marks and up to 64 points per path. Highlight thickness follows the box height; other stroke widths use source pixels. Set `showSource:false` for transparent markup only.

Marks stay fixed in source coordinates: they do not track scrolling, camera motion, or objects. Make separate clips when the page changes. Embedded media still limits splitting and left trims.

## Text stickers

Run `oc sticker presets --json` to inspect installed presets. `cinema_clean` suits short titles, `tech_label` suits precise labels, and `editorial_note` suits explanatory text. They default to regular weight without a background plate. Select `--enter` and `--exit` independently (`soft_rise`, `mask_reveal`, or `focus`). `--letter-spacing` uses pixels; `--line-height-percent` accepts 80–250, or 0 for automatic line height.

New presets compute entrance and exit durations from the frame rate. If timing is automatic and the clip is short, the animations shrink proportionally, leaving at least one static frame. Explicit durations are not silently rewritten; they fail if too long. Legacy presets keep their original frame counts. Resetting style preserves placement and motion unless you explicitly change or reset the animation too.

## Object labels and screen recordings

In Desktop, Object Marker sets the target point, box, leader, and label position. For Agent edits, use `oc html add --preset hud-callout` or `hud-target` instead of building a separate component for each device. For a moving object, `oc timeline follow <overlay-clip> --target <video-clip> --box x,y,w,h --at-frame N` creates editable keyframes. Review the tracking frame by frame after retiming or realigning the source clip.

For an existing screen recording, run `oc html screen <absolute-recording-path> --at-frame 0 --json`. The Desktop tool exposes source in-point, frame, background, crop, manual focus, and click markers. See `oc html screen --help` for parameters. Supply the focus and click locations; they are not detected automatically. Source media remains read-only. Original audio can go on an independent track and needs its own move and trim edits.

Screen and dual-view components support moving and right trimming. They do not support splitting or left trimming, which could restart the embedded video or focus animation. Change source in-points in the dual-view inspector; recreate a screen component for a different source section.

## Device mockups

`oc html device <config.json> --json` places an imported recording inside an editable, transparent phone mockup. In Desktop, choose Device Display from the Component tools. Example:

```json
{"assetId":"<recording>","durationFrames":180,"startFrame":30,"sourceStartFrame":0,"color":"silver","pose":"front","cutout":"none","xPercent":20,"yPercent":50,"heightPercent":82,"shadow":60}
```

`color` is `silver` or `black`; `pose` defaults to `front` and can also be `left` or `right`. Position and body height are canvas percentages. Shadow strength is 0–100. The body and screen use the iPhone 14 Pro proportions. Recordings with a different ratio fit without stretching. `cutout` defaults to `none`; check that `island` does not obscure important content. The mockup is silent; add source audio separately if needed.

Source in-point and duration use the Sequence frame rate and must fit the media. Reopen the component to replace the recording or restyle it. `--dry-run`, `--base-revision`, and `--idempotency-key` use the same Core contract; additions and updates are undoable. Use the screen-recording tools when you need focus or click indicators.

## Target focus

For a visible contour, `oc media matte <source> --output <clip.webm> --outline-width 6 --outline-color '#FFFFFF' --json` adds a soft outline beneath the source alpha. Width is in output pixels (0–32); `0` preserves the original matte. Quote the `#RRGGBB` or `#RRGGBBAA` color. The output is a silent VP9 alpha WebM for either matte quality. Check edges and missing frames first: the outline decorates the existing alpha; it does not improve segmentation. For a layered treatment, place the base media below an `atmo-*` or `hook-*` overlay and the aligned cutout above it. For `editorial-framed-stage`, use a separate masked window above the stage. See [Native HTML components](html-component.md) for preset discovery.

`oc html focus <config.json> --json` adds the source image, dimmed background, and visible subject as an editable, undoable batch. `--dry-run` validates without writing. Example:

```json
{"assetId":"<source>","mode":"region","shape":"rect","box":[300,200,400,250],"sourceWidth":1448,"sourceHeight":1086,"startFrame":150,"sourceStartFrame":0,"durationFrames":90,"enterFrames":12,"exitFrames":9,"dimPercent":65,"feather":8,"halo":0}
```

`box` is in source pixels. The complete source fits the canvas without stretching. Video begins at `sourceStartFrame`; frames use Sequence FPS. Supply `sourceWidth/sourceHeight` when probe dimensions are unavailable; never edit Asset probe data. Region shapes are `rect/ellipse`.

For object focus, use `mode:object` with `alphaAssetId` and `alphaStartFrame`. Match the cutout's dimensions and content to the original. Supply `alphaWidth/alphaHeight` for a transparent PNG without probe dimensions. Both visual layers are silent; add the original audio once if needed.

For the video-cutout step, prefer `--from-time numerator/denominator` for an exact in-point. Copy `alphaOffset` from the result into the focus config. The alpha video begins at `alphaStartFrame / sequenceFps + alphaOffset`; omitting the offset can cause a mismatch at different frame rates. Use automatic object segmentation on a single CFR shot. For VFR, normalize to CFR or use region focus.

Create the cutout with `oc media focus-cutout <source> --box x,y,w,h --output <new.png|new.webm> [--from-sec S --duration-sec D] --no-wait --json`. Images produce PNG; videos produce WebM. Process only the selected shot. The installed SAM 2.1 CUDA plugin is required. Use the returned service `jobId` with `oc media task watch/cancel`. This step does not change the Project. Check `framesWithoutObject` and the alpha edges before using `oc asset import` and placing the focus component.

New labels use a thicker main stroke, darker edge, and stable text backing. Existing HTML does not restyle automatically; resave or update the component for the new styling. Check readability at mobile size.

## Presenter picture-in-picture

Import the presenter video, then run `oc html presenter <config.json> --json` (inline JSON also works). `fit` defaults to `cover`. `contain` keeps the full video in large windows; circular corner poses keep `cover`. Override with `--fit {cover,contain}`.

- Poses: `full | center | left | right | br | tr | tl | bl | off`. Full is edge-to-edge with no border/shadow. Window size, corner radius, and `box-shadow` interpolate together; the colored border and shadow return on small poses. `br/tr/tl/bl` are circular corner windows; `off` moves off canvas.
- Typical sequence: `full` introduction → `br`/`tr` demo → `left`/`center` emphasis → `full` explanation or close.

```json
{
  "assetId": "<imported presenter video asset ID>",
  "startFrame": 0,
  "sourceStartFrame": 0,
  "durationFrames": 600,
  "cues": [
    {"atFrame":0,"pose":"full"},
    {"atFrame":90,"pose":"br"},
    {"atFrame":300,"pose":"left"},
    {"atFrame":450,"pose":"full"}
  ]
}
```

- All frames use sequence FPS. `startFrame` is timeline placement; `sourceStartFrame` is source in-point. `cues.atFrame` is clip-local, strictly increasing from 0 and less than `durationFrames`.
- Defaults: `transitionSec: 0.38`, `borderColor: "#fb923c"`, `faceX: 50`, `faceY: 38` (0–100). `dimOnCenter: true` dims only at `center`; full dim opacity is 0.
- Real pose changes play `wind-swoosh` (sound 11) one frame early at linear gain `0.5`, clamped to frame zero. Repeated poses do not add cues. Use `--sfx none`, `--sfx <id>`, or `--sfx-volume` (0–2). Four cinematic micro-SFX: `cinema-boom-soft` (soft bass landing), `paper-highlight` (paper swipe), `counter-tick-lock` (mechanical counter), and `micro-whoosh` (short air sweep).
- `includeAudio: true` creates one editable narration track and mutes the video window; set it to `false` for sources without audio. `--dry-run` preflights. The component, narration, and cues are one undoable semantic batch. On uncertainty replay the same request, `--base-revision`, and `--idempotency-key`. Do not write project files. Windows and macOS share the HTML/CSS contract.

## Dual view

Import the videos or stills, then run `oc html dual <config.json> --json`. Example:

```json
{
  "layout": "horizontal",
  "gapPx": 16,
  "splitPercent": 50,
  "panes": [
    {"assetId":"<imported assetA>","sourceStartFrame":30,"startFrame":0,"durationFrames":90,"fit":"contain"},
    {"assetId":"<imported assetB>","sourceStartFrame":60,"startFrame":15,"durationFrames":75,"fit":"cover","cropX":65,"cropY":50}
  ]
}
```

`horizontal`, `vertical`, and `primary` arrange the windows side by side, stacked, or in a primary/secondary layout. Select the layout explicitly; the tool does not infer the narrative relationship. Each window selects its own source in-point and timeline range using the Sequence frame rate. A still starts at 0. `contain` shows the full source; `cover` fills the window by cropping. `cropX/cropY` set the crop anchor (0–100). Override either window with `rect:{x,y,width,height}` in canvas pixels; the rectangle must fit inside the canvas.

`audio:true` adds original sound on a separate track in the same batch; it is off by default. Do not enable it for a silent source. `--dry-run` checks the batch without adding windows. Both windows are created and undone together, remain independently editable, and are not baked into the source video.
