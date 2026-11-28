# Inspect, edit, fork, and verify projects

For a split-screen package, use `oc sequence list`, `oc sequence create`, and `oc timeline add-sequence` instead of intermediate exports. You can reuse the same inner edit in two outer windows with independent transforms and `--muted` on the comparison window. After an inner edit, re-read the outer sequence at the new Project revision; verify picture and listen to the mix before final export. Do not build cross-Project references, cycles, or more than four nested edges. For retryable writes pass the original `--base-revision` and `--idempotency-key` together. See [editing.md](editing.md) for the two frame grids.

These commands take explicit editorial intent. The Agent still chooses material and makes editorial decisions. Check parameters with `oc <group> <action> --help`. For exact request shapes, use `oc capabilities --command timeline.edit --json`; it also supports `timeline.inspect`, `project.fork`, `project.diff`, and semantic command names such as `clip.add`.

## Inspect only the relevant entities

```text
oc timeline inspect --text "caption to edit" --kind caption --json
oc timeline inspect --id clip-a --id clip-b --json
oc timeline inspect --from-frame 300 --to-frame 600 --json
oc timeline inspect --external-ref "shot:opening" --full --json
```

Results include `projectId`, `revision`, exact timeline and source ranges, and linked A/V IDs. `--full` returns all entity fields, not all referenced components, fonts, or derived media. Read `projection` for omitted fields and fetch dependencies separately for complex changes. The default result cap is 200, maximum 1000; an oversized result fails rather than silently truncating. Ranges are half-open. Text matches asset names and caption text, not meaning. Resolve external references to a unique entity; never guess an ID.

## Plan one atomic, undoable edit

Write the plan as UTF-8 JSON. Dry-run and commit the same request:

```text
oc timeline edit --file <plan.json> --dry-run --json
oc timeline edit --file <plan.json> --json
```

```json
{
  "baseRevision": 7,
  "idempotencyKey": "replace-approved-take-01",
  "intent": "Replace the selected clip and preserve its placement and effects.",
  "operations": [
    {"op": "replace-source", "clipId": "clip-a", "assetId": "asset-new", "timing": "preserve"}
  ],
  "constraints": {"unchangedIds": ["clip-ending"]}
}
```

Use IDs and `baseRevision` from inspection. Retry exactly the same document after an uncertain outcome; the key binds the entire plan. A stale revision fails without rebasing. Inspect `transaction`, `summary`, and `committed`, then reread at the new revision and preview the affected edit.

### Operations

- `replace-source`: Match media kinds and retain clip ID, transform, effects, and linked A/V. `sourceStart` is an exact rational and defaults to zero. `timing: preserve` keeps slot and speed; `fit` resizes playback speed to fill the slot; `resize` adjusts the tail at the original rate without moving later content and accepts `durationFrames`; `ripple` requires `durationFrames` and moves later content. Insufficient source, overlaps, and effects that cannot be retained fail explicitly.
- `replace-narration`: Supply standalone audio `clipId`, new `assetId`, `captionTrackId`, `captionIds`, and `captions`. Each new cue is `{text, sourceRange, tokens?}` in the new recording's source time. The service maps it to the timeline using the source in-point and playback rate. Style, speaker, emphases, motion, and extensions inherit only when the match is unambiguous; use `inheritFrom` to name a specific old cue. The service rejects ambiguous styles, missing emphasized words, and incompatible animation retiming. Use `presentation: {speaker, styleRef, emphases, motion, extensions}` to replace presentation explicitly (null for nullable fields, empty arrays/objects to clear), not with `inheritFrom`. An operation-level `styleRef` overrides style; other captions are unchanged. Timing matches replace-source, with optional `atFrame` to move narration and captions together, not with `ripple`.
- `audio-envelope`: Supply audio `clipId` and strictly increasing `points` within the clip as `[local-time-rational, linear-gain-rational]` pairs. For example, `[["0/1","1/2"],["1/1","1/1"]]` goes from half gain at 0 s to unity at 1 s. `interpolation` defaults to `linear` and also accepts `hold`. Only the gain curve is replaced; existing pan and fades are retained, or a mix is created if absent.
- `insert`: Supply `assetId`, `trackId`, `atFrame`, and `durationFrames`, optionally `sourceStart` and `muted`. In the candidate state, the service splits crossing clips, opens a gap across all tracks, and inserts the asset with native linked sound. A crossing caption, locked track, or unsupported time mapping rejects the entire edit.
- `copy-range`: Supply `fromFrame`, `toFrame`, and `atFrame` in the same project, optionally `trackIds` and `ripple`. Preserves source ranges, styles, and A/V pairing; select both sides of linked A/V. Component and caption styles are copied and animation keys get new IDs. The service trims copies of linear clips without trimming originals; captions must be fully inside the range. Gain envelopes are interpolated and shifted exactly, including a possible point at the exclusive media endpoint. Reject partial fades or other effects that cannot be preserved, partial components, unsupported retiming, and transitions that depend on clips outside the range. No cross-project asset import.
- `external-ref`: `{op:"external-ref", id:"clip-a", value:"shot:opening"}` sets a stable external reference, unique in its Sequence. Use it to link to a shot or a script, not paths, secrets, or account-specific fields. Copies do not inherit the unique reference.
- `commands`: When the high-level operations are insufficient, supply the typed `commands` array in the same plan. Dry-run, constraints, and undo cover the entire batch.

