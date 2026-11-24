# 独立人声增强

GUI 同源入口：在时间线的音频或带声音视频上右键 → 人声增强 → 自然饱满/清晰口播。
弹层可看进度和取消；完成后仅声音使用派生资产，画面、切点与音画联动保留。可撤销或右键“恢复原声”。
切换预设从原声重新派生，普通速度以外的变速/定格/倒放先恢复再处理。

手机录音、真人旁白或 TTS 需要更稳定、清楚、饱满时使用。只用包内 FFmpeg，不要求 Project、GUI、模型或云。
持续嘶声与人声重叠时使用独立降噪选项，不能靠噪声门或提高音量解决。1.1.0 起：

```sh
oc audio enhance "原声.wav" --preset none --noise-reduction standard --noise-engine fft --output "基础净化.wav" --json
oc audio enhance "原声.wav" --preset natural --noise-reduction standard --noise-engine deepfilter --output "净化并增强.wav" --json
```

- `--noise-reduction off|standard|strong` 与 `--preset none|natural|clear` 独立。显式选择会替代预设内的降噪，不叠加；不能再传 `--denoise-db`。
- `fft` 是包内基础降噪；`deepfilter` 是本地 CPU 智能人声降噪，使用完整安装包内的 OrangeCut 浮点运行时。不联网上传音频，不要求 GPU。缺少运行时明确失败，不自动退化。
- standard / strong 最大抑制参数为 12 / 24 dB，不代表每段录音实测一定下降对应分贝。优先 standard；加强后检查轻声、齿音、呼吸与尾音。
- `none` 保持音色，仍统一响度和控制峰值。`oc audio denoise` 兼容入口现在也走同一服务任务，默认 none + standard + deepfilter，输出为新的 24-bit WAV。
- 固定 DeepFilterNet3 / OrangeCut 0.5.6-orangecut.1：浮点中间处理、48 kHz / 24-bit WAV 交付，保持采样数、声道和起止位置。原始文件始终保留。旧 denoise 插件不强制升级，新请求不调用其旧适配器。
- 不指定新选项时保持原 natural/clear 的兼容行为。先查 `enhance-presets` 的实际服务版本，不能假设旧服务支持这些字段。
- GUI 录音面板可记住录后降噪与音色设置；时间线右键“人声增强 → 降噪与音色设置”。从原素材派生，可撤销、恢复原声；录音保留原始和净化版本。对比试听默认匹配响度。

先比较未增强原声，确认噪声是否来自采集链路。不要把已经净化的文件再次送入降噪；需要换参数时回到原始文件。降噪后再增强应在同一次请求完成。加入 BGM 后另做最终混音响度检查。

1. 保留原文件。先 `oc media loudness "<input>" --json` 了解电平，结合底噪与齿音选择预设。
2. `oc audio enhance-presets --json` 确认实际服务支持及版本。默认 natural：温暖、保留起伏、无降噪；
   clear：较强咬字与稳定感，附轻度 6 dB FFT 降噪。干净录音可用 clear `--denoise-db 0`。
3. 从原文件生成**新** WAV：

```sh
oc audio enhance "<input>" --preset natural --output "<new-natural.wav>" --json
oc audio enhance "<input>" --preset clear --output "<new-clear.wav>" --json
```

输出固定 48 kHz / 24-bit PCM WAV，默认保留 mono/stereo，多声道必须显式 `--channels mono|stereo`。
多音轨拒绝，先选择需要的声音。总超时默认 1800 秒，可用 `--timeout-seconds` 调整到最多 14400。
长任务用 `--no-wait`，保存 `data.jobId`，再 `oc media task watch <jobId> --json`；
取消用 `oc media task cancel <jobId> --json`，继续观察到 cancelled。watch 超时不代表任务失败。
任务 ID 仅在当前服务有效，重启后失效；不自动重跑。输出冲突必须换新文件名。

4. 检查 `data.result`：`before/after.integratedLufs`、`truePeakDbtp`、采样数和时长、warnings、
   `presetVersion`、实际 parameters 与滤镜。真峰值必须 ≤-1.5 dBTP；不达目标会告警或失败，以实测为准。
   静音/不可测失败时不要盲目加增益。保留 JSON 回执在素材旁，避免之后不知已处理过。
5. **试听匹配响度**：原声、natural、clear 以单纯线性增益调到共同较低 LUFS 再比较，避免只听到“更响”。
   检查音色、齿音、呼吸、噪声抽吸、开头与尾部、同步。未经真实试听不得宣称听感已验收。
6. 满意后 `oc asset import`，沿用原有语义时间线接口放置/替换；此命令本身不改工程。

覆盖参数仅用于有依据的微调：`--target-lufs -16`（范围 -24..-9）、`--denoise-db 0..12`
（非零最小 0.01）、`--compression-ratio 1..4`。服务会为轻声自适应计算预增益，不要先外部大幅放大。

**避免叠加**：始终由原声派生两个候选；WAV 有增强标记，默认拒绝再次增强。
`--allow-reprocess` 只用于有意重加工；改格式/去 metadata 可能丢标记，所以仍要检查素材历史。

单人声增强、Clip gain 和最终混音是三件事：`audio enhance` 整理独立源文件；
`audio measure/level/volume` 决定时间线片段间的增益；加入 BGM/音效后重新测整片并用
`audio loudness`/最终导出做混音归一化，不能认为单人声 -16 LUFS 就是最终混音响度。
