# OrangeCut v0.1.0 · Windows x64 Agent 安装 SOP

先完整获取可信分发镜像（含本文件、manifest.json、agent-update.json、agent-install/ 和 skills/），在镜像根目录启动普通 PowerShell 5.1+。不要以管理员运行。目标固定为当前用户 LOCALAPPDATA/Programs/OrangeCut，当前 Agent 的 home 必须明确选定；默认示例为 Codex，Claude Code 改成用户自己的 .claude，其他 Agent 按自身 Skill 目录约定配置。不得卸载其他 Agent 的 Skill，不传 --adopt，不删除已有工程、授权凭据或整个用户目录。

正式下载入口：https://orangecut.timor419.com/desktop 。可信 Skill 镜像为 https://github.com/puke3615/OrangeCut-Skill ，请完整获取同一版本的 INSTALL.md、manifest.json、agent-update.json 与安装资源。桌面 ZIP 与可独立更新的 Agent 组件分别校验。404、所有链接不可达、大小/摘要错误都必须失败，不能报告“安装成功”，不能临时改成其他来源或关闭校验。

## 确定性执行

确认用户确实要安装后，运行下面完整脚本。网络受限时由用户预设 HTTPS_PROXY；海外下载显式使用 -Proxy，不依赖 PowerShell 5.1 自动识别代理环境变量。官方阿里云域名与 orangecut.timor419.com 默认直连；ORANGECUT_PROXY_ALL=1 可让这些地址也使用 HTTPS_PROXY。不把开发者本机代理地址写到用户机器。下载 ZIP 逐链接尝试，任何候选只有 sizeBytes 和 SHA256 都一致才可继续；所有候选失败则停止。清单必须来自可信镜像，SHA256 校验本身不等同发布者签名。

~~~powershell
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function Get-DownloadOptions([string]$Uri) {
    $HostName = ([uri]$Uri).DnsSafeHost
    $Direct = $HostName -ieq 'orangecut.timor419.com' -or $HostName -ieq 'orangecut-dl.auroraflow.co' -or $HostName -ieq 'aliyuncs.com' -or $HostName.EndsWith('.aliyuncs.com', [StringComparison]::OrdinalIgnoreCase)
    $Options = @{}
    if ($env:HTTPS_PROXY -and ($env:ORANGECUT_PROXY_ALL -eq '1' -or -not $Direct)) { $Options.Proxy = $env:HTTPS_PROXY }
    return $Options
}
$AgentHome = Join-Path $HOME '.codex'
$ManifestPath = Join-Path $PWD 'manifest.json'
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$Fields = @('version','buildDate','platform','zipFileName','downloadUrl','fallbackUrls','sha256','sizeBytes')
if (@(Compare-Object ($Fields | Sort-Object) ($Manifest.PSObject.Properties.Name | Sort-Object)).Count) { throw 'manifest 字段不匹配' }
if ($Manifest.platform -cne 'win-x64' -or $Manifest.version -cnotmatch '^\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?$') { throw '版本/平台不匹配' }
if ($Manifest.zipFileName -cne "OrangeCut-$($Manifest.version)-win-x64.zip") { throw 'ZIP 文件名不匹配' }
if ($Manifest.sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Manifest.sizeBytes -le 0) { throw '摘要/大小无效' }
if ($Manifest.buildDate -cnotmatch '^\d{4}-\d{2}-\d{2}$') { throw '构建日期格式无效' }
$null = [datetime]::ParseExact($Manifest.buildDate, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
if ($Manifest.fallbackUrls -isnot [array]) { throw 'fallbackUrls 必须是数组' }
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw '仅支持 Windows x64' }

