## Choose the right overlay density

These observations come from 21 high-engagement examples across six categories: short drama, film commentary, travel, food, fitness, and tech reviews (16k to 4.7M likes, August 2026). Treat the sample as creative guidance, not a causal ranking.

- **More overlays did not predict reach.** The sample's leaders included a 4.7M-like travel vlog, 2.3M-like tech review, 2.2M-like film commentary, and 2.0M-like AI drama. Three needed little beyond captions; the AI drama used captions only.
- **Use overlays to deliver information.** Tech reviews and fitness tutorials benefit from charts, labels, and lists when viewers need facts they can use. In narrative formats, favor captions and an occasional card so the visuals stay readable.
- **Match pacing to the format.** Typical shots in the sample ran 1.8s for food, 2.3s for short drama, about 3.3s for travel, 3.7s for commentary, 6.8s for tech reviews, and about 8.3s for tutorials.
- **Check framing before reusing a layout.** Fifteen of the 21 examples were 1920 x 1080. Preset sizes use canvas-relative values. Check a frame on the target canvas before committing a layout from a different orientation.

## Charts and persistent labels

- **Charts:** Use `chart-bar` for labeled bars, `chart-inline` for values inside bars, `chart-rank` for numbered rankings, `chart-gradient` for gradient bars, `chart-minimal` for no track or plate, `chart-segment` for battery-style cells, `chart-column` for vertical bars, `chart-neon` for a neon treatment, `chart-diverge` for a shared centerline, and `chart-card` for one card per row. Supply `bars` as a JSON array of `label`, numeric `value`, and optional `unit`: `--set bars='[{"label":"iQOO 13","value":"9.2","unit":"h"},{"label":"Pixel 10","value":"6.4","unit":"h"}]'`. Bar lengths are relative to the maximum, not the sum. For lower-is-better metrics, order rows and label the direction (“Shorter is better”), or convert values to scores first.
- **Persistent labels:** `tag-bar`, `tag-badge`, `tag-numeral`, `tag-pill`, `tag-outline`, `tag-topbar`, `tag-corner`, `tag-lower`, `tag-note`, and `tag-neon` take `number`, `title`, and optional `note`. Leave `number` blank for an unnumbered label.
- **Countdown labels:** `tag-countdown` takes `label`, `value` (calculate this before editing), `unit`, and `note`. Blank slots take no space. For daily series, record the target date in the account profile and calculate the value from the publication date. Disable the default entrance sound with `--sfx none` if it would cover the opening narration.

## Lists and speech bubbles

- **Lists:** `list-numbered` for steps, `list-bullet` for points, `list-check` for checklists, `list-stat` for big numbers with explanations, `list-timeline` for dates, `list-rank` for scores, `list-versus` for two-column comparisons, `list-progress` for percentages, `list-cards` for a wrapping grid, and `list-quote` for ruled text. `list-recap` is a full-frame, centered summary with a high-opacity plate. Use `title`, optional `footer`, and three to six `items` with a `title` each. Keep it on screen long enough to read or capture.
- **Rows:** The `items` array determines the row count. For example: `oc html add --preset list-rank --set 'title=Where the Money Went' --set 'items=[{"title":"Rent","score":"38%"},{"title":"Food","score":"22%"}]'`. Check each preset's schema: stats use `value` and `title`, timelines use `when` and `title`, comparisons use `left` and `right`, and progress bars use `percent`. Rows animate in individually.
- **Legibility:** The default dark plate is about 70% opaque. Use `--oc-list-plate`, `--oc-list-pad`, and `--oc-list-radius` to adjust it. `--oc-list-accent` recolors numbers, marks, and bars together.
- **Bubbles:** `bubble-say` is white with a tail toward the lower left; `bubble-say-right` mirrors it; `bubble-think` is dark with an upward tail; `bubble-shout` is yellow. Set the tail position with `--oc-bubble-tail-at`, and place the box with `--oc-bubble-x` and `--oc-bubble-y`. Point the tail at the actual speaker.

## HUD overlays (`hud-*`)

Use these to label parts or data in maker videos and reviews. The four presets share enter/exit motion and a default cyan `--oc-hud-color` of `#4DE3FF`. Dimensions are canvas-relative.

- `hud-callout`: put the anchor `--oc-hud-x/--oc-hud-y` on the object. The leader runs vertically, then horizontally. `--oc-hud-up` is -1 up or 1 down, and `--oc-hud-side` is 1 right or -1 left. Set the lengths with `--oc-hud-rise`/`--oc-hud-run`. Slots: `title` (small) and `value` (large).
- `hud-ring`: counter-rotating rings centered on a point. `--oc-hud-size` is the outer diameter. Slot: `label` under the ring.
- `hud-target`: corner brackets, a scanning line, and a label above the box. Bounds: `--oc-hud-x/y/w/h`. Slots: `label` and `info`.
- `hud-data`: data rows on a translucent plate, for example `--set items='[{"label":"Fetch latency","value":"11 s"}]'`. Heading slot: `title`.

