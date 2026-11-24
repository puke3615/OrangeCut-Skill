#!/usr/bin/env python3
"""Validate signed Agent bundle resources and invoke the managed installer."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Any


SCHEMA_VERSION = "1"
RESOURCE_SCHEMA_ID = "https://schemas.orangecut.dev/distribution/v1/agent-install.schema.json"
RESOURCE_MANIFEST = "agent-install.json"
PAYLOAD_DIRECTORY = "payload"
INSTALLER_FILE = "install_orangecut_agent_payload.py"
LAUNCHER_FILE = "run_orangecut_agent_bundle_installer.py"
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SCRIPT_BYTES = 2 * 1024 * 1024
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
UV_VERSION_PATTERN = re.compile(r"uv ([0-9]+\.[0-9]+\.[0-9]+)(?: .*)?")


class ResourceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def emit_error(error: ResourceError, **details: Any) -> None:
    print(
        json.dumps(
            {
                "schemaVersion": SCHEMA_VERSION,
                "ok": False,
                "status": "failed",
                "code": error.code,
                "message": error.message,
                **details,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return True
    if stat.S_ISLNK(metadata.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def require_directory(path: Path, label: str) -> None:
    if is_link_or_reparse(path) or not path.is_dir():
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} is not a regular directory"
        )


def read_bounded_file(path: Path, limit: int, label: str) -> bytes:
    if is_link_or_reparse(path):
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} is not a regular file"
        )
    try:
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ResourceError(
                "AGENT_RESOURCE_INVALID", f"the {label} is not a bounded regular file"
            )
        with path.open("rb") as source:
            content = source.read(limit + 1)
    except ResourceError:
        raise
    except OSError as error:
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} could not be read"
        ) from error
    if len(content) > limit:
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} exceeds its size limit"
        )
    return content


def sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def require_exact_object(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} has an unexpected shape"
        )
    return value


def validate_file_entry(
    value: object, expected_path: str, root: Path, label: str
) -> Path:
    entry = require_exact_object(value, {"path", "sha256"}, label)
    if entry["path"] != expected_path or not isinstance(entry["sha256"], str):
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} has an unexpected contract"
        )
    if SHA256_PATTERN.fullmatch(entry["sha256"]) is None:
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", f"the {label} digest is invalid"
        )
    path = root / expected_path
    content = read_bounded_file(path, MAX_SCRIPT_BYTES, label)
    if sha256_bytes(content) != entry["sha256"]:
        raise ResourceError(
            "AGENT_RESOURCE_TAMPERED", f"the {label} does not match the signed digest"
        )
    return path


def validate_resources(root: Path) -> tuple[Path, Path, str]:
    require_directory(root, "Agent resource root")
    raw_manifest = read_bounded_file(
        root / RESOURCE_MANIFEST, MAX_MANIFEST_BYTES, "Agent resource manifest"
    )
    try:
        manifest_value = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", "the Agent resource manifest is not valid JSON"
        ) from error
    manifest = require_exact_object(
        manifest_value,
        {"$schema", "schemaVersion", "product", "launcher", "installer", "payload"},
        "Agent resource manifest",
    )
    if (
        manifest["$schema"] != RESOURCE_SCHEMA_ID
        or manifest["schemaVersion"] != SCHEMA_VERSION
    ):
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", "the Agent resource schema is unsupported"
        )
    product = require_exact_object(manifest["product"], {"name", "version"}, "product")
    if (
        product["name"] != "OrangeCut"
        or not isinstance(product["version"], str)
        or not product["version"]
    ):
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", "the Agent resource product identity is invalid"
        )
    launcher = validate_file_entry(
        manifest["launcher"], LAUNCHER_FILE, root, "Agent resource launcher"
    )
    running_launcher = Path(os.path.abspath(Path(__file__)))
    running_digest = sha256_bytes(
        read_bounded_file(running_launcher, MAX_SCRIPT_BYTES, "running launcher")
    )
    resource_digest = sha256_bytes(
        read_bounded_file(launcher, MAX_SCRIPT_BYTES, "Agent resource launcher")
    )
    if running_digest != resource_digest:
        raise ResourceError(
            "AGENT_RESOURCE_TAMPERED", "the running launcher is not the signed resource launcher"
        )
    installer = validate_file_entry(
        manifest["installer"], INSTALLER_FILE, root, "Agent resource installer"
    )
    payload = require_exact_object(manifest["payload"], {"path", "sha256"}, "payload")
    if (
        payload["path"] != PAYLOAD_DIRECTORY
        or not isinstance(payload["sha256"], str)
        or SHA256_PATTERN.fullmatch(payload["sha256"]) is None
    ):
        raise ResourceError(
            "AGENT_RESOURCE_INVALID", "the Agent payload resource contract is invalid"
        )
    payload_path = root / PAYLOAD_DIRECTORY
    require_directory(payload_path, "Agent payload")
    return installer, payload_path, payload["sha256"]


def resolve_command(value: str | None, name: str, code: str) -> str:
    resolved = shutil.which(value or name)
    if resolved is None:
        raise ResourceError(code, f"a supported {name} executable is required")
    return os.path.abspath(resolved)


def probe_python(value: str | None) -> tuple[str, str]:
    python = resolve_command(value or sys.executable, "Python", "PYTHON_UNAVAILABLE")
    try:
        completed = subprocess.run(
            [
                python,
                "-c",
                "import json,sys; print(json.dumps(list(sys.version_info[:3])))",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_value = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise ResourceError(
            "PYTHON_UNAVAILABLE", "the selected Python executable could not be verified"
        ) from error
    if (
        completed.returncode != 0
        or not isinstance(version_value, list)
        or len(version_value) != 3
        or any(isinstance(part, bool) or not isinstance(part, int) for part in version_value)
    ):
        raise ResourceError(
            "PYTHON_UNAVAILABLE", "the selected Python executable could not be verified"
        )
    version = tuple(version_value)
    if version < (3, 10, 0):
        raise ResourceError(
            "PYTHON_UNSUPPORTED", "OrangeCut Agent tools require Python 3.10 or newer"
        )
    return python, ".".join(str(part) for part in version)


def probe_uv(value: str | None) -> tuple[str, str]:
    uv = resolve_command(value, "uv", "UV_UNAVAILABLE")
    try:
        completed = subprocess.run(
            [uv, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ResourceError(
            "UV_UNAVAILABLE", "the selected uv executable could not be verified"
        ) from error
    match = UV_VERSION_PATTERN.fullmatch(completed.stdout.strip())
    if completed.returncode != 0 or match is None:
        raise ResourceError(
            "UV_UNAVAILABLE", "the selected uv executable could not be verified"
        )
    return uv, match.group(1)


def emit_runtime_ready(
    python: str, python_version: str, uv: str, uv_version: str
) -> None:
    print(
        json.dumps(
            {
                "schemaVersion": SCHEMA_VERSION,
                "ok": True,
                "status": "runtime_ready",
                "pythonExecutable": python,
                "pythonVersion": python_version,
                "uvExecutable": uv,
                "uvVersion": uv_version,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def validate_registration_path(path: Path, *, directory: bool) -> None:
    if not path.is_absolute() or any(is_link_or_reparse(parent) for parent in path.parents):
        raise ResourceError("WINDOWS_REGISTRATION_UNSAFE", "a registration path has an unsafe parent")
    if is_link_or_reparse(path) or (not path.is_dir() if directory else not path.is_file()):
        raise ResourceError("WINDOWS_REGISTRATION_UNSAFE", "a registration path is not a regular file or directory")


def user_path_value(registry: Any, key: Any) -> tuple[str, int]:
    try:
        value, kind = registry.QueryValueEx(key, "Path")
    except FileNotFoundError:
        return "", registry.REG_EXPAND_SZ
    if kind not in (registry.REG_SZ, registry.REG_EXPAND_SZ) or not isinstance(value, str) or "\0" in value:
        raise ResourceError("WINDOWS_REGISTRATION_UNSAFE", "the current user PATH has an unsupported registry value")
    return value, kind


def append_user_path(registry: Any, bin_directory: Path) -> bool:
    with registry.CreateKeyEx(
        registry.HKEY_CURRENT_USER, "Environment", 0,
        registry.KEY_QUERY_VALUE | registry.KEY_SET_VALUE,
    ) as key:
        original, kind = user_path_value(registry, key)
        target = ntpath.normcase(ntpath.normpath(str(bin_directory)))
        for entry in original.split(";"):
            candidate = entry.strip().strip('"')
            if kind == registry.REG_EXPAND_SZ:
                candidate = registry.ExpandEnvironmentStrings(candidate)
            if candidate and ntpath.normcase(ntpath.normpath(candidate)) == target:
                return False
        separator = "" if not original or original.endswith(";") else ";"
        registry.SetValueEx(key, "Path", 0, kind, original + separator + str(bin_directory))
    return True


def create_windows_shortcuts(powershell: Path, executable: Path, shortcuts: list[Path]) -> None:
    script = r"""