function Assert-RegularPath([string]$Path) {
    $Cursor = [IO.Path]::GetFullPath($Path)
    while ($Cursor) {
        if (Test-Path -LiteralPath $Cursor) {
            if ((Get-Item -LiteralPath $Cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '拒绝重解析点' }
        }
        $Parent = Split-Path -Path $Cursor -Parent
        if ($Parent -eq $Cursor) { break }
        $Cursor = $Parent
    }
}
function Assert-DownloadUrl([string]$Value) {
    $Uri = [uri]$Value
    if (-not $Uri.IsAbsoluteUri -or $Uri.Scheme -cne 'https' -or $Uri.UserInfo -or $Uri.Query -or $Uri.Fragment) { throw '仅支持无凭据/签名的 HTTPS 链接' }
    if ([IO.Path]::GetFileName($Uri.AbsolutePath) -cne $Manifest.zipFileName) { throw '下载链接文件名不匹配' }
}
function Assert-AgentUpdate([string]$Root, $Update) {
    Assert-RegularPath $Root
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw '缺少完整 agent-install 目录' }
    $UpdateFields = @('schemaVersion','version','desktopSha256','files')
    if (@(Compare-Object ($UpdateFields | Sort-Object) ($Update.PSObject.Properties.Name | Sort-Object)).Count) { throw 'Agent 更新清单字段不匹配' }
    if ($Update.schemaVersion -cne '1' -or $Update.version -cne $Manifest.version -or $Update.desktopSha256 -cne $Manifest.sha256) { throw 'Agent 更新与桌面 ZIP 不匹配' }
    if ($Update.files -isnot [array] -or $Update.files.Count -lt 1 -or $Update.files.Count -gt 256) { throw 'Agent 更新文件数无效' }
    $Expected = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $Total = 0L
    foreach ($Entry in $Update.files) {
        $EntryFields = @('path','sha256','sizeBytes')
        if (@(Compare-Object ($EntryFields | Sort-Object) ($Entry.PSObject.Properties.Name | Sort-Object)).Count) { throw 'Agent 文件字段不匹配' }
        $Name = [string]$Entry.path
        if (@($Name.Split('/') | Where-Object { $_ -match '[. ]$|[<>"|?*\x00-\x1f]' -or $_ -match '^(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)' }).Count) { throw '拒绝 Windows 非规范 Agent 路径' }
        if (-not $Name -or $Name.Contains('\') -or $Name.Contains(':') -or [IO.Path]::IsPathRooted($Name) -or @($Name.Split('/') | Where-Object { $_ -eq '' -or $_ -eq '.' -or $_ -eq '..' }).Count -or -not $Expected.Add($Name)) { throw 'Agent 更新路径无效或重复' }
        if ($Entry.sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Entry.sizeBytes -lt 0) { throw 'Agent 更新摘要/大小无效' }
        $Total += $Entry.sizeBytes
        if ($Total -gt 16777216) { throw 'Agent 更新超过大小边界' }
        $File = Join-Path $Root $Name
        Assert-RegularPath $File
        if (-not (Test-Path -LiteralPath $File -PathType Leaf) -or (Get-Item -LiteralPath $File).Length -ne $Entry.sizeBytes -or (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Entry.sha256) { throw 'Agent 更新文件校验失败' }
    }
    $Actual = @(Get-ChildItem -LiteralPath $Root -Recurse -Force)
    foreach ($Item in $Actual) { Assert-RegularPath $Item.FullName }
    if (@($Actual | Where-Object { -not $_.PSIsContainer }).Count -ne $Expected.Count) { throw 'Agent 更新含未声明文件' }
    foreach ($Required in @('agent-install.json','run_orangecut_agent_bundle_installer.py','install_orangecut_agent_payload.py','payload/manifest.json','payload/skills/orangecut/SKILL.md')) {
        if (-not $Expected.Contains($Required)) { throw 'Agent 更新缺少官方资源' }
    }
}
function Install-AgentUpdate([string]$Source, [string]$Destination, $Update) {
    Assert-AgentUpdate $Source $Update
    Assert-RegularPath $Destination
    $Stage = $Destination + '.update-' + [guid]::NewGuid().ToString('N')
    Assert-RegularPath $Stage
    $null = New-Item -ItemType Directory -Path $Stage
    foreach ($Entry in $Update.files) {
        $Target = Join-Path $Stage $Entry.path
        $null = New-Item -ItemType Directory -Path (Split-Path $Target -Parent) -Force
        Copy-Item -LiteralPath (Join-Path $Source $Entry.path) -Destination $Target
    }
    Assert-AgentUpdate $Stage $Update
    if (Test-Path -LiteralPath $Destination) {
        $Backup = $Destination + '.backup-' + [guid]::NewGuid().ToString('N')
        [IO.Directory]::Move($Destination, $Backup)
        Write-Warning ('原 Agent 组件已保留：' + $Backup)
    }
    [IO.Directory]::Move($Stage, $Destination)
    Assert-AgentUpdate $Destination $Update
}
$InstallRoot = Join-Path $env:LOCALAPPDATA 'Programs/OrangeCut'
$ToolsRoot = Join-Path $env:LOCALAPPDATA 'Programs/OrangeCut-tools'
$Work = Join-Path $env:TEMP ('orangecut-install-' + [guid]::NewGuid().ToString('N'))
foreach ($Path in @($InstallRoot, $ToolsRoot, $Work, $AgentHome)) { Assert-RegularPath $Path }
$null = New-Item -ItemType Directory -Path $Work
$Archive = Join-Path $Work $Manifest.zipFileName
$MirrorRoot = Split-Path $ManifestPath -Parent
$UpdatePath = Join-Path $MirrorRoot 'agent-update.json'
Assert-RegularPath $UpdatePath
$AgentUpdate = Get-Content -LiteralPath $UpdatePath -Raw -Encoding UTF8 | ConvertFrom-Json
$AgentSource = Join-Path $MirrorRoot 'agent-install'
Assert-AgentUpdate $AgentSource $AgentUpdate
$Verified = $false
foreach ($Url in @($Manifest.downloadUrl) + @($Manifest.fallbackUrls)) {
    Assert-DownloadUrl $Url
    try {
        $DownloadOptions = Get-DownloadOptions $Url
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Archive -TimeoutSec 600 @DownloadOptions
        if ((Get-Item -LiteralPath $Archive).Length -ne $Manifest.sizeBytes) { throw 'ZIP 大小不匹配' }
        if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Manifest.sha256) { throw 'ZIP SHA256 不匹配' }
        $Verified = $true
        break
    } catch { Write-Warning '此候选下载失败或校验不通过，尝试已声明的下一候选' }
}
if (-not $Verified) { throw '没有通过校验的 ZIP，停止安装并检查官方链接与网络' }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip = [IO.Compression.ZipFile]::OpenRead($Archive)
$Resources = Join-Path $InstallRoot 'resources'
$ResourcesBackup = $null
$CopyStarted = $false
try {
    $Seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $InstallPrefix = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\') + '\'
    foreach ($Entry in $Zip.Entries) {
        $Name = $Entry.FullName.TrimEnd('/')
        if (-not $Name -or $Name -match '(^/|\\|:|(^|/)\.\.?(/|$)|(^|/)(\.git|\.orangecut|projects|license\.json)(/|$)|^resources\.(backup|incomplete)-|LOCAL-ACCEPTANCE)') { throw '拒绝危险 ZIP 路径' }
        if (-not $Seen.Add($Name)) { throw 'ZIP 路径重复' }
        if ((($Entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { throw 'ZIP 含符号链接' }
        $Target = [IO.Path]::GetFullPath((Join-Path $InstallRoot $Name))
        if (-not $Target.StartsWith($InstallPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'ZIP 路径越界' }
        Assert-RegularPath $Target
    }
    if (-not $Seen.Contains('OrangeCut.exe') -or -not $Seen.Contains('resources/app.asar') -or -not $Seen.Contains('resources/agent-install/run_orangecut_agent_bundle_installer.py')) { throw 'ZIP 根不是应用内容' }
    Assert-RegularPath $Resources
    if (Test-Path -LiteralPath $Resources) {
        if (-not (Test-Path -LiteralPath $Resources -PathType Container)) { throw '原 resources 不是普通目录，停止安装' }
        $BackupCandidate = Join-Path $InstallRoot ('resources.backup-' + [guid]::NewGuid().ToString('N'))
        Assert-RegularPath $BackupCandidate
        if (Test-Path -LiteralPath $BackupCandidate) { throw 'resources 备份目标已存在，停止安装' }
        [IO.Directory]::Move($Resources, $BackupCandidate)
        $ResourcesBackup = $BackupCandidate
        Write-Warning ('原 resources 已保留，恢复路径：' + $ResourcesBackup)
    }
    $CopyStarted = $true
    foreach ($Entry in $Zip.Entries) {
        $Target = Join-Path $InstallRoot $Entry.FullName
        if ($Entry.FullName.EndsWith('/')) {
            $null = New-Item -ItemType Directory -Path $Target -Force
        } else {
            $null = New-Item -ItemType Directory -Path (Split-Path $Target -Parent) -Force
            Assert-RegularPath $Target
            [IO.Compression.ZipFileExtensions]::ExtractToFile($Entry, $Target, $true)
        }
    }
} catch {
    if ($CopyStarted) {
        $Recovery = if ($ResourcesBackup) { $ResourcesBackup } else { '无旧 resources 备份（首次安装）' }
        throw ('应用文件复制失败，安装可能不完整；未继续 CLI/Skill 注册。不要启动或声称已回滚，保留现场和已验证 ZIP。旧资源恢复路径：' + $Recovery + '。原因：' + $_.Exception.Message)
    }
    throw
} finally { $Zip.Dispose() }

$Uv = $env:ORANGECUT_INSTALL_UV
if (-not $Uv) {
    $UvCommand = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
    if ($UvCommand) { $Uv = $UvCommand.Source }
}
if (-not $Uv) {
    $UvVersion = '0.9.5'
    $UvName = 'uv-x86_64-pc-windows-msvc.zip'
    $UvBase = "https://github.com/astral-sh/uv/releases/download/$UvVersion"
    $UvArchive = Join-Path $Work $UvName
    $UvChecksum = Join-Path $Work ($UvName + '.sha256')
    $DownloadOptions = Get-DownloadOptions "$UvBase/$UvName"
    Invoke-WebRequest -UseBasicParsing -Uri "$UvBase/$UvName" -OutFile $UvArchive -TimeoutSec 600 @DownloadOptions
    $DownloadOptions = Get-DownloadOptions "$UvBase/$UvName.sha256"
    Invoke-WebRequest -UseBasicParsing -Uri "$UvBase/$UvName.sha256" -OutFile $UvChecksum -TimeoutSec 60 @DownloadOptions
    $UvExpected = ((Get-Content -LiteralPath $UvChecksum -Raw).Trim() -split '\s+')[0]
    if ($UvExpected -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $UvArchive -Algorithm SHA256).Hash -ine $UvExpected) { throw 'uv 校验失败' }
    $UvStage = Join-Path $Work 'uv'
    Expand-Archive -LiteralPath $UvArchive -DestinationPath $UvStage
    $Uv = Join-Path $ToolsRoot 'uv.exe'
    Assert-RegularPath $Uv
    $null = New-Item -ItemType Directory -Path $ToolsRoot -Force
    Copy-Item -LiteralPath (Join-Path $UvStage 'uv.exe') -Destination $Uv -Force
}
Assert-RegularPath $Uv
& $Uv --version
if ($LASTEXITCODE -ne 0) { throw 'uv 自检失败' }
$Candidates = @($env:ORANGECUT_INSTALL_PYTHON)
foreach ($Name in @('python', 'python3')) {
    foreach ($Command in @(Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($Command.Source -and $Command.Source -notmatch 'WindowsApps') { $Candidates += $Command.Source }
    }
}
try {
    $ExistingPython = (& $Uv python find --no-python-downloads '>=3.10' 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -eq 0) { $Candidates += $ExistingPython }
} catch { Write-Verbose '未发现现有受管 Python，继续检查候选' }
$Python = $null
foreach ($Candidate in $Candidates) {
    if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { continue }
    Assert-RegularPath $Candidate
    $Probe = (& $Candidate -c 'import sys; sys.exit(2) if sys.version_info < (3,10) else print(sys.executable)' | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $Probe -PathType Leaf)) { $Python = $Probe; break }
}
if (-not $Python) {
    & $Uv python install 3.12.11
    if ($LASTEXITCODE -ne 0) { throw '用户态 Python 自举失败' }
    $Python = (& $Uv python find --managed-python 3.12.11 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw '找不到受管 Python' }
}
Install-AgentUpdate $AgentSource (Join-Path $InstallRoot 'resources/agent-install') $AgentUpdate
$Installer = Join-Path $InstallRoot 'resources/agent-install/run_orangecut_agent_bundle_installer.py'
$Runtime = & $Python $Installer --runtime-check --uv $Uv --python $Python | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $Runtime.ok) { throw '官方安装器 runtime-check 失败' }
$Installed = & $Python $Installer --agent-home $AgentHome --uv $Uv --python $Python --register-windows | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $Installed.ok -or -not $Installed.binDirectory) { throw '官方 CLI/Skill 注册失败' }
$env:PATH = $Installed.binDirectory + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:PATH
$Check = & $Python $Installer --check --agent-home $AgentHome --uv $Uv --python $Python | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $Check.ok) { throw '官方安装状态核验失败' }
$VersionOutput = & oc --version
if ($LASTEXITCODE -ne 0 -or ($VersionOutput | Out-String) -notmatch [regex]::Escape($Manifest.version)) { throw 'oc --version 失败或版本不匹配' }
Write-Output $VersionOutput
Write-Output '授权查询入口：oc license status --json；仅查已有服务：oc --no-autostart license status --json'
Write-Output 'CLI/Skill 安装核验完成；桌面启动和用户审片仍需另行验证'
~~~

## 异常与升级

- 桌面 ZIP 可以保持原字节；统一 Skill/CLI 的更新在完整镜像的 agent-install/，agent-update.json 将版本和每个文件的大小/SHA256 绑定到该 ZIP。执行任何更新组件的 Python 之前先验证整棵文件树；只复制已经声明的文件到新目录，再次核验后替换应用内资源。旧组件单独保留为 agent-install.backup-随机标识，不合并旧 wheel、不删除备份。缺件、额外文件、摘要不符或桌面摘要不匹配都停止；不得跳过这一组件而声称已安装版本感知 Skill。此覆盖步骤不承诺断电原子回滚。
- 官方参数为 --runtime-check、--agent-home、--uv、--python、--check，并在安装调用显式传 --register-windows 进行用户 PATH 与桌面快捷方式注册。普通无 flag 调用依然不做这两项。包内 launcher 若不认识该 flag 就停止，负责人必须重建新版 Agent 资源，不能悄悄省略。官方注册器验证 Python >=3.10 与 uv，通过已有事务安装本地 wheel；不需要 --install / --add-path / --create-shortcut。
- 优先探测本机 PATH 及 Agent 提供的可执行路径 ORANGECUT_INSTALL_UV / ORANGECUT_INSTALL_PYTHON，并实跑版本检查，不默认已安装。uv 缺失时仅从官方固定版本 Releases 获取独立二进制及对应 SHA256；没有可达官方源就停止。Python 缺失时使用 uv 的受管下载与校验机制安装固定 3.12.11，随后官方 --runtime-check 再验证可执行文件与版本。不要求管理员或预装 Python，不承诺运行包自带 Python。
- bootstrap 来源信任依赖官方 HTTPS，与应用 ZIP 的发布清单校验分别处理；不得从未声明镜像兜底。Get-DownloadOptions 按 URL 主机选择代理：海外使用 HTTPS_PROXY，官方国内地址默认直连，ORANGECUT_PROXY_ALL=1 强制使用已配置代理；uv 的受管 Python 下载仍遵循 uv 自己的代理机制。脚本只刷新当前进程 PATH，用户 PATH 与快捷方式由显式 --register-windows 负责，不调用 GUI 向导，不使用 setx 截断 PATH，不写系统 PATH。已有不受管同名 CLI/Skill 时保留冲突，不自动 --adopt 或卸载。
- 升级前必须正常关闭旧 OrangeCut。ZIP 大小、摘要和全部路径检查通过后，仅将保留给应用的旧 InstallRoot/resources 同卷重命名到 InstallRoot/resources.backup-随机标识，再复制 ZIP 声明的应用文件；禁止合并旧资源，否则旧版 wheel 或过时 runtime 文件会使严格清单校验失败。首次安装不创建旧资源备份；备份重命名失败就停止，不复制应用文件。
- 不清空安装目录、不递归删除备份、不删除 APPDATA/LOCALAPPDATA 的其他内容、不修改工程或凭据库。每次升级的旧 resources 均保留，脚本打印其确切绝对路径；正常升级后也不自动删除。遇到文件占用/磁盘错误停止，不擅自结束用户进程。此文件复制步骤不承诺原子回滚，CLI/Skill 事务由官方注册器处理。
- 复制中断时，新 resources 和顶层 EXE/DLL 都可能不完整，脚本失败退出且不继续 CLI/Skill 注册。不要启动应用或只恢复 resources 就声称回滚完成。保留已打印的 resources.backup-路径、现场和已验证 ZIP；关闭应用后可重新执行完整脚本，残留 resources 会另存为新的独立备份。若需回退，先同卷重命名残留 resources 到新的 resources.incomplete-随机标识，再将选定的原 resources.backup-目录改名为 resources，并从与该备份版本对应、重新校验过的旧 ZIP 恢复顶层应用文件；没有匹配旧 ZIP 时停止并请求人工恢复，不合并资源、不删除现场。
- Work 是此次唯一新建的临时下载目录，成功或失败后可核对它的绝对路径，再单独删除此目录。不要执行对整个 TEMP、LOCALAPPDATA、Programs、Agent home 或用户目录的递归清理。
- 本地开发测试只运行隔离 fixture，把 TEMP/TMP 和所有安装相关路径改为 repo target 内，不执行本文真实用户目录安装链路。单测通过不替代真实下载安装、升级恢复与桌面审片验收。

参考：uv 官方安装文档 https://docs.astral.sh/uv/getting-started/installation/ 与用户态 Python 文档 https://docs.astral.sh/uv/guides/install-python/ 。版本号固定是为了可复现，不代表最新版本；更新 bootstrap 版本应重新验收。
