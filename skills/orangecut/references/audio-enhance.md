# Standalone voice enhancement

In the desktop timeline, right-click audio or a video with sound and choose voice enhancement. The panel shows progress and supports cancellation. The derived asset replaces only the audio; picture, edit points, and linked A/V stay intact. Undo or restore the original sound. Changing presets starts from the original source. Restore normal playback before processing retimed, frozen, or reversed clips.

Use this for phone recordings, live narration, or TTS that needs more consistent, intelligible sound. The local service uses packaged FFmpeg without an open Project, GUI, or cloud call. When hiss overlaps speech, use separate noise reduction rather than a gate or more gain. Available since 1.1.0:

```sh
oc audio enhance "narration.wav" --preset none --noise-reduction standard --noise-engine fft --output "cleaned.wav" --json
oc audio enhance "narration.wav" --preset natural --noise-reduction standard --noise-engine deepfilter --output "enhanced.wav" --json
```

- `--noise-reduction off|standard|strong` is independent of `--preset none|natural|clear`. An explicit setting replaces the preset's noise reduction; do not combine it with `--denoise-db`.
- `fft` is the bundled basic denoiser. `deepfilter` uses the bundled OrangeCut floating-point runtime on CPU; audio stays local. A missing runtime fails explicitly rather than falling back. Standard and strong cap suppression at 12 and 24 dB, respectively, not a guaranteed measured reduction. Start with standard and audition quiet syllables, sibilants, breaths, and tails after stronger processing.
- `none` preserves tone while controlling loudness and peaks. `oc audio denoise` uses the same job service with `none` + `standard` + `deepfilter`, writing a new 24-bit WAV.
- The pinned DeepFilterNet3 / OrangeCut 0.5.6-orangecut.1 runtime preserves sample count, channels, and start/end timing through floating-point processing and 48 kHz / 24-bit output. New requests do not use the old denoise plugin adapter or require upgrading it.
- Leaving the new options unset preserves `natural`/`clear` compatibility. Check the service's `enhance-presets` version before using newer fields. The desktop recording panel remembers tone and denoising settings, keeps both original and processed recordings, and defaults to loudness-matched comparison.

Always audition the unprocessed recording first. If settings change, process from the original, not from a denoised copy. Combine denoising and enhancement in one request.

1. Run `oc media loudness "<input>" --json` to measure the original. Choose settings based on both the measurement and what you hear.
2. Run `oc audio enhance-presets --json` to verify support. `natural` adds warmth while preserving dynamics and does not denoise by default. `clear` adds articulation and mild 6 dB FFT noise reduction. For clean material, try `--denoise-db 0`.
3. Produce a new WAV from the original:

```sh
oc audio enhance "<input>" --preset natural --output "<new-natural.wav>" --json
oc audio enhance "<input>" --preset clear --output "<new-clear.wav>" --json
```

Output is 48 kHz / 24-bit PCM WAV. Mono and stereo are preserved by default; for more channels choose `--channels mono|stereo`. Multiple audio streams are rejected; select the desired stream first. The timeout defaults to 1800 seconds; `--timeout-seconds` accepts up to 14400. For long tasks pass `--no-wait`, retain `data.jobId`, and run `oc media task watch <jobId> --json`. Cancel with `oc media task cancel <jobId> --json`, then watch for `cancelled`. A watch timeout is not failure. Task IDs are scoped to the current service; after restart, do not rerun automatically. Use a new output path on conflicts.

4. Inspect `data.result`: `before/after.integratedLufs`, `truePeakDbtp`, sample count, duration, warnings, `presetVersion`, parameters, and filters. True peak must be ≤ -1.5 dBTP; trust measured output and warnings, not the requested target. Do not boost a silent or unmeasurable file blindly. Keep the JSON with the material.
5. Loudness-match the original, natural, and clear samples to the lowest common LUFS with linear gain. Check intelligibility, sibilance, breaths, pumping, both ends, and sync. A measured result is not listening approval.
6. Once approved, use `oc asset import` and normal semantic timeline edits to place or replace the audio. Enhancement alone does not edit the Project.

Fine-tune only where needed: `--target-lufs -16` (range -24..-9), `--denoise-db 0..12` (minimum positive value 0.01), and `--compression-ratio 1..4`. Do not pre-amplify just to compensate for the service's adaptive processing. Enhanced WAVs are tagged to prevent accidental reprocessing. Use `--allow-reprocess` only intentionally; remuxing or metadata stripping can remove the tag, so check the asset's history.

Source cleanup (`audio enhance`), timeline clip levels (`audio measure/level/volume`), and final mix loudness are different. Recheck the full mix with `audio loudness` and final export after adding music or effects. A -16 LUFS narration file is not proof of final mix loudness.
