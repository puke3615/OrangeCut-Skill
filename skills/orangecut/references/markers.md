# Sequence markers: chapters, beats, and review notes

A marker names a point in the Sequence, such as where the second act starts. Markers can be read and rebuilt with the rest of the edit.

- `oc marker list --json` returns each marker's ID, label, frame, and time in seconds.
- `oc marker add "Chapter 1" --at-frame <frame> --json` adds a marker at an exact frame. Supply `--marker-id` for a stable ID or omit it to generate one.
- `oc marker update <marker-id> [--label <text>] [--at-frame <frame>] --json` moves or renames a marker. Supply at least one change; an empty update is rejected.
- `oc marker remove <marker-id> --json` removes the marker.

Markers belong to the Sequence, not a track. The Sequence uses a half-open interval: a marker at or after its end is invalid. To plan a chapter bar, mark the beats, read the markers back, and place `chapter-bar` with a matching `chapters` list.