Check support before editing complex retiming, derived masks, privacy effects, or incompatible linked A/V. Do not remove effects just to make the request succeed. Source replacement checks both sides of linked A/V. It will not reuse source-dependent enhancements, retimes, masks, or privacy derivatives; rebuild them through their supported commands.

### Constrain the edit

`constraints.duration` fixes the exact Sequence duration. `unchangedIds` protects existing entities. `allowedChangedIds` limits all modifications, including creates, deletes, and Sequence duration changes. Dry-run to get generated IDs before adding scope constraints. Constraints do not change generated IDs, but use a fresh key for the changed formal request. Constraints run against the candidate and fail without writes. Matching media fingerprints do not relax identity constraints. Track order of clips and captions also counts. Inspect `fieldChanges` for JSON paths and before/after values. Large fields are summarized and marked omitted; reread full entities to verify them.

## Fork and compare versions

```text
oc project fork <source-id> --revision <revision> --title "Next cut" --idempotency-key <key> --json
oc project diff <source-id> --against <next-id> --json
oc project diff <id> --from-revision 7 --to-revision 8 --json
```

Fork neither closes nor edits the source. The new project starts closed, without another window. The new project retains source revision, hash, and title; an exact retry returns the same project. An unavailable revision or missing source media fails rather than publishing a partial fork. `project duplicate` still requires a closed source.

Diff works with open or closed projects. It reports changed entities and fields, source/text/time summaries, and before/after duration. Match by stable IDs; a unique identical media fingerprint can normalize reassigned import IDs. Relative media paths do not count as edits, and ordinary text is not rewritten globally. This is a structural comparison, not pixel equivalence or a merge.

## Generate a verification report

```text
oc project check --json
oc project check --layout --from-frame 300 --to-frame 600 --read-frames 300,450,599 --output <report.json> --json
oc project check --audio-clip <voice-clip-id> --json
```

Default checks cover structure, source bounds, caption token alignment, compilation dependencies, and media bindings. Unresolvable required media, fonts, or derivatives fail; unused offline assets are listed separately. `--layout` reuses overlap checks. `--read-frames` produces composited PNGs next to a supplied report path. `--audio-clip` can be repeated to measure selected clips, not the final mix or subjective listening quality.

The report pins project ID and starting revision and rechecks them before returning. A concurrent edit or a failed requested check yields a nonzero exit status. With `--output`, available evidence survives failures. Check `attentionRequired` for layout or offline assets. `notPerformed` lists unchecked items such as full decode, whole-program audio, or human review. `finalExportVerified: false` means no final export validation; frame generation is not visual approval.

### Read-only source sync

Use `oc project check --sync --sequence-id <id> --json` to check overlapping clips on separate video tracks when they share a video source or recorded matte/mask lineage. `syncIssues: []` means no drift was detected among those pairs. A failed check includes `error.details.syncIssues` with the first mismatch per pair in original-source frames. Unrelated overlaps and old mattes without lineage are not inferred to be related. This checks time mapping, not decoded pixels or creative quality.
