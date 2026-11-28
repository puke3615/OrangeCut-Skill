# Native HTML components

Use `dev.orangecut.html` for information cards, tables, inline SVG, charts, and CSS animation that built-in text, shapes, or captions cannot express. OrangeCut compiles these components for HyperFrames/Chromium.

## Discover a preset or author your own

- Start with `oc html presets --pack cinema --json`, then `oc html add --preset <id> --set <slot>=<value>`. This is the same library as the editor's built-in panel.
- Filter along two independent dimensions: `--pack` (`cinema`, `editorial`, `kinetic`, `meme`, `utility`) and `--category` (`opening`, `evidence`, `data`, `narrative`, `callout`, `transition`, `meme`). Combine filters: `oc html presets --pack cinema --category data --json`. Get only short summaries and default durations; then use `oc html presets <id> --json` to inspect slots, CSS theme variables, and `sfxCues` for one candidate.
- Prefer `cinema-*` for common use cases. Hand-authored HTML remains fully supported: `oc html add <fragment.html> --at-frame <frame> --duration-frames <frames>`; presets are optional. For a custom atomic batch, use `oc command apply` with `component.add` and `clip.add`.
- CinemaKit includes SFX in the same batch. `--sfx none` mutes all cues; `--sfx <id>` replaces only the first cue.

## Responsive sizing

- Opt into the new overlays with `oc html presets --pack atmosphere --category lighting --json` (or `texture` / `transition`), `--pack kinetic --category opening`, or `--pack editorial --category opening|callout|narrative` (choose one category). Unfiltered discovery omits these additions. Inspect an ID for the exact slot and `variables[].parameter` names, numeric bounds, and enum values. For example, `oc html add --preset atmo-spotlight --at-frame 0 --set centerX=55 --set warmth=warm --json`.
- Use `atmo-*` for lighting and texture, `hook-*` for standalone or interleaved type, and `editorial-framed-stage` as a backplate for a separate media layer. A layer sandwich can use `oc media matte <source> --output <clip.webm> --outline-width 6 --outline-color '#FFFFFF' --json` above the graphics. `hook-giant-backdrop` is silent by default; opt in with `--sfx cinema-boom-soft`.

Set `container-type: size` on the root. Use `cqmin` for type and `cqw` for width-relative spacing, so portrait, landscape, and 4K scale proportionally. Use container units on descendants, not on the container itself. Fixed `px` does not scale; `vw`/`vh` can diverge between the downscaled preview and export. Fill the clip root with `width` / `height` at `100%`, with layout on an inner wrapper. Animate `transform` and `opacity` on descendants; the Clip owns both on the root.

## Data shape

```json
{
  "id": "component-quote-card",
  "componentType": "dev.orangecut.html",
  "capabilityRequirements": ["dev.orangecut.component.html"],
  "properties": {
    "root": { "tag": "div", "classes": ["card"], "children": [] },
    "stylesheet": "@keyframes rise{from{transform:translateY(40px);opacity:0}to{transform:none;opacity:1}}.card{animation:rise .6s ease-out both;animation-delay:calc(var(--oc-clip-start, 0s) + 0s)}"
  }
}
```

`root` is a typed subtree, not a string of markup. The Clip owns the root's timing, track, and transform.

| Field | Meaning |
|---|---|
| `tag` | Allowed element name (see list below) |
| `namespace` | `html` (default) or `svg` |
| `text` | Text content |
| `classes` | Named CSS hooks |
| `attributes` | Ordinary attributes such as `viewBox`, `role`, `aria-*` |
| `styles` | Inline CSS declarations as a map |
| `assetId` | Project Asset for `img`, `video`, `audio`, `source`, or `use` |
| `children` | Child nodes |

## Animation and media

Scope CSS and `@keyframes` to distinctive classes: styles enter the whole composition. No JavaScript. HyperFrames seeks CSS animations frame-accurately. At a nonzero clip start, use `calc(var(--oc-clip-start, 0s) + <local delay>)` for `animation-delay`. Put it after the `animation` shorthand. Use the same expression at frame zero. Example: frame 150 at 30 fps plus .2 s gives a 5.2 s global delay; omitting the clip start can make the animation finish before the clip appears.