$ErrorActionPreference = 'Stop'
$configuration = $env:ORANGECUT_WINDOWS_REGISTRATION | ConvertFrom-Json
foreach ($path in @($configuration.executable) + @($configuration.shortcuts)) {
    $cursor = $path
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Unsafe registration path' }
        } elseif ($cursor -ne $path) { throw 'Missing registration directory' }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
}
$shell = New-Object -ComObject WScript.Shell
foreach ($path in $configuration.shortcuts) {
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $configuration.executable
    $shortcut.WorkingDirectory = [IO.Path]::GetDirectoryName($configuration.executable)
    $shortcut.IconLocation = $configuration.executable + ',0'
    $shortcut.Description = 'OrangeCut'
    $shortcut.Save()
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Shortcut was not created' }
}
@{ok=$true} | ConvertTo-Json -Compress
"""
    environment = dict(os.environ)
    environment["ORANGECUT_WINDOWS_REGISTRATION"] = json.dumps(
        {"executable": str(executable), "shortcuts": [str(path) for path in shortcuts]}
    )
    completed = subprocess.run(
        [str(powershell), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand",
         base64.b64encode(script.encode("utf-16le")).decode("ascii")],
        check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30, env=environment,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    )
    try:
        response = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise ResourceError("WINDOWS_REGISTRATION_FAILED", "current user shortcuts could not be created") from error
    if completed.returncode != 0 or not isinstance(response, dict) or set(response) != {"ok"} or response["ok"] is not True:
        raise ResourceError("WINDOWS_REGISTRATION_FAILED", "current user shortcuts could not be created")


def broadcast_environment_change(powershell: Path) -> dict[str, Any]:
    script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class OrangeCutEnvironmentNotification {
    [DllImport("user32.dll", CharSet = CharSet.Unicode, ExactSpelling = true, SetLastError = true)]
    public static extern IntPtr SendMessageTimeoutW(IntPtr window, uint message, UIntPtr parameter, string value, uint flags, uint timeout, out UIntPtr result);
}
'@
$Result = [UIntPtr]::Zero
$Sent = [OrangeCutEnvironmentNotification]::SendMessageTimeoutW([IntPtr]0xffff, 0x001a, [UIntPtr]::Zero, 'Environment', 0x0022, 1000, [ref]$Result)
@{ok=($Sent -ne [IntPtr]::Zero); win32Error=[Runtime.InteropServices.Marshal]::GetLastWin32Error()} | ConvertTo-Json -Compress
"""
    warning = {
        "status": "warning", "code": "WINDOWS_ENVIRONMENT_NOTIFICATION_FAILED",
        "message": "User PATH and shortcuts are registered, but environment notification was not confirmed; restart affected applications or sign out and back in if PATH remains stale",
    }
    try:
        completed = subprocess.run(
            [str(powershell), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand",
             base64.b64encode(script.encode("utf-16le")).decode("ascii")],
            check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except subprocess.TimeoutExpired:
        return {**warning, "reason": "timeout"}
    except OSError:
        return {**warning, "reason": "unavailable"}
    try:
        response = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError):
        return {**warning, "reason": "invalid_response"}
    if not isinstance(response, dict) or set(response) != {"ok", "win32Error"} \
            or type(response["ok"]) is not bool or type(response["win32Error"]) is not int \
            or not 0 <= response["win32Error"] <= 0xffffffff:
        return {**warning, "reason": "invalid_response"}
    if completed.returncode != 0:
        return {**warning, "reason": "process_failed"}
    if not response["ok"]:
        return {**warning, "reason": "win32_error", "win32Error": response["win32Error"]}
    return {"status": "broadcast"}


