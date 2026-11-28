# Project lifecycle

## Manage a project by ID

- `oc project rename <project-id> --title <title> --json` renames a project.
- `oc project duplicate <project-id> --title <title> --json` copies a closed project's content and media under a new title. The copy starts at revision 0 with independent history. Use it to reuse a template without changing the original.
- `oc project trash <project-id> --json` moves a closed project to the system Trash. The user can recover it there. Never delete a project directory directly.

These commands address the given ID, not the implicit current project. Duplication and trash require the target to be closed; other projects can stay open. To copy the current revision without closing its window, use [project fork](agent-operations.md). For an experiment, list projects with `oc project list --json` and `trash` the appropriate closed copy when cleanup is requested.

## Open, edit, and close

- List: `oc project list --json`.
- Create: `oc project create --title "..." --json` for a canvas that follows the first clip. Add `--width 1080 --height 1920 --fps 30` for a fixed vertical canvas.
- Open: `oc project open <project-id> --json`.
- Close: `oc project close --json`; on multi-project targets pass `--project <id>` to close the intended project.

Import adds an Asset to the library, not the timeline. Read back `assetId`, then use `oc timeline add`. Before split, move, trim, remove, or place, read `oc timeline snapshot --json` for the exact clip and track IDs. Use a raw CommandBatch for policies such as changing tracks, closing a gap, or rippling later clips when a shortcut cannot express them. Shortcuts never infer these policies.

The CLI discovers the app's private loopback service and credentials, and starts the service when needed. Do not provide an endpoint, port, token, repo path, or data root for routine calls. Do not start the service separately: a single lock already coalesces concurrent `oc` invocations.

Use `oc docs --json` to open offline Swagger UI with a short-lived same-origin session. For a headless or remote shell use `oc docs --url --json`: it returns a read-only documentation URL without opening a browser or creating a session. Neither prints process credentials or one-time session tickets.
