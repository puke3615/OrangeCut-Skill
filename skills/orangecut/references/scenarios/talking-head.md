# Talking-head direction

Use this only when a direct-to-camera speaker carries the scene. Keep one true voice lane. Compose each beat from the spoken point, the intended focal object, and the first frame on which the viewer should see it. Inspect the canvas, sequence FPS, source in-point, track order, and caption placement before editing. Fix ASR wording against the recording; cut the argument before styling it.

## Platform & Language Routing

Identify the spoken language, target platform, and aspect ratio first. Honor the approved account style. If targets need different treatments, make separate versions rather than compromising the Chinese cut.

| Route | Direction |
|---|---|
| **Chinese Vertical (9:16)**: Douyin, Xiaohongshu, WeChat Channels, Bilibili vertical | Use clean white bottom captions at **72 px or more at 1080×1920**, with sparse warm-gold `#F4C373` or vermilion `#FF6B4A` keyword highlights. Pair **Noto Serif Bold + Source Han Sans Heavy** from the `fonts` plugin. Keep captions in the **70%–84%** band from the top and shift the staging on clauses every **2–3 s**. |
| **Global Short-Form (9:16)**: X, YouTube Shorts, Instagram Reels, TikTok; English or other Latin-script narration | Use **2–4 words per line** or dynamic word-level emphasis instead of long lines. Start with Inter, Montserrat, Plus Jakarta Sans, or bold Playfair Display. Design for muted autoplay: land a high-contrast visual hook or oversized keyword within **0.5–3 s** (`hook-giant-backdrop` or `hook-contrast-stack`). The hook must make sense without audio. |
| **Landscape (16:9)**: YouTube, Bilibili landscape, long-form X | Place captions in the **82%–92%** band from the top, not the portrait band. Fit line lengths and side margins to a **1920×1080** canvas. Use the extra width for presenter PiP, a speaker beside an evidence card or 3D list, or a two-up comparison using a Nested Sequence. |

## Five Non-Negotiables

1. **Hair-level alpha & intentional edge treatment.** Require `oc media matte --quality high` (MatAnyone 2) for every background replacement, text-behind-speaker stack, or `--outline-width > 0`. Never outline the 192×192 `--quality fast` matte. Choose one of two distinct edge styles—never mix them by accident:
   - *Natural integration (default for editorial/cinematic cuts, dark studio swaps, and text-behind-speaker):* Keep `--outline-width 0` with minimal feather (`0.5–2 px`) and match background darkness/depth-of-field so hair blends organically like real optical bokeh.
   - *Sticker pop outline (optional, brief 1–2 s hook/emphasis beats only):* Use crisp white (`#FFFFFF`, `2–5 px`) as an intentional graphic collage accent—never as a bandage to hide a messy mask, because any stray background highlight or hair artifact gets amplified by the stroke. Always inspect zoomed hair and shoulder crops on multiple rendered frames, including movement. If high quality is unavailable, choose a beat without a matte; do not downgrade silently.
2. **Clause-driven motion.** Shift foreground, background, or framing purposefully every **2–3 seconds** on spoken clauses. Never hold one static stage or card for more than **4 seconds**. Keep the face continuous when the delivery needs trust; move a proof element or reframe instead of adding a gratuitous cut.
3. **Editorial type, clean captions.** Use the route's type and caption treatment. On the Chinese route, Noto Sans Black is an alternative to Source Han Sans Heavy; scale the 72 px baseline for other portrait canvas sizes. Keep captions legible with a subtle stroke or drop shadow. Never put ordinary subtitles on heavy opaque black bars.
4. **Music bed, not a dry cut.** Use mood-matched BGM at about **−17 LUFS** between speech and duck smoothly to **−23 LUFS** under speech. These are measured bed levels, not master targets or gain settings. Ship without BGM only if the user explicitly requests a raw anti-edit style.
5. **Audible event foley.** Start around **45%–75% gain**, depending on sample peak; audition against voice and BGM rather than burying cues at 7%–13%. Sync `dong`, `bo`, `ding`, `marker-tick`, `marker-sweep`, `cinema-boom-soft`, `wind-swoosh`, or `paper-highlight` to actual foreground pops, cards, or keywords. Never add a whoosh to a plain hard cut just because it cuts.

## Golden 5-Second Hook Choreography