```css
.quote-body {
  animation: quote-rise .8s ease-out both;
  animation-delay: calc(var(--oc-clip-start, 0s) + .2s);
}
```

Use `assetId`, never `src`. Authorized local assets are resolved by the compiler and fingerprinted again at render. No remote URL: `default-src 'none'; connect-src 'none'`.

```json
{ "tag": "img", "assetId": "asset-logo", "styles": { "width": "120px" } }
```

## Rejected constructs

A rejection is a structured batch failure, not a silent fallback.

| Rejected | Reason |
|---|---|
| `script`, `iframe`, `object`, `embed`, `form`, `a`, `canvas`, `template` | Execution, navigation or embeds |
| `on*` | Event handlers |
| `id`, `class`, `style`, `src`, `data-start`, `data-hf-*`, `data-oc-*` | Compiler-owned; use typed fields |
| CSS `url(...)`, `@import` | Bypasses the authorized asset registry |
| `;` in inline style values | Starts another declaration |
| `javascript:`, `vbscript:`, `data:text/html` | Executable content |
| `img` / `video` / `audio` without `assetId` | No authorized source |

Limits: 512 nodes, 32 levels, 64 KiB per text node, and 128 KiB per stylesheet.

## Allowed tags

Structure and text: `div span p section article header footer main aside nav
h1..h6 ul ol li dl dt dd blockquote figure figcaption hr br pre code em strong
b i u s small sub sup mark time abbr table thead tbody tfoot tr th td caption
colgroup col ruby rt rp bdi bdo wbr`

Project media: `img video audio picture source`

Inline SVG: `svg g path rect circle ellipse line polyline polygon text tspan
defs linearGradient radialGradient stop clipPath mask filter feGaussianBlur
feOffset feBlend feColorMatrix feComposite feMerge feMergeNode use symbol marker
pattern foreignObject`

## Full example

```bash
cat <<'JSON' | oc command apply --stdin
{
  "commandId": "add-quote-card",
  "projectId": "<from `oc project current --json`>",
  "baseRevision": <current revision>,
  "intent": "Add an animated quote card over the intro.",
  "commands": [
    {
      "type": "component.add",
      "payload": {
        "component": {
          "id": "component-quote-card",
          "componentType": "dev.orangecut.html",
          "capabilityRequirements": ["dev.orangecut.component.html"],
          "properties": {
            "root": {
              "tag": "div",
              "classes": ["quote-card"],
              "styles": { "width": "100%", "height": "100%", "display": "flex",
                          "align-items": "center", "justify-content": "center" },
              "children": [
                { "tag": "blockquote", "classes": ["quote-body"],
                  "text": "Explain the risks before the benefits.",
                  "styles": { "color": "#f5f5f7", "font-size": "72px",
                              "max-width": "80%", "text-align": "center" } }
              ]
            },
            "stylesheet": "@keyframes quote-rise{from{transform:translateY(48px);opacity:0}to{transform:none;opacity:1}}.quote-card{background:linear-gradient(160deg,#101014,#1d1d24)}.quote-body{animation:quote-rise .8s cubic-bezier(.2,.8,.2,1) both;animation-delay:calc(var(--oc-clip-start, 0s) + 0s)}"
          }
        }
      }
    },
    {
      "type": "clip.add",
      "payload": {
        "sequenceId": "sequence-main",
        "trackId": "track-component",
        "clip": {
          "id": "clip-quote-card",
          "enabled": true,
          "timelineRange": { "start": {"num":"0","den":"1"}, "end": {"num":"3","den":"1"} },
          "source": { "type": "component", "componentId": "component-quote-card" },
          "playback": { "rate": {"num":"1","den":"1"}, "reverse": false, "freeze": false },
          "effects": [],
          "extensions": {}
        }
      }
    }
  ]
}
JSON
```

Discover exact command types and payload schemas with `oc capabilities --json`. Read the live revision and IDs before building the batch. Use `oc proposal create` for review-first requests: only the user accepts or rejects the card in Desktop.
