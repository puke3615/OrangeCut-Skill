# Recommend and apply a color grade

Review the footage and offer two or three justified options rather than a long filter list. Apply a look only after the user chooses it.

1. **Measure the main footage.** Run `oc media colorstats` and read `verdicts`. If the sources look different, measure each and base the recommendation on the main section.
2. **Shortlist by format, then adjust for the measurements.** List looks with `oc canvas looks --json`. Use `--look <id>` to select one and `--intensity` to override the recommended strength.

   | Format | First choice | Alternative | Strength | Avoid |
   |---|---|---|---|---|
   | Portrait, travel, fashion | `japanese-airy` | `teal-orange` | 60–80 | `morandi` on skin-heavy shots; heavy stylization |
   | Talking head, explainer, interview | `clean-studio` | `soft-boost`, `skin-soft` | 100 (subtle by design) | An obvious grade that distracts from the speaker |
   | Food, shop visit, unboxing | `food-pop` | `bright-pop` | 80–100 | Monochrome or bleaching |
   | Night or dim interior | `night-lift` | Layer `cool-morning` | 100 | `deep-contrast`, which can crush shadows |
   | Memory, period, family footage | `vintage-wash` | `warm-vintage`, `home-movie-8mm` | 80–100 | Cool looks |
   | Suspense or reveal | `deep-contrast` | `mono-clean` for flashbacks only | 80–100 | Bright or food looks |
   | Home, still life, premium products | `morandi` | `muted-editorial` | 100 | Saturation boosts |
   | Film commentary | Retain the source grade | `teal-orange` only if needed | ≤ 50 | Anything that obscures the film's look |
   | Quick cuts, memes, graphics-heavy edits | `bright-pop` | `vhs-playback`, `editorial-halftone` for transitions only | 80 | Strong grading across the entire cut |

   If `lighting: dark|dim`, start with `night-lift`. If `temperature: cool` and the story calls for warmth, try `warm-daylight` or reduce the cool look's intensity. If `saturation: vivid`, lower a saturation boost to 60 or use `soft-boost`. If `skin: prominent`, avoid `morandi` and `bleach-bypass`, and reduce looks that turn skin green or gray. If `contrast: punchy`, do not add `deep-contrast`.
3. **Review before applying.** Explain the rationale in one sentence per option. When approved, use `oc canvas grade --look <id>` after picture, story, captions, and components are in place.

- Keep one coherent look. Change it mid-cut only for a story reason, such as a monochrome memory, and motivate the transition.
- The grade affects image and video assets, not captions, stickers, or HTML components. To grade the composite itself, export an MP4 and reimport it as footage.
- Explain any lower-than-default strength. A talking-head grade should be hard to notice.
- Use `--lut <absolute-path>` for a supplied `.cube` LUT intended for Rec.709. Do not apply a technical log-to-709 LUT to already normalized footage.
- Preview and export share the shader. Use the live preview to review the look without exporting solely for grade approval.
