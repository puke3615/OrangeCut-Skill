# 标记保持素材原声

新建对象标注、描绘批注、箭头、目标聚焦均只提供画面效果，默认不附加提示音。
不要主动替标记配内置音效。用户需要音效时，先导入用户选择的音频，再用 timeline add 放在独立音轨，
与画面分别编辑；素材原声、解说和已有音轨保持原样。

## 清理旧版本附带的提示音

```powershell
oc sfx marker <组件clip-id> --preset none --base-revision <revision> --idempotency-key <key> --json
```

旧组件 GUI 编辑表单提供“移除已有提示音”，保存后生效。
如需临时关闭旧工程全部组件提示音，兼容命令为 `oc sfx markers --no-enabled --json`。
这些命令不影响原声和独立音频 Clip。仍须使用精确 revision/key，通过 Core Command 提交，可 undo/redo。

旧工程的 sound、typed audioCue、音效 Asset ID 和总开关继续按原样读取、渲染及导出，不在加载时静默重写。
显式的旧 sound 配置仍可复建历史工程；它不是新建标记的默认行为。