Choose one recipe. Typical timing: establish the speaker or tension at 0–0.5s, make the first visual change on the claim at 0.5–1.6s, then hold or resolve long enough to read before 5s. The spoken word wins over these suggested windows. Layer orders below are **back to front**; the captions remain on their own lane.

1. **Dimmed circular reveal → outlined subject pop.** Start on a dim plate. Reveal a circular patch of the aligned, ungraded source over it with an animated `ellipse` mask (equal pixel radii); grow from a small focal aperture to a stable circle. Place `hook-giant-backdrop` over that reveal, then land the outlined cutout on the promise word: `oc media matte <source> --output <cutout.webm> --quality high --outline-width 6 --outline-color '#FFFFFF' --json`. Align source time and transform on every copy; the bright outline should separate the subject, not buzz at the edge.
2. **Anchored cutout → background wipe → type sandwich.** Hold the cutout still. Use `oc media make-mask` with `--end-*` and `--frames` to build a white-keeps animated mask at source dimensions and cadence. Apply it to the *background* clip with `oc timeline mask <clip-id> --mask <mask-video> --json`; match mask length to the selected clip range. Stack plate → wiping background → `hook-giant-backdrop` → cutout. Wipe toward the claim; don't move the cutout to follow the wipe.
3. **Studio spotlight → text behind subject.** Source → `atmo-spotlight` → `hook-giant-backdrop` → clean matte. Set `centerX`/`centerY` and `radius` to the subject's position; set a light temperature that fits the shot. Land the headline as the pool settles. Keep at least one readable part of every key glyph clear of the silhouette.
4. **High-contrast type stack → half-frame rise.** Use `hook-contrast-stack` for kicker → setup line → focal phrase. Choose `scrimCoverage=upper` or `full`, then set `scrimOpacity` to cope with the source rather than burying it. Bring a matted subject up from the lower half using native position keyframes, settling before it reaches the title or caption reservation. Inspect each stagger, especially the first frame both subject and focal word are visible.
5. **Exposure flash → radial vignette → keyword.** Lead the cut with one `atmo-flash-hit` (0.35s by default); carry the quieter `atmo-focus-vignette` into the settled shot. Disable its second glint (`flashIn=false`) if the main flash already supplies the beat. Add one native kinetic emphasis on the keyword; never flash over several syllables or use repeated bright pulses.
6. **Analog texture → vertical glowing type.** Place `atmo-crt-scanlines` *or* `atmo-film-grain` above the base and `hook-vertical-glow` above the texture. Keep the two phrases short; anchor them on the side opposite the speaker, using clip position or a tested authored variant if the default side does not fit. Read at phone size before making the texture or glow stronger.

**Placement and trim.** Discover using `oc html presets --pack kinetic --category opening --json` (or `--pack editorial` / `--pack atmosphere`); inspect the ID before setting fields. Add each preset with `--at-frame` and `--duration-frames`. For the giant backdrop, `--set headline=99% --set subtext= --set yPercent=42` gives a short headline with no subtitle. Use `--sfx cinema-boom-soft` only if it helps; leave silent when manually placing the foley one frame early. Check frame zero, the pop/wipe midpoint, and the settled frame.

## Mid-Section Choreography: 8-Beat Studio Repertoire

Rotate two or three methods; this is a repertoire, not a required sequence. Schedule the next shift on a clause pivot, proof word, or useful breath, leaving enough time to read the evidence.

