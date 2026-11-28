# Keep source audio intact when adding visual markers

New labels, annotations, arrows, and focus effects are visual only. Do not add built-in sound by default. When the user requests a cue, import the chosen audio and place it on its own track with `timeline add`. Leave source sound, narration, and existing tracks unchanged.

## Remove a legacy cue

```powershell
oc sfx marker <component-clip-id> --preset none --base-revision <revision> --idempotency-key <key> --json
```

In the desktop editor, remove the cue in the legacy component's edit form and save. To temporarily disable all legacy component cues for a project, use `oc sfx markers --no-enabled --json`. Neither command changes source sound or standalone audio clips. Use the exact revision and key; these commands go through Core and support undo/redo.

Legacy sound settings, typed `audioCue`, sound asset IDs, and the master switch are read, rendered, and exported as stored. Opening a project does not rewrite them. Explicit legacy settings can reconstruct a historical project but are not the default for new markers.
