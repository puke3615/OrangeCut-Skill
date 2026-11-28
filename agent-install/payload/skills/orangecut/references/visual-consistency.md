# Visual consistency across shots

Use this workflow when the same character, location, or object must remain recognizable across shots, scenes, or episodes. It adds no Project fields and does not mandate a model or protocol. Follow the user's style and continuity rules first.

## Decide what must stay consistent

Give each recurring entity a stable ID and separate these three categories:

| Category | Example | What to do |
|---|---|---|
| Fixed traits | A cat's face and markings, window layout, product shape and logo placement | Check every scene against the approved reference. |
| Planned changes | Outfit, age, time of day, wear | Record the state and the shots or episodes where it applies. Do not flag these changes as drift. |
| Unverified details | Back of the product, inside of the cover, unseen side of a building | Mark them unknown. Do not present a generated guess as fact. |

For narrated work, finalize and record or synthesize the voiceover, measure its actual timing, then break it into shots. For other formats, follow their own audio structure. Record each shot's duration, action, composition, entities and states, and source material. Do not force every entity into every shot.

## Build traceable references

- **Characters:** Where useful, make approved front, side, and back views, face close-ups, and a color reference. Give each recurring character a separate sheet. Check features, proportions, clothing, and accessories before approval. For fictional characters, `oc media genimage --model gpt` is one option; do not invent missing details for real subjects.
- **Locations:** Fix the room layout, doors and windows, key furnishings, and color palette. Use a single view if it is sufficient. Any added view must agree with the established layout.
- **Products and other real objects:** Prefer original, official, verifiable sources. Label generated guesses as unverified. Check details that affect a purchase against a credible source.
- **Records:** Track the stable ID, version, source and reliability, approval status, and applicable state. Keep iterations distinct from the approved reference. Examples: `C1_cat_v1`, `C2_owner_v1`, `S1_room_v1`.

Save the reference list, shot map, and review notes with the source assets, not in the Project files, SQLite, or cache. Bring approved material into OrangeCut with `oc asset import` and semantic edit commands.

## Bind the right references for each shot

Test a few cross-scene or multi-entity shots before generating the batch. Map each shot to specific asset versions:

```text
Shot 12A | Narration line 12 | About 4 seconds
Reference 1 = C1_cat_v1   (cat)
Reference 2 = C2_owner_v1 (person)
Reference 3 = S1_room_v1  (living room)
Action = A cat watches a person in the same living room; no duplicated characters.
```

Pass the references in the order the shot requires and specify what each image should control. An identity reference is not a fixed start frame. If the first frame must be exact, confirm the generation tool supports that input. For video-to-video work, start with a reliable video reference. Import the result via OrangeCut's supported interface.

Check current model limits, concurrency, and prompt requirements in the material-generation workflow. External tools can make source assets, but control the OrangeCut Project only through `oc`.

## Review generated footage before delivery

Compare each shot's first, middle, last, and key action frames against the approved references and adjacent shots. Check faces, proportions, outfits, and character count; then check windows, furniture, and movement through the scene; finally check object shape, color, parts, and branding. Look for morphing, unintended text, black frames, and broken motion. Stills help locate problems but do not replace playback of an entire high-risk action. `oc media faces` can help screen faces; the Agent or user makes the final visual judgment.

Find whether a problem came from the reference, shot map, prompt, or generation, then fix only the affected shot. Do not hide an inaccurate product with captions or cropping. Placeholders are fine for a rough cut, not a final one. Check the actual MP4 after export for the ending, key shots, continuity, captions, and sound; Job `ok` and Project preview are not acceptance. Archive the approved references, shot map, and fixes for the next edit.