| Method | Execution |
|---|---|
| **Multi-Cam Illusion Punch-In** | Alternate `1.0x` with `1.12x–1.16x` at clause pivots or breath cuts. Keep eye height and eyeline stable. On the emotional climax, use native compositor `oc keyframe upsert` with `--property scale` and `--easing ease_in_out` for a smooth push; use position keys to keep framing if needed. Never use FFmpeg `zoompan`. |
| **Dark Studio / Bookshelf Background Swap** | Stack a curated low-key studio or bookshelf plate below a `--quality high` cutout. Motivate a smooth GPU-composited push-in on the claim with native `oc keyframe upsert` scale/position keys; never use `zoompan`. |
| **Circular Portrait + Frosted Evidence Card Box** | Place the speaker in a soft-lit circular frame. Pop two or three real-photo proof cards in sequence inside a translucent dark glass tray; land a `marker-tick` when each card becomes legible. |
| **Bilateral Ping-Pong Keywords** | Alternate bold warm-gold keywords on the left and vermilion on the right on contrasting clauses. Keep the face centered and show one side at a time; use `hook-flank-badges` when a short parallel pair should read together. |
| **Foreground Rising Evidence Strip** | Raise a strip of real-photo B-roll from the lower third with eased native position keys. Put one bold, slightly angled keyword above it; stop the strip clear of the caption band. |
| **Speaker Shrink Bottom-Left + 3D Perspective Checklist Card** | Ease native scale/position keys to tuck the speaker bottom-left as a subtly perspective-tilted dark glass checklist enters. Highlight one row at a time on the spoken points and keep unspoken rows quiet. |
| **Framed Editorial Stage** | Add `editorial-framed-stage` as a backplate. Fit a rounded or masked speaker window just inside the frame on a higher visual lane. Top title names the point; bottom strip states the takeaway, not the whole caption. Check that the strap does not occupy the caption band. |
| **Evidence Cutaway / Data Behind Subject** | Let the voice continue over licensed B-roll or credited proof (`cinema-news-highlight`, `cinema-social-post`, `cinema-quote-glass`). For layered statistics, stack base → `cinema-kpi-chart` or `hook-giant-backdrop` → synced high-quality matte. Check digits and units at maximum occlusion. Never fabricate proof or overstate it. |

At real section boundaries, `cinema-chapter-minimal` can reset the scene. Use `cinema-progress-bar` only when a map helps; weight chapters by their actual spans and keep the rail clear of face and captions.

## Word-level timing, audio, and verification

For a Before/After split screen, nest the inner edit directly in the outer layout and mute the comparison window if only one side should be audible. A pause or caption edit inside the child appears in the next outer preview/read/export without an intermediate MP4.

1. **Map source words into edit frames.** Run `oc media transcribe <media> --json`; use `data.words` timestamps, not segment boundaries. Map each retained word through its source in-point, clip start, and any retime to the sequence frame grid. Snap to the first frame on or after the cue, and audition where ASR confidence or alignment is weak. Place headline reveals, badges, and visual accents on the meaningful spoken word, not on every noun.
2. **Tighten silence conservatively.** Run `oc media silence <media> --json`; tune its threshold using the measured voice and noise floor. Cross-check candidates against word boundaries and listen before cutting. Keep meaningful pauses, breaths and final consonants; apply linked picture/audio edits atomically.
3. **Verify the layered mix.** For a cue with a soft attack, try one frame before the visual hit, clamped at frame zero. If the preset already contributes sound, use `--sfx none` before adding an explicit cue. Keep derived cutouts silent. Measure the bed before and during speech, then audition the actual mix at phone volume: every intentional cue should register without masking a syllable or clipping.
4. **Protect captions.** Use the route's caption band and leave room for feed controls on portrait versions. Run `oc layout check --json` after moves and before export; resolve every `CAPTION_OVERLAP`. Inspect `unverified` items and rendered frames at hook entry, peak, and settle, and at midsection pivots. Layout checks cannot confirm face clearance or moving WebM alpha. Listen through transitions and review the exported segment before calling it final.

## Anti-patterns and restraint

- One dominant hook and two or three repeating mid-section techniques per edit. Don't combine a flash, whip, dust layer, badge pair, and giant word just because they exist.
- Don't keyframe every clause or decorate unimportant words. Leave clean frames after emphases and preserve a continuous face on the moments that need trust.
- Don't trade proof or readable captions for a clever sandwich. Use plainer type, a simple cut, or a clean hold when effects obstruct the point.
- Don't clone loudness by copying volume percentages, double the voice with the upper layer, or add noise/flicker over text to imply energy. Check at phone size with sound on and muted.

## Local timing repairs

Keep the complete source. For a clipped word tail, check the source handles and dry-run `oc timeline ripple-trim <clip-id> --delta-frames +9 --exclude-tracks bgm --dry-run --json`. For excess silence use `oc timeline ripple-delete --from-frame <a> --to-frame <b> --exclude-tracks bgm --dry-run --json`. Commit only the verified splice; don't rebuild the cut. If a newly visible source interval needs alpha, request the extended range with `oc media matte --in-frame <a> --out-frame <b>` using the original settings and prompt anchor. Check cache counts and inspect both seams. Verify the base/foreground mapping with `oc project check --sync --json`.