To track an object, place the overlay on a reference frame, then run `oc timeline follow <component clip> --target <shot> --box <object canvas box on the reference frame> --at-frame <reference-frame>`. This adds translation keyframes, not scaling. For changing object size, use `oc shape add rectangle` with `--scale box`. Put the anchor on the object and aim the label toward open space so it does not cover the subject in motion.

## Recreated interfaces (`ui-*`)

Show a chat, comment, search, or notification as a story beat. `--oc-ui-x/--oc-ui-y`, `--oc-ui-width`, and `--oc-ui-size` use canvas-relative values. Place the overlay in open space, away from faces.

- `ui-chat`: `--set title=Casey --set messages='[{"side":"left","text":"Do you have the data?","avatar":"Me"},{"side":"right","text":"Yes, sending it now.","avatar":"C"},{"side":"right","kind":"file","text":"data.zip","meta":"1.2 MB","avatar":"C"}]'`. `side` selects left (other person, white) or right (self, green). Use `kind` of `file` for a file card; omit it for text. `meta` is the card's secondary line, and `avatar` is a short label. Messages appear in order at `--oc-ui-stagger` intervals; leave enough time in the Clip for all rows.
- `ui-comment`: `avatar`, `nickname`, `text`, `meta` (for time or location), and `likes`.
- `ui-search`: `query` types in, then the button presses. The default `--oc-ui-type` is 1.4s. `oc` derives `--oc-ui-steps` from the character count of `query` unless explicitly set; it counts letters in English, not words. The built-in `dazi` typing sound (1.3s) starts 0.35s after entry. `oc sfx set <component> --sfx <other-id>` changes that sound without moving the delay or removing the click. For slower typing, extend the sound by adding `oc sfx add dazi --at-frame <frame>`. The built-in `dianji` click plays at the fully pressed frame, 0.6s plus typing duration. `--sfx none` at placement or `oc sfx set <component> --sfx none` afterward removes both sounds.
- `ui-notify`: a banner that slides down from the top. Slots: `icon`, `app`, `when`, `title`, `text`. Set the icon color with `--oc-ui-icon`.

These overlays do not occupy the main video track. Chat, comment, and notifications default to a pop sound; search defaults to typing and a click. Use `--sfx none` to opt out.

## Comparison overlays (`compare-*`)

Use these for products, methods, people versus machines, or before/after comparisons. The shared colors are red for A (`--oc-cmp-a`) and blue for B (`--oc-cmp-b`).

- `compare-vs`: opposing nameplates slide in; the center title lands with a flash and shake. Slots: `left`, `left-sub`, `right`, `right-sub`, `vs`. Set vertical position with `--oc-cmp-y`. Default sound: impact.
- `compare-card`: show one side's name and attributes, for example `--set name=Robot --set tag=B --set 'items=[{"label":"Time","value":"11 s"},{"label":"Cost","value":"CNY 20,000"}]'`. Keep A left/red. For B, use `--set=--oc-cmp-x=62cqw --set=--oc-cmp-from=1 --set=--oc-cmp-color=#2F8BFF` for a right-side blue card.
- `compare-bar`: use a numeric left-side share (`--oc-cmp-share`, for example `--set=--oc-cmp-share=22`). Match the display strings in `left-value`/`right-value` to the share yourself.
- `compare-countdown`: READY, 3, 2, 1, GO. `--oc-cmp-beat` defaults to 0.6s; GO stays until the end after the five beats. Set the `ready`/`three`/`two`/`one`/`go` slots to customize it. The preset is silent; add cues on beat starts with `oc sfx add` if needed.
- `compare-result`: reveal the result with a radial burst. Set `text` to the result and `sub` to a short summary, e.g. “Robot arm: 3x faster.”

A typical sequence is VS opener, two cards or a bar, countdown, test footage, then result. Move nameplates or the comparison bar with `--oc-cmp-y` if they compete with captions.

## Group shots into narrative scenes

OrangeCut does not expose a scene command. For long-form commentary and reference studies, combine these signals to distinguish scene changes from camera cuts:

1. **Shots:** Use `oc media shots` to find cut points. A scene boundary must be one of those cuts, never mid-shot.
2. **Speech:** Use `oc audio speakers` to get the speaker timeline. A speaker change across a cut plus at least about 1.5–2 seconds of silence around it suggests a scene change; use `oc media silence` spans as evidence. If speech continues across the cut, treat it as a camera change within the same scene.
3. **Picture:** For uncertain cuts with no dialogue or a single speaker, sample a frame on each side and ask `oc media describe` what setting it shows. Compare words, not individual characters, looking for a clear subject or location change. Use `oc media search` vector distance as a cheaper first pass if needed.
4. **Evidence:** Record the boundary signal and the shots it covers. Do not infer a title or summary at this stage. Keep the evidence traceable to source timecodes for later commentary edits.

For long videos with thousands of shots, run the speech rule over the whole film first. Apply visual checks only to unresolved cuts in monologues or stretches without dialogue.