def register_windows(root: Path, uv: str, result: dict[str, Any]) -> dict[str, Any]:
    if sys.platform != "win32":
        raise ResourceError("WINDOWS_REGISTRATION_UNSUPPORTED", "--register-windows requires Windows")
    import winreg

    if root.name != "agent-install" or root.parent.name != "resources":
        raise ResourceError("WINDOWS_REGISTRATION_UNSAFE", "Windows registration requires the packaged resource layout")
    validate_registration_path(root, directory=True)
    executable = root.parent.parent / "OrangeCut.exe"
    validate_registration_path(executable, directory=False)
    bin_value = result.get("binDirectory")
    if not isinstance(bin_value, str) or not bin_value or any(char in bin_value for char in ';\r\n\0"'):
        raise ResourceError("AGENT_INSTALL_RESULT_INVALID", "the installer did not report a safe UV bin directory")
    bin_directory = Path(bin_value)
    validate_registration_path(bin_directory, directory=True)
    completed = subprocess.run(
        [uv, "tool", "dir", "--bin", "--no-config", "--no-progress"],
        check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    )
    if completed.returncode != 0 or ntpath.normcase(ntpath.normpath(completed.stdout.strip())) != ntpath.normcase(ntpath.normpath(bin_value)):
        raise ResourceError("AGENT_INSTALL_RESULT_INVALID", "the installer bin directory does not match the verified UV runtime")
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    validate_registration_path(powershell, directory=False)
    shortcuts = []
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        0, winreg.KEY_QUERY_VALUE,
    ) as key:
        for name in ("Desktop", "Programs"):
            value, kind = winreg.QueryValueEx(key, name)
            if not isinstance(value, str) or kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) or not value or "\0" in value:
                raise ResourceError("WINDOWS_REGISTRATION_UNSAFE", "a current user shortcut folder is invalid")
            directory = Path(winreg.ExpandEnvironmentStrings(value) if kind == winreg.REG_EXPAND_SZ else value)
            validate_registration_path(directory, directory=True)
            shortcut = directory / "OrangeCut.lnk"
            if os.path.lexists(shortcut):
                validate_registration_path(shortcut, directory=False)
            shortcuts.append(shortcut)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_QUERY_VALUE) as key:
            user_path_value(winreg, key)
    except FileNotFoundError:
        pass
    create_windows_shortcuts(powershell, executable, shortcuts)
    changed = append_user_path(winreg, bin_directory)
    notification = broadcast_environment_change(powershell)
    return {"status": "registered", "pathChanged": changed,
            "shortcuts": [str(path) for path in shortcuts], "newTerminalRequired": changed,
            "environmentNotification": notification}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-root", type=Path)
    parser.add_argument(
        "--agent-home",
        type=Path,
        help="the Agent home to install into, e.g. ~/.claude or ~/.codex",
    )
    parser.add_argument("--codex-home", type=Path, help="deprecated alias for --agent-home")
    parser.add_argument("--uv")
    parser.add_argument("--python")
    parser.add_argument(
        "--register-windows", action="store_true",
        help="after installation, register the UV bin directory and OrangeCut shortcuts for the current Windows user",
    )
    parser.add_argument(
        "--adopt",
        action="store_true",
        help="take over an existing unmanaged orangecut-cli UV tool in place",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--runtime-check", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--uninstall", action="store_true")
    arguments = parser.parse_args()
    root = Path(
        os.path.abspath(
            (arguments.resource_root or Path(__file__).parent).expanduser()
        )
    )
    try:
        installer, payload, expected_sha256 = validate_resources(root)
        python, python_version = probe_python(arguments.python)
        uv, uv_version = probe_uv(arguments.uv)
        if arguments.runtime_check:
            emit_runtime_ready(python, python_version, uv, uv_version)
            return 0
        arguments.agent_home = arguments.agent_home or arguments.codex_home
        if arguments.agent_home is None:
            raise ResourceError(
                "AGENT_HOME_REQUIRED", "name the Agent home to install into with --agent-home"
            )
    except ResourceError as error:
        emit_error(error)
        return 2

    command = [
        sys.executable,
        str(installer),
        "--payload",
        str(payload),
        "--expected-sha256",
        expected_sha256,
        "--agent-home",
        str(arguments.agent_home),
        "--uv",
        uv,
        "--python",
        python,
    ]
    if arguments.check:
        command.append("--check")
    elif arguments.uninstall:
        command.append("--uninstall")
    elif arguments.adopt:
        command.append("--adopt")
    registration_requested = arguments.register_windows and not arguments.check and not arguments.uninstall
    try:
        if registration_requested:
            completed = subprocess.run(
                command, check=False, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=600,
                **({"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}),
            )
        else:
            completed = subprocess.run(command, check=False)
    except (OSError, subprocess.TimeoutExpired):
        emit_error(
            ResourceError(
                "AGENT_INSTALLER_UNAVAILABLE", "the signed Agent installer could not be started"
            )
        )
        return 2
    if registration_requested:
        installation_status = None
        try:
            try:
                result = json.loads(completed.stdout)
            except (TypeError, json.JSONDecodeError) as error:
                raise ResourceError("AGENT_INSTALL_RESULT_INVALID", "the signed installer did not return a JSON result") from error
            if not isinstance(result, dict) or result.get("schemaVersion") != SCHEMA_VERSION:
                raise ResourceError("AGENT_INSTALL_RESULT_INVALID", "the signed installer returned an invalid result")
            if completed.returncode != 0:
                if result.get("ok") is not False or result.get("status") != "failed":
                    raise ResourceError("AGENT_INSTALL_RESULT_INVALID", "the signed installer failed without a failure result")
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
                return completed.returncode
            if result.get("ok") is not True or result.get("status") not in ("installed", "already_ready", "adopted"):
                raise ResourceError("AGENT_INSTALL_RESULT_INVALID", "the signed installer did not confirm installation")
            installation_status = result["status"]
            result["windowsRegistration"] = register_windows(root, uv, result)
        except (ResourceError, OSError, subprocess.TimeoutExpired) as error:
            failure = error if isinstance(error, ResourceError) else ResourceError(
                "WINDOWS_REGISTRATION_FAILED", "current user Windows registration did not complete; installed Agent tools are retained"
            )
            details = {"installationStatus": installation_status, "registrationStatus": "failed"} if installation_status else {}
            emit_error(failure, **details)
            return 2
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
