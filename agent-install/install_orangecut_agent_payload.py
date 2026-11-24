#!/usr/bin/env python3
"""Install a verified OrangeCut Agent payload into explicit user-scoped roots."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from typing import Any, Callable, Iterator
import uuid
import zipfile


SCHEMA_VERSION = "1"
PRODUCT_NAME = "OrangeCut"
SKILL_NAME = "orangecut"
CLI_PACKAGE = "orangecut-cli"
COMMANDS = ("oc", "orangecut")
SKILL_MARKER = ".orangecut-product.json"
STATE_DIRECTORY = ".orangecut-agent-v1"
INSTALL_RECORD = "install.json"
INSTALL_LOCK = ".orangecut-agent.lock"
INSTALL_TRANSACTION = ".orangecut-agent-transaction.json"
MANAGED_BY = "OrangeCut Agent Installer"
MAX_JSON_BYTES = 64 * 1024
MAX_SKILL_BYTES = 2 * 1024 * 1024
MAX_WHEEL_BYTES = 8 * 1024 * 1024
MAX_PAYLOAD_BYTES = MAX_JSON_BYTES + MAX_SKILL_BYTES + MAX_WHEEL_BYTES
MAX_WHEEL_FILES = 64
MAX_COMMAND_BYTES = 2 * 1024 * 1024
MAX_DIRECTORY_ENTRIES = 128
MAX_DIRECTORY_DEPTH = 16
WINDOWS_REPARSE_POINT = 0x400
_ACTIVE_INSTALL_LOCK_DESCRIPTOR: int | None = None


def is_product_managed(value: object) -> bool:
    return value == MANAGED_BY


class InstallError(RuntimeError):
    def __init__(self, code: str, message: str, remediation: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.remediation = remediation


@contextmanager
def installation_lock(agent_home: Path) -> Iterator[None]:
    global _ACTIVE_INSTALL_LOCK_DESCRIPTOR
    lock_path = agent_home / INSTALL_LOCK
    if path_is_link(lock_path):
        raise InstallError("INSTALL_LOCK_UNSAFE", "the Agent installer lock is redirected")
    flags = os.O_CREAT | os.O_RDWR
    for flag_name in ("O_BINARY", "O_CLOEXEC", "O_NOFOLLOW"):
        flags |= getattr(os, flag_name, 0)
    descriptor: int | None = None
    acquired = False
    windows_lock = None
    unix_lock = None
    try:
        try:
            descriptor = os.open(lock_path, flags, 0o600)
            metadata = os.fstat(descriptor)
        except OSError as error:
            raise InstallError(
                "INSTALL_LOCK_UNAVAILABLE", "the Agent installer lock cannot be opened"
            ) from error
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise InstallError("INSTALL_LOCK_UNSAFE", "the Agent installer lock is not regular")
        try:
            if os.name == "nt":
                import msvcrt

                windows_lock = msvcrt
                if metadata.st_size == 0:
                    os.write(descriptor, b"\0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                unix_lock = fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise InstallError(
                    "INSTALL_BUSY",
                    "another OrangeCut Agent installer operation is already running",
                    "wait for the other install, update, check, or uninstall to finish and retry",
                ) from error
            raise InstallError(
                "INSTALL_LOCK_UNAVAILABLE", "the Agent installer lock cannot be acquired"
            ) from error
        _ACTIVE_INSTALL_LOCK_DESCRIPTOR = descriptor
        yield
    finally:
        if descriptor is not None:
            if _ACTIVE_INSTALL_LOCK_DESCRIPTOR == descriptor:
                _ACTIVE_INSTALL_LOCK_DESCRIPTOR = None
            if acquired:
                try:
                    if windows_lock is not None:
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        windows_lock.locking(descriptor, windows_lock.LK_UNLCK, 1)
                    elif unix_lock is not None:
                        unix_lock.flock(descriptor, unix_lock.LOCK_UN)
                except OSError:
                    pass
            os.close(descriptor)


def emit(ok: bool, status: str, **details: object) -> None:
    print(
        json.dumps(
            {"schemaVersion": SCHEMA_VERSION, "ok": ok, "status": status, **details},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def path_is_link(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(
        getattr(metadata, "st_file_attributes", 0) & WINDOWS_REPARSE_POINT
    )


def sync_regular_file(path: Path) -> None:
    # Windows flushes through `_commit`, which needs a writable handle: a
    # read-only descriptor fails the flush outright with EBADF, after the copy
    # and its digest check have both already passed. Every file reaching here
    # was just written by this installer, so it is ours to open for writing.
    flags = os.O_RDWR if os.name == "nt" else os.O_RDONLY
    for flag_name in ("O_BINARY", "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK"):
        flags |= getattr(os, flag_name, 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise InstallError("FILE_UNSAFE", "an installer file is not regular")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sync_directory(path: Path) -> None:
    if os.name == "nt":
        # Directory FlushFileBuffers needs a Windows backup-semantics handle;
        # retain that as an explicit real-runner Gate instead of pretending a
        # normal Python directory descriptor provides the same guarantee.
        return
    flags = os.O_RDONLY
    for flag_name in ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW"):
        flags |= getattr(os, flag_name, 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise InstallError("DIRECTORY_UNSAFE", "an installer directory is not regular")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_replace(source: Path, destination: Path) -> None:
    source_parent = source.parent
    destination_parent = destination.parent
    os.replace(source, destination)
    sync_directory(destination_parent)
    if source_parent != destination_parent:
        sync_directory(source_parent)


def sync_tree(root: Path) -> None:
    files = regular_files(root)
    for path in files:
        sync_regular_file(path)
    directories = {root, *(path.parent for path in files)}
    for directory in sorted(
        directories,
        key=lambda path: len(path.relative_to(root).parts),
        reverse=True,
    ):
        sync_directory(directory)


def read_regular_bytes(path: Path, maximum: int) -> bytes:
    try:
        metadata = path.lstat()
        if path_is_link(path) or not stat.S_ISREG(metadata.st_mode):
            raise InstallError("FILE_UNSAFE", "a required installer file is not regular")
        flags = os.O_RDONLY
        for flag_name in ("O_BINARY", "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK"):
            flags |= getattr(os, flag_name, 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise InstallError("FILE_UNSAFE", "a required installer file is not regular")
            content = source.read(maximum + 1)
    except InstallError:
        raise
    except OSError as error:
        raise InstallError("FILE_UNREADABLE", "a required installer file cannot be read") from error
    if len(content) > maximum:
        raise InstallError("FILE_TOO_LARGE", "a required installer file is too large")
    return content


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(read_regular_bytes(path, MAX_JSON_BYTES).decode("utf-8"))
    except InstallError:
        raise
    except (UnicodeError, json.JSONDecodeError) as error:
        raise InstallError("JSON_INVALID", "a required installer JSON file is invalid") from error
    if not isinstance(payload, dict):
        raise InstallError("JSON_INVALID", "a required installer JSON value is not an object")
    return payload


def regular_files(root: Path) -> list[Path]:
    if path_is_link(root) or not root.is_dir():
        raise InstallError("DIRECTORY_UNSAFE", "an installer directory is not regular")
    files: list[Path] = []
    directories = [root]
    entry_count = 0
    while directories:
        directory = directories.pop()
        try:
            with os.scandir(directory) as scanned:
                entries = sorted(scanned, key=lambda entry: entry.name)
        except OSError as error:
            raise InstallError(
                "DIRECTORY_UNREADABLE", "an installer directory cannot be read"
            ) from error
        for entry in entries:
            entry_count += 1
            if entry_count > MAX_DIRECTORY_ENTRIES:
                raise InstallError(
                    "DIRECTORY_TOO_LARGE", "an installer directory contains too many entries"
                )
            path = Path(entry.path)
            if path_is_link(path):
                raise InstallError("DIRECTORY_UNSAFE", "an installer directory contains a link")
            try:
                if entry.is_file(follow_symlinks=False):
                    files.append(path)
                elif entry.is_dir(follow_symlinks=False):
                    if len(path.relative_to(root).parts) > MAX_DIRECTORY_DEPTH:
                        raise InstallError(
                            "DIRECTORY_TOO_DEEP",
                            "an installer directory exceeds its nesting limit",
                        )
                    directories.append(path)
                else:
                    raise InstallError(
                        "DIRECTORY_UNSAFE",
                        "an installer directory contains a special file",
                    )
            except OSError as error:
                raise InstallError(
                    "DIRECTORY_UNREADABLE", "an installer directory entry cannot be read"
                ) from error
    # Ordered by the relative POSIX path, never by `Path`. `WindowsPath`
    # compares case-folded, so `SKILL.md` sorts last on Windows and first
    # everywhere else -- and `tree_digest` hashes in this order, which made the
    # same payload hash differently on the two platforms and the manifest file
    # list unmatchable on one of them.
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def sha256_file(path: Path, maximum: int = MAX_PAYLOAD_BYTES) -> str:
    digest = hashlib.sha256()
    try:
        metadata = path.lstat()
        if path_is_link(path) or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise InstallError("FILE_UNSAFE", "a payload file is not bounded and regular")
        flags = os.O_RDONLY
        for flag_name in ("O_BINARY", "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK"):
            flags |= getattr(os, flag_name, 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > maximum:
                raise InstallError("FILE_UNSAFE", "a payload file is not bounded and regular")
            size = 0
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > maximum:
                    raise InstallError("FILE_TOO_LARGE", "a payload file exceeds its size limit")
                digest.update(chunk)
    except InstallError:
        raise
    except OSError as error:
        raise InstallError("FILE_UNREADABLE", "a payload file cannot be hashed") from error
    return f"sha256:{digest.hexdigest()}"


def tree_digest(
    root: Path,
    *,
    ignored: set[str] | None = None,
    maximum: int = MAX_PAYLOAD_BYTES,
) -> str:
    ignored = ignored or set()
    digest = hashlib.sha256()
    size = 0
    for path in regular_files(root):
        relative = path.relative_to(root).as_posix()
        if relative in ignored:
            continue
        body = read_regular_bytes(path, maximum - size)
        size += len(body)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(body)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def require_keys(payload: dict[str, Any], expected: set[str], label: str) -> None:
    if set(payload) != expected:
        raise InstallError("MANIFEST_INVALID", f"{label} has an unexpected shape")


def require_text(payload: dict[str, Any], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise InstallError("MANIFEST_INVALID", f"{label}.{key} must be text")
    return value


def safe_relative(value: str) -> PurePosixPath:
    if "\\" in value or ":" in value or "\0" in value:
        raise InstallError("MANIFEST_INVALID", "a payload relative path is unsafe")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise InstallError("MANIFEST_INVALID", "a payload relative path is unsafe")
    return path


def payload_path(root: Path, relative: str) -> Path:
    safe = safe_relative(relative)
    return root.joinpath(*safe.parts)


def validate_skill_file(relative: str) -> None:
    path = safe_relative(relative)
    if relative == "SKILL.md":
        return
    if path.parts[0] == "agents" and len(path.parts) == 2 and path.suffix in {".yaml", ".yml"}:
        return
    # References may sit one folder deep -- `references/scenarios/<name>.md` --
    # and no deeper. Flat was the original rule and the scenario library
    # outgrew it; a bounded depth keeps the layout readable without letting a
    # manifest describe an arbitrary tree.
    if (
        path.parts[0] == "references"
        and len(path.parts) in (2, 3)
        and path.suffix == ".md"
    ):
        return
    raise InstallError("MANIFEST_INVALID", "the Agent payload Skill file type is invalid")


def verify_wheel(wheel: Path, version: str) -> None:
    sha256_file(wheel, MAX_WHEEL_BYTES)
    expected_dist_info = f"orangecut_cli-{version}.dist-info"
    try:
        with zipfile.ZipFile(wheel) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_WHEEL_FILES:
                raise InstallError("PAYLOAD_INVALID", "the oc wheel file count is invalid")
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise InstallError("PAYLOAD_INVALID", "the oc wheel contains duplicate entries")
            if sum(entry.file_size for entry in entries) > MAX_WHEEL_BYTES:
                raise InstallError("PAYLOAD_INVALID", "the oc wheel expands beyond its size limit")
            for entry in entries:
                try:
                    relative = safe_relative(entry.filename)
                except InstallError as error:
                    raise InstallError(
                        "PAYLOAD_INVALID", "the oc wheel contains an unsafe entry"
                    ) from error
                unix_type = (entry.external_attr >> 16) & 0o170000
                if (
                    entry.is_dir()
                    or entry.flag_bits & 0x1
                    or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or unix_type not in (0, stat.S_IFREG)
                ):
                    raise InstallError("PAYLOAD_INVALID", "the oc wheel contains an unsafe entry")
                if relative.parts[0] == "orangecut_cli":
                    if relative.suffix != ".py" and relative.as_posix() != "orangecut_cli/html-presets.json":
                        raise InstallError("PAYLOAD_INVALID", "the oc wheel package content is invalid")
                elif relative.parts[0] == expected_dist_info:
                    if relative.name not in {
                        "METADATA",
                        "WHEEL",
                        "entry_points.txt",
                        "top_level.txt",
                        "RECORD",
                    }:
                        raise InstallError("PAYLOAD_INVALID", "the oc wheel metadata content is invalid")
                else:
                    raise InstallError("PAYLOAD_INVALID", "the oc wheel contains an unexpected package")
            metadata_files = [
                entry.filename
                for entry in entries
                if entry.filename.endswith(".dist-info/METADATA")
            ]
            entry_point_files = [
                entry.filename
                for entry in entries
                if entry.filename.endswith(".dist-info/entry_points.txt")
            ]
            if metadata_files != [f"{expected_dist_info}/METADATA"] or entry_point_files != [
                f"{expected_dist_info}/entry_points.txt"
            ]:
                raise InstallError("PAYLOAD_INVALID", "the oc wheel metadata is incomplete")
            if not {"orangecut_cli/__init__.py", "orangecut_cli/cli.py"}.issubset(names):
                raise InstallError("PAYLOAD_INVALID", "the oc wheel package is incomplete")
            metadata = archive.read(metadata_files[0]).decode("utf-8")
            entry_points = archive.read(entry_point_files[0]).decode("utf-8")
    except InstallError:
        raise
    except (OSError, UnicodeError, zipfile.BadZipFile) as error:
        raise InstallError("PAYLOAD_INVALID", "the oc wheel is unreadable") from error
    metadata_lines = set(metadata.splitlines())
    if not {
        f"Name: {CLI_PACKAGE}",
        f"Version: {version}",
        "Requires-Python: >=3.10",
    }.issubset(metadata_lines):
        raise InstallError("PAYLOAD_INVALID", "the oc wheel metadata differs from the manifest")
    scripts = {
        line.strip()
        for line in entry_points.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    if scripts != {
        "oc = orangecut_cli.cli:main",
        "orangecut = orangecut_cli.cli:main",
    }:
        raise InstallError("PAYLOAD_INVALID", "the oc wheel entry points are invalid")


def verify_payload(root: Path) -> dict[str, Any]:
    root = Path(os.path.abspath(root.expanduser()))
    if path_is_link(root) or not root.is_dir():
        raise InstallError("PAYLOAD_INVALID", "the Agent payload is not a regular directory")
    manifest = read_json_object(root / "manifest.json")
    require_keys(manifest, {"schemaVersion", "product", "skill", "cli"}, "manifest")
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        raise InstallError("PAYLOAD_UNSUPPORTED", "the Agent payload schema is unsupported")

    product = manifest.get("product")
    skill = manifest.get("skill")
    cli = manifest.get("cli")
    if not all(isinstance(item, dict) for item in (product, skill, cli)):
        raise InstallError("MANIFEST_INVALID", "the Agent payload sections must be objects")
    require_keys(product, {"name", "version"}, "product")
    require_keys(skill, {"name", "relativePath", "sha256", "files"}, "skill")
    require_keys(
        cli,
        {"package", "version", "requiresPython", "commands", "wheel", "sha256"},
        "cli",
    )
    version = require_text(product, "version", "product")
    if product.get("name") != PRODUCT_NAME or skill.get("name") != SKILL_NAME:
        raise InstallError("MANIFEST_INVALID", "the Agent payload product or Skill name is invalid")
    if cli.get("package") != CLI_PACKAGE or cli.get("version") != version:
        raise InstallError("MANIFEST_INVALID", "the Agent payload versions are not aligned")
    if cli.get("requiresPython") != ">=3.10" or cli.get("commands") != list(COMMANDS):
        raise InstallError("MANIFEST_INVALID", "the Agent payload CLI contract is invalid")
    if skill.get("relativePath") != f"skills/{SKILL_NAME}":
        raise InstallError("MANIFEST_INVALID", "the Agent payload Skill location is invalid")

    skill_files = skill.get("files")
    if (
        not isinstance(skill_files, list)
        or not skill_files
        or any(not isinstance(value, str) for value in skill_files)
        or len(set(skill_files)) != len(skill_files)
    ):
        raise InstallError("MANIFEST_INVALID", "the Agent payload Skill file list is invalid")
    for relative in skill_files:
        validate_skill_file(relative)
    roots = {PurePosixPath(relative).parts[0] for relative in skill_files}
    if "SKILL.md" not in skill_files or not {"agents", "references"}.issubset(roots):
        raise InstallError("MANIFEST_INVALID", "the Agent payload Skill is incomplete")
    wheel_relative = require_text(cli, "wheel", "cli")
    wheel_safe = safe_relative(wheel_relative)
    expected_wheel = f"orangecut_cli-{version}-py3-none-any.whl"
    if wheel_safe.parts != ("cli", expected_wheel):
        raise InstallError("MANIFEST_INVALID", "the Agent payload wheel location is invalid")

    skill_root = payload_path(root, skill["relativePath"])
    wheel = payload_path(root, wheel_relative)
    actual_skill_files = [path.relative_to(skill_root).as_posix() for path in regular_files(skill_root)]
    # Which files are here is the question; what order they came back in is not.
    # Comparing the two listings as written once made this unsatisfiable on
    # Windows, where the walk is case-folded and the manifest is not.
    if sorted(actual_skill_files) != sorted(skill_files):
        raise InstallError("PAYLOAD_INVALID", "the Agent payload Skill file set does not match its manifest")
    if skill_files != sorted(skill_files):
        raise InstallError("MANIFEST_INVALID", "the Agent payload Skill file list is not canonical")
    if tree_digest(skill_root, maximum=MAX_SKILL_BYTES) != require_text(skill, "sha256", "skill"):
        raise InstallError("PAYLOAD_TAMPERED", "the Agent payload Skill hash does not match")
    if path_is_link(wheel) or not wheel.is_file():
        raise InstallError("PAYLOAD_INVALID", "the Agent payload wheel is not regular")
    verify_wheel(wheel, version)
    if sha256_file(wheel, MAX_WHEEL_BYTES) != require_text(cli, "sha256", "cli"):
        raise InstallError("PAYLOAD_TAMPERED", "the Agent payload wheel hash does not match")

    expected_files = {
        "manifest.json",
        wheel_relative,
        *{f"skills/{SKILL_NAME}/{relative}" for relative in skill_files},
    }
    actual_files = {path.relative_to(root).as_posix() for path in regular_files(root)}
    if actual_files != expected_files:
        raise InstallError("PAYLOAD_INVALID", "the Agent payload contains undeclared files")
    return {
        "root": root,
        "manifest": manifest,
        "version": version,
        "skillRoot": skill_root,
        "wheel": wheel,
        "payloadSha256": tree_digest(root, maximum=MAX_PAYLOAD_BYTES),
    }


def run_uv(uv: str, arguments: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        inherited_lock = (
            (_ACTIVE_INSTALL_LOCK_DESCRIPTOR,)
            if os.name != "nt" and _ACTIVE_INSTALL_LOCK_DESCRIPTOR is not None
            else ()
        )
        # uv writes UTF-8 regardless of the console code page; decoding it with the
        # locale (GBK on a Chinese Windows) kills the reader thread mid-install.
        return subprocess.run(
            [uv, *arguments, "--no-config", "--no-progress"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            pass_fds=inherited_lock,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise InstallError("UV_UNAVAILABLE", "UV could not execute the requested tool lifecycle") from error


def uv_bin_directory(uv: str) -> Path:
    completed = run_uv(uv, ["tool", "dir", "--bin"])
    candidate = Path(completed.stdout.strip()) if completed.returncode == 0 else Path()
    if completed.returncode != 0 or not candidate.is_absolute():
        raise InstallError("UV_UNAVAILABLE", "UV could not resolve its executable directory")
    if candidate.exists() and (path_is_link(candidate) or not candidate.is_dir()):
        raise InstallError("UV_DIRECTORY_UNSAFE", "the UV executable directory is unsafe")
    return candidate


def uv_has_cli_package(uv: str) -> bool:
    completed = run_uv(uv, ["tool", "list", "--show-paths"])
    if completed.returncode != 0:
        raise InstallError("UV_UNAVAILABLE", "UV could not inspect installed tools")
    return re.search(rf"(?m)^{re.escape(CLI_PACKAGE)}(?:\s|$)", completed.stdout) is not None


def uv_install(uv: str, wheel: Path, python: str | None, *, force: bool) -> None:
    arguments = ["tool", "install", "--no-index"]
    if force:
        arguments.append("--force")
    if python:
        arguments.extend(("--python", python))
    arguments.append(str(wheel))
    completed = run_uv(uv, arguments)
    if completed.returncode != 0:
        raise InstallError(
            "CLI_INSTALL_FAILED",
            "UV could not install the verified oc wheel",
            "resolve the reported command/Python conflict and retry",
        )


def uv_uninstall(uv: str) -> None:
    completed = run_uv(uv, ["tool", "uninstall", CLI_PACKAGE])
    if completed.returncode != 0:
        raise InstallError(
            "CLI_UNINSTALL_FAILED",
            "UV could not uninstall the managed oc package",
            "repair the managed UV tool and retry",
        )


def command_candidates(bin_root: Path, command: str) -> list[Path]:
    suffixes = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)
    return [
        bin_root / f"{command}{suffix}"
        for suffix in suffixes
        if (bin_root / f"{command}{suffix}").exists()
        or path_is_link(bin_root / f"{command}{suffix}")
    ]


def command_fingerprint(path: Path) -> str:
    if path_is_link(path):
        try:
            target = os.readlink(path)
            resolved = path.resolve(strict=True)
            content_digest = sha256_file(resolved, MAX_COMMAND_BYTES)
        except OSError as error:
            raise InstallError("CLI_COMMAND_UNSAFE", "a managed CLI command cannot be verified") from error
        digest = hashlib.sha256(
            b"link\0"
            + os.fsencode(target)
            + b"\0"
            + content_digest.encode("ascii")
        )
        return f"sha256:{digest.hexdigest()}"
    if not path.is_file():
        raise InstallError("CLI_COMMAND_UNSAFE", "a managed CLI command is not a regular file")
    return sha256_file(path, MAX_COMMAND_BYTES)


def installed_commands(bin_root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for command in COMMANDS:
        candidates = command_candidates(bin_root, command)
        if len(candidates) != 1:
            raise InstallError("CLI_COMMAND_INVALID", f"the managed {command} command is missing or ambiguous")
        result[command] = candidates[0]
    return result


def preflight_external_commands(bin_root: Path) -> None:
    for command in COMMANDS:
        if command_candidates(bin_root, command):
            raise InstallError(
                "CLI_COMMAND_CONFLICT",
                f"the {command} command already exists and is not managed by this installer",
                "preserve the existing command or explicitly uninstall its owner before retrying",
            )
        visible = shutil.which(command)
        if visible is not None:
            raise InstallError(
                "CLI_COMMAND_CONFLICT",
                f"another {command} command is already visible on PATH",
                "preserve the existing command or change PATH before installing OrangeCut Agent tools",
            )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as destination:
        json.dump(payload, destination, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())
    sync_directory(path.parent)


def replace_json(path: Path, payload: dict[str, Any]) -> None:
    staging = path.with_name(f".{path.name}.stage-{uuid.uuid4().hex}")
    try:
        write_json(staging, payload)
        durable_replace(staging, path)
    finally:
        if staging.exists() and not path_is_link(staging):
            staging.unlink()
            sync_directory(staging.parent)


def copy_skill(payload: dict[str, Any], destination: Path) -> None:
    skill = payload["manifest"]["skill"]
    destination.mkdir(parents=True)
    for relative in skill["files"]:
        source = payload_path(payload["skillRoot"], relative)
        target = payload_path(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if tree_digest(destination, maximum=MAX_SKILL_BYTES) != skill["sha256"]:
        raise InstallError(
            "PAYLOAD_TAMPERED",
            "the Agent payload Skill changed while it was being staged",
        )
    write_json(
        destination / SKILL_MARKER,
        {
            "schemaVersion": SCHEMA_VERSION,
            "managedBy": MANAGED_BY,
            "version": payload["version"],
            "payloadSha256": payload["payloadSha256"],
            "skillSha256": skill["sha256"],
        },
    )
    sync_tree(destination)


def install_record(payload: dict[str, Any], commands: dict[str, Path]) -> dict[str, Any]:
    wheel = payload["wheel"]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "managedBy": MANAGED_BY,
        "version": payload["version"],
        "payloadSha256": payload["payloadSha256"],
        "skillSha256": payload["manifest"]["skill"]["sha256"],
        "cliWheelSha256": payload["manifest"]["cli"]["sha256"],
        "cliWheelFile": wheel.name,
        "commands": {name: command_fingerprint(path) for name, path in commands.items()},
    }


def copy_state_wheel(payload: dict[str, Any], destination: Path) -> Path:
    destination.mkdir(parents=True)
    retained = destination / payload["wheel"].name
    shutil.copyfile(payload["wheel"], retained)
    if sha256_file(retained, MAX_WHEEL_BYTES) != payload["manifest"]["cli"]["sha256"]:
        raise InstallError(
            "PAYLOAD_TAMPERED",
            "the Agent payload wheel changed while it was being staged",
        )
    sync_regular_file(retained)
    sync_directory(destination)
    return retained


def validate_record(record: dict[str, Any]) -> None:
    require_keys(
        record,
        {
            "schemaVersion",
            "managedBy",
            "version",
            "payloadSha256",
            "skillSha256",
            "cliWheelSha256",
            "cliWheelFile",
            "commands",
        },
        "install record",
    )
    if (
        record.get("schemaVersion") != SCHEMA_VERSION
        or not is_product_managed(record.get("managedBy"))
    ):
        raise InstallError(
            "INSTALL_STATE_UNMANAGED",
            "the existing Agent install state is not managed by OrangeCut",
        )
    for key in ("version", "payloadSha256", "skillSha256", "cliWheelSha256", "cliWheelFile"):
        require_text(record, key, "install record")
    digest_keys = ("payloadSha256", "skillSha256", "cliWheelSha256")
    if any(
        re.fullmatch(r"sha256:[0-9a-f]{64}", record[key]) is None
        for key in digest_keys
    ):
        raise InstallError("INSTALL_STATE_INVALID", "the managed digest record is invalid")
    if not isinstance(record.get("commands"), dict) or set(record["commands"]) != set(COMMANDS):
        raise InstallError("INSTALL_STATE_INVALID", "the managed command record is invalid")
    if any(
        not isinstance(value, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None
        for value in record["commands"].values()
    ):
        raise InstallError("INSTALL_STATE_INVALID", "the managed command fingerprints are invalid")
    try:
        wheel_file = safe_relative(record["cliWheelFile"])
    except InstallError as error:
        raise InstallError("INSTALL_STATE_INVALID", "the managed wheel name is invalid") from error
    if (
        len(wheel_file.parts) != 1
        or wheel_file.name != f"orangecut_cli-{record['version']}-py3-none-any.whl"
    ):
        raise InstallError("INSTALL_STATE_INVALID", "the managed wheel name is invalid")


def validate_managed_skill(skill_root: Path) -> dict[str, Any]:
    if path_is_link(skill_root) or not skill_root.is_dir():
        raise InstallError(
            "INSTALL_STATE_INVALID",
            "the managed Agent Skill is missing or redirected",
        )
    marker = read_json_object(skill_root / SKILL_MARKER)
    require_keys(
        marker,
        {"schemaVersion", "managedBy", "version", "payloadSha256", "skillSha256"},
        "Skill marker",
    )
    if (
        marker.get("schemaVersion") != SCHEMA_VERSION
        or not is_product_managed(marker.get("managedBy"))
    ):
        raise InstallError(
            "INSTALL_STATE_UNMANAGED",
            "the Agent Skill is not managed by OrangeCut",
        )
    for key in ("version", "payloadSha256", "skillSha256"):
        require_text(marker, key, "Skill marker")
    if any(
        re.fullmatch(r"sha256:[0-9a-f]{64}", marker[key]) is None
        for key in ("payloadSha256", "skillSha256")
    ):
        raise InstallError("INSTALL_STATE_INVALID", "the managed Skill marker is invalid")
    if tree_digest(skill_root, ignored={SKILL_MARKER}) != marker["skillSha256"]:
        raise InstallError("INSTALL_STATE_TAMPERED", "the installed Skill has changed outside the installer")
    return marker


def validate_managed_state(state_root: Path) -> dict[str, Any]:
    if path_is_link(state_root) or not state_root.is_dir():
        raise InstallError(
            "INSTALL_STATE_INVALID",
            "the managed Agent rollback state is missing or redirected",
        )
    record = read_json_object(state_root / INSTALL_RECORD)
    validate_record(record)
    wheel = state_root / record["cliWheelFile"]
    if {
        path.relative_to(state_root).as_posix() for path in regular_files(state_root)
    } != {INSTALL_RECORD, record["cliWheelFile"]}:
        raise InstallError("INSTALL_STATE_TAMPERED", "the managed rollback state has unexpected files")
    if path_is_link(wheel) or not wheel.is_file() or sha256_file(wheel) != record["cliWheelSha256"]:
        raise InstallError("INSTALL_STATE_TAMPERED", "the retained rollback wheel does not match install state")
    return {"record": record, "wheel": wheel}


def validate_managed_files(skill_root: Path, state_root: Path) -> dict[str, Any]:
    marker = validate_managed_skill(skill_root)
    current = validate_managed_state(state_root)
    record = current["record"]
    if (
        marker["version"] != record["version"]
        or marker["payloadSha256"] != record["payloadSha256"]
        or marker["skillSha256"] != record["skillSha256"]
    ):
        raise InstallError("INSTALL_STATE_INVALID", "the managed Skill marker does not match install state")
    return current


def validate_managed_install(agent_home: Path, bin_root: Path, uv: str) -> dict[str, Any] | None:
    state_root = agent_home / STATE_DIRECTORY
    skill_root = agent_home / "skills" / SKILL_NAME
    state_exists = state_root.exists() or path_is_link(state_root)
    skill_exists = skill_root.exists() or path_is_link(skill_root)
    if not state_exists and not skill_exists:
        return None
    if skill_exists and not state_exists:
        raise InstallError(
            "INSTALL_STATE_UNMANAGED",
            "an unmanaged orangecut Skill exists and was preserved",
        )
    current = validate_managed_files(skill_root, state_root)
    if not uv_has_cli_package(uv):
        raise InstallError("INSTALL_STATE_INVALID", "the managed UV tool is missing")
    commands = installed_commands(bin_root)
    fingerprints = {name: command_fingerprint(path) for name, path in commands.items()}
    if fingerprints != current["record"]["commands"]:
        raise InstallError("INSTALL_STATE_TAMPERED", "a managed CLI command has changed outside the installer")
    current["commands"] = commands
    return current


def cleanup_tree(path: Path) -> None:
    if not path.exists() and not path_is_link(path):
        return
    if path_is_link(path) or not path.is_dir():
        raise InstallError("CLEANUP_REFUSED", "refusing to remove a non-directory installer staging path")
    shutil.rmtree(path)
    sync_directory(path.parent)


def transaction_path(agent_home: Path) -> Path:
    return agent_home / INSTALL_TRANSACTION


def begin_transaction(
    agent_home: Path,
    operation: str,
    suffix: str,
    previous: bool,
    previous_payload_sha256: str | None,
    target_payload_sha256: str,
) -> None:
    path = transaction_path(agent_home)
    if path.exists() or path_is_link(path):
        raise InstallError(
            "INSTALL_RECOVERY_REQUIRED",
            "an earlier Agent installer transaction must be recovered first",
        )
    write_json(
        path,
        {
            "schemaVersion": SCHEMA_VERSION,
            "managedBy": MANAGED_BY,
            "operation": operation,
            "suffix": suffix,
            "previous": previous,
            "previousPayloadSha256": previous_payload_sha256,
            "targetPayloadSha256": target_payload_sha256,
        },
    )


def read_transaction(agent_home: Path) -> dict[str, Any] | None:
    path = transaction_path(agent_home)
    if not path.exists() and not path_is_link(path):
        return None
    transaction = read_json_object(path)
    expected = {
        "schemaVersion",
        "managedBy",
        "operation",
        "suffix",
        "previous",
        "previousPayloadSha256",
        "targetPayloadSha256",
    }
    if set(transaction) != expected:
        raise InstallError("INSTALL_RECOVERY_REQUIRED", "the installer transaction shape is invalid")
    operation = transaction.get("operation")
    suffix = transaction.get("suffix")
    previous = transaction.get("previous")
    previous_payload = transaction.get("previousPayloadSha256")
    target = transaction.get("targetPayloadSha256")
    if (
        transaction.get("schemaVersion") != SCHEMA_VERSION
        or not is_product_managed(transaction.get("managedBy"))
        or not isinstance(operation, str)
        or operation not in {"install", "update", "uninstall"}
        or not isinstance(suffix, str)
        or re.fullmatch(r"[0-9a-f]{32}", suffix) is None
        or not isinstance(previous, bool)
        or (
            previous_payload is not None
            and (
                not isinstance(previous_payload, str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", previous_payload) is None
            )
        )
        or not isinstance(target, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", target) is None
        or (operation == "install" and previous)
        or (operation in {"update", "uninstall"} and not previous)
        or (previous != (previous_payload is not None))
    ):
        raise InstallError("INSTALL_RECOVERY_REQUIRED", "the installer transaction is invalid")
    return transaction


def finish_transaction(agent_home: Path) -> None:
    path = transaction_path(agent_home)
    try:
        metadata = path.lstat()
    except OSError as error:
        raise InstallError(
            "INSTALL_RECOVERY_REQUIRED", "the installer transaction record is missing"
        ) from error
    if path_is_link(path) or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise InstallError(
            "INSTALL_RECOVERY_REQUIRED", "the installer transaction record is unsafe"
        )
    path.unlink()
    sync_directory(path.parent)


def transaction_directories(
    agent_home: Path, transaction: dict[str, Any]
) -> dict[str, Path]:
    suffix = transaction["suffix"]
    skills_root = agent_home / "skills"
    if transaction["operation"] == "uninstall":
        skill_backup = skills_root / f".{SKILL_NAME}.uninstall-{suffix}"
        state_backup = agent_home / f"{STATE_DIRECTORY}.uninstall-{suffix}"
    else:
        skill_backup = skills_root / f".{SKILL_NAME}.backup-{suffix}"
        state_backup = agent_home / f"{STATE_DIRECTORY}.backup-{suffix}"
    return {
        "skillRoot": skills_root / SKILL_NAME,
        "stateRoot": agent_home / STATE_DIRECTORY,
        "skillStage": skills_root / f".{SKILL_NAME}.stage-{suffix}",
        "stateStage": agent_home / f"{STATE_DIRECTORY}.stage-{suffix}",
        "skillBackup": skill_backup,
        "stateBackup": state_backup,
    }


def cleanup_transaction_directories(paths: dict[str, Path]) -> None:
    for name in ("skillStage", "stateStage", "skillBackup", "stateBackup"):
        cleanup_tree(paths[name])


def require_payload_identity(actual: str, expected: str, label: str) -> None:
    if actual != expected:
        raise InstallError(
            "INSTALL_RECOVERY_REQUIRED",
            f"the interrupted installer {label} does not match its transaction",
        )


def replace_live_with_backup(
    live: Path,
    backup: Path,
    target_payload_sha256: str,
    validator: Callable[[Path], dict[str, Any]],
) -> None:
    if not backup.exists() and not path_is_link(backup):
        return
    if live.exists() or path_is_link(live):
        current = validator(live)
        actual = current.get("payloadSha256") or current["record"]["payloadSha256"]
        require_payload_identity(actual, target_payload_sha256, "live state")
        cleanup_tree(live)
    durable_replace(backup, live)


def recover_interrupted_transaction(
    agent_home: Path,
    uv: str,
    python: str | None,
) -> str | None:
    transaction = read_transaction(agent_home)
    if transaction is None:
        return None
    paths = transaction_directories(agent_home, transaction)
    target = transaction["targetPayloadSha256"]
    bin_root = uv_bin_directory(uv)

    try:
        current = validate_managed_install(agent_home, bin_root, uv)
    except InstallError:
        current = None
    if current is not None and current["record"]["payloadSha256"] == target:
        previous_target = transaction["previousPayloadSha256"]
        backup_skill_exists = paths["skillBackup"].exists() or path_is_link(
            paths["skillBackup"]
        )
        backup_state_exists = paths["stateBackup"].exists() or path_is_link(
            paths["stateBackup"]
        )
        if (backup_skill_exists or backup_state_exists) and not isinstance(
            previous_target, str
        ):
            raise InstallError(
                "INSTALL_RECOVERY_REQUIRED",
                "the interrupted initial install has unexpected recovery backups",
            )
        if backup_skill_exists and backup_state_exists:
            backup = validate_managed_files(
                paths["skillBackup"], paths["stateBackup"]
            )
            require_payload_identity(
                backup["record"]["payloadSha256"], previous_target, "recovery backup"
            )
        elif backup_skill_exists:
            marker = validate_managed_skill(paths["skillBackup"])
            require_payload_identity(
                marker["payloadSha256"], previous_target, "Skill backup"
            )
        elif backup_state_exists:
            state = validate_managed_state(paths["stateBackup"])
            require_payload_identity(
                state["record"]["payloadSha256"], previous_target, "state backup"
            )
        cleanup_transaction_directories(paths)
        finish_transaction(agent_home)
        return "rolled_back" if transaction["operation"] == "uninstall" else "completed"

    if transaction["operation"] == "uninstall":
        skill_exists = paths["skillRoot"].exists() or path_is_link(paths["skillRoot"])
        state_exists = paths["stateRoot"].exists() or path_is_link(paths["stateRoot"])
        cli_exists = uv_has_cli_package(uv)
        if not skill_exists and not state_exists and not cli_exists:
            backup_skill_exists = paths["skillBackup"].exists() or path_is_link(
                paths["skillBackup"]
            )
            backup_state_exists = paths["stateBackup"].exists() or path_is_link(
                paths["stateBackup"]
            )
            if backup_skill_exists != backup_state_exists:
                raise InstallError(
                    "INSTALL_RECOVERY_REQUIRED",
                    "the interrupted uninstall has incomplete recovery backups",
                )
            if backup_skill_exists:
                backup = validate_managed_files(
                    paths["skillBackup"], paths["stateBackup"]
                )
                require_payload_identity(
                    backup["record"]["payloadSha256"], target, "uninstall backup"
                )
            cleanup_transaction_directories(paths)
            finish_transaction(agent_home)
            return "completed"

    if transaction["previous"]:
        previous_target = transaction["previousPayloadSha256"]
        assert isinstance(previous_target, str)
        old_skill = (
            paths["skillBackup"]
            if paths["skillBackup"].exists() or path_is_link(paths["skillBackup"])
            else paths["skillRoot"]
        )
        old_state = (
            paths["stateBackup"]
            if paths["stateBackup"].exists() or path_is_link(paths["stateBackup"])
            else paths["stateRoot"]
        )
        previous = validate_managed_files(old_skill, old_state)
        require_payload_identity(
            previous["record"]["payloadSha256"], previous_target, "previous state"
        )
        replace_live_with_backup(
            paths["skillRoot"], paths["skillBackup"], target, validate_managed_skill
        )
        replace_live_with_backup(
            paths["stateRoot"], paths["stateBackup"], target, validate_managed_state
        )
        previous = validate_managed_files(paths["skillRoot"], paths["stateRoot"])
        uv_install(uv, previous["wheel"], python, force=True)
        refresh_command_record(previous, paths["stateRoot"], bin_root)
        validate_managed_install(agent_home, bin_root, uv)
    else:
        if paths["skillRoot"].exists() or path_is_link(paths["skillRoot"]):
            marker = validate_managed_skill(paths["skillRoot"])
            require_payload_identity(marker["payloadSha256"], target, "new Skill")
            cleanup_tree(paths["skillRoot"])
        if paths["stateRoot"].exists() or path_is_link(paths["stateRoot"]):
            state = validate_managed_state(paths["stateRoot"])
            require_payload_identity(
                state["record"]["payloadSha256"], target, "new rollback state"
            )
            cleanup_tree(paths["stateRoot"])
        if uv_has_cli_package(uv):
            uv_uninstall(uv)

    cleanup_transaction_directories(paths)
    finish_transaction(agent_home)
    return "rolled_back"


def refresh_command_record(
    previous: dict[str, Any], state_root: Path, bin_root: Path
) -> None:
    record = dict(previous["record"])
    record["commands"] = {
        name: command_fingerprint(path)
        for name, path in installed_commands(bin_root).items()
    }
    replace_json(state_root / INSTALL_RECORD, record)
    previous["record"] = record


def rollback_cli(
    uv: str,
    python: str | None,
    previous: dict[str, Any] | None,
    state_root: Path,
    bin_root: Path,
) -> None:
    if previous is None:
        if uv_has_cli_package(uv):
            uv_uninstall(uv)
    else:
        uv_install(uv, previous["wheel"], python, force=True)
        refresh_command_record(previous, state_root, bin_root)


def displace_adopted_skill(agent_home: Path) -> Path | None:
    """Move aside a Skill this product wrote but has no managed state for.

    Installing over it is otherwise impossible: the installer keeps a record of
    what it put there, and a Skill directory with no matching record is one it
    refuses to touch -- rightly, because the usual reason for one is that
    somebody wrote it themselves. But the directory this product writes carries
    a marker naming this product, and that tells the two cases apart. Anyone
    who staged the Skill by hand, around a failing installer, is left holding
    exactly that: our own directory, no record, and no way forward.

    Moved rather than deleted, so a failed install can put it back.
    """
    if path_is_link(agent_home) or not agent_home.is_dir():
        return None
    state_root = agent_home / STATE_DIRECTORY
    if state_root.exists() or path_is_link(state_root):
        return None
    skills_root = agent_home / "skills"
    skill_root = skills_root / SKILL_NAME
    if path_is_link(skill_root) or not skill_root.is_dir():
        return None
    try:
        marker = read_json_object(skill_root / SKILL_MARKER)
    except InstallError:
        return None
    if not is_product_managed(marker.get("managedBy")):
        # Somebody else's Skill, or somebody's own notes under our name. The
        # refusal that follows names it and leaves it where it is.
        return None
    displaced = skills_root / f".{SKILL_NAME}.adopted-{uuid.uuid4().hex}"
    durable_replace(skill_root, displaced)
    return displaced


def install(
    payload: dict[str, Any],
    agent_home: Path,
    uv: str,
    python: str | None,
    *,
    adopt: bool = False,
) -> str:
    displaced = displace_adopted_skill(agent_home) if adopt else None
    if displaced is None:
        return perform_install(payload, agent_home, uv, python, adopt=adopt)
    try:
        status = perform_install(payload, agent_home, uv, python, adopt=adopt)
    except BaseException:
        skill_root = agent_home / "skills" / SKILL_NAME
        if not skill_root.exists() and not path_is_link(skill_root):
            durable_replace(displaced, skill_root)
        raise
    cleanup_tree(displaced)
    # What happened is a takeover whether or not a UV tool was involved.
    return "adopted" if status == "installed" else status


def perform_install(
    payload: dict[str, Any],
    agent_home: Path,
    uv: str,
    python: str | None,
    *,
    adopt: bool = False,
) -> str:
    if path_is_link(agent_home):
        raise InstallError("AGENT_HOME_UNSAFE", "the explicit Agent home must not be a directory link")
    agent_home.mkdir(parents=True, exist_ok=True)
    sync_directory(agent_home)
    sync_directory(agent_home.parent)
    skills_root = agent_home / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    if path_is_link(skills_root) or not skills_root.is_dir():
        raise InstallError("AGENT_HOME_UNSAFE", "the Agent skills root is unsafe")
    sync_directory(agent_home)
    bin_root = uv_bin_directory(uv)
    previous = validate_managed_install(agent_home, bin_root, uv)
    adopted = False
    if previous is None:
        unmanaged = (agent_home / STATE_DIRECTORY).exists() or uv_has_cli_package(uv)
        # Reachable only for the UV tool: `validate_managed_install` returns
        # None just when neither the managed state nor the Skill is there, and
        # it refuses an unmanaged Skill earlier and by name. So adopting takes
        # over a `uv tool install orangecut-cli` somebody ran themselves, and
        # never touches a Skill directory somebody wrote by hand.
        if unmanaged and not adopt:
            # Uninstalling by hand is not the cheap way out it reads as: the
            # `oc` launcher this product ships runs out of the UV tool
            # environment rather than carrying its own, so a `uv tool
            # uninstall` that fails halfway -- and it does, whenever something
            # still holds the Scripts directory open -- leaves `oc` unable to
            # import its own package. Taking the tool over in place never puts
            # the machine through that window.
            raise InstallError(
                "INSTALL_STATE_UNMANAGED",
                "an unmanaged orangecut-cli UV tool already exists",
                "rerun with --adopt to take it over in place, which replaces it "
                "with this verified wheel without uninstalling it first",
            )
        if unmanaged:
            adopted = True
        else:
            preflight_external_commands(bin_root)
    elif previous["record"]["payloadSha256"] == payload["payloadSha256"]:
        return "already_ready"

    suffix = uuid.uuid4().hex
    skill_root = skills_root / SKILL_NAME
    skill_stage = skills_root / f".{SKILL_NAME}.stage-{suffix}"
    skill_backup = skills_root / f".{SKILL_NAME}.backup-{suffix}"
    state_root = agent_home / STATE_DIRECTORY
    state_stage = agent_home / f"{STATE_DIRECTORY}.stage-{suffix}"
    state_backup = agent_home / f"{STATE_DIRECTORY}.backup-{suffix}"
    cli_attempted = False
    skill_swapped = False
    skill_backed_up = False
    state_swapped = False
    state_backed_up = False
    begin_transaction(
        agent_home,
        "update" if previous is not None else "install",
        suffix,
        previous is not None,
        previous["record"]["payloadSha256"] if previous is not None else None,
        payload["payloadSha256"],
    )
    try:
        copy_skill(payload, skill_stage)
        retained_wheel = copy_state_wheel(payload, state_stage)
        if previous is not None:
            durable_replace(skill_root, skill_backup)
            skill_backed_up = True
        durable_replace(skill_stage, skill_root)
        skill_swapped = True

        cli_attempted = True
        uv_install(uv, retained_wheel, python, force=previous is not None or adopted)
        commands = installed_commands(bin_root)
        record = install_record(payload, commands)
        write_json(state_stage / INSTALL_RECORD, record)
        if previous is not None:
            durable_replace(state_root, state_backup)
            state_backed_up = True
        durable_replace(state_stage, state_root)
        state_swapped = True
    except BaseException as error:
        rollback_errors: list[str] = []
        if state_swapped or state_backed_up:
            try:
                if state_swapped:
                    cleanup_tree(state_root)
                if state_backed_up and state_backup.exists():
                    durable_replace(state_backup, state_root)
            except BaseException:
                rollback_errors.append("state")
        if cli_attempted:
            try:
                rollback_cli(uv, python, previous, state_root, bin_root)
            except BaseException:
                rollback_errors.append("cli")
        if skill_swapped or skill_backed_up:
            try:
                if skill_swapped:
                    cleanup_tree(skill_root)
                if skill_backed_up and skill_backup.exists():
                    durable_replace(skill_backup, skill_root)
            except BaseException:
                rollback_errors.append("skill")
        for staging_name, staging in (("skill-stage", skill_stage), ("state-stage", state_stage)):
            try:
                cleanup_tree(staging)
            except BaseException:
                rollback_errors.append(staging_name)
        if rollback_errors:
            raise InstallError(
                "INSTALL_ROLLBACK_FAILED",
                "the Agent installation failed and rollback needs repair: " + ", ".join(rollback_errors),
            ) from error
        finish_transaction(agent_home)
        if isinstance(error, InstallError):
            raise
        raise InstallError("INSTALL_FAILED", "the Agent installation could not be committed") from error

    for path in (skill_stage, state_stage, skill_backup, state_backup):
        cleanup_tree(path)
    finish_transaction(agent_home)
    if previous is not None:
        return "updated"
    return "adopted" if adopted else "installed"


def check(payload: dict[str, Any], agent_home: Path, uv: str) -> str:
    if path_is_link(agent_home) or not agent_home.is_dir():
        raise InstallError("INSTALL_NOT_FOUND", "the OrangeCut Agent tools are not installed")
    current = validate_managed_install(agent_home, uv_bin_directory(uv), uv)
    if current is None:
        raise InstallError("INSTALL_NOT_FOUND", "the OrangeCut Agent tools are not installed")
    if current["record"]["payloadSha256"] != payload["payloadSha256"]:
        raise InstallError(
            "INSTALL_UPDATE_REQUIRED",
            "the installed Agent tools do not match this verified payload",
            "run the product installer to update Skill and CLI together",
        )
    return "ready"


def uninstall(agent_home: Path, uv: str, python: str | None) -> str:
    bin_root = uv_bin_directory(uv)
    if path_is_link(agent_home) or not agent_home.is_dir():
        if uv_has_cli_package(uv):
            raise InstallError("UNINSTALL_REFUSED", "an unmanaged orangecut-cli UV tool exists")
        return "already_absent"
    current = validate_managed_install(agent_home, bin_root, uv)
    if current is None:
        if uv_has_cli_package(uv):
            raise InstallError("UNINSTALL_REFUSED", "an unmanaged orangecut-cli UV tool exists")
        return "already_absent"

    suffix = uuid.uuid4().hex
    skill_root = agent_home / "skills" / SKILL_NAME
    state_root = agent_home / STATE_DIRECTORY
    skill_backup = agent_home / "skills" / f".{SKILL_NAME}.uninstall-{suffix}"
    state_backup = agent_home / f"{STATE_DIRECTORY}.uninstall-{suffix}"
    skill_backed_up = False
    state_backed_up = False
    begin_transaction(
        agent_home,
        "uninstall",
        suffix,
        True,
        current["record"]["payloadSha256"],
        current["record"]["payloadSha256"],
    )
    try:
        durable_replace(skill_root, skill_backup)
        skill_backed_up = True
        durable_replace(state_root, state_backup)
        state_backed_up = True
        current["wheel"] = state_backup / current["record"]["cliWheelFile"]
        uv_uninstall(uv)
    except BaseException as error:
        rollback_errors: list[str] = []
        try:
            if uv_has_cli_package(uv):
                commands = installed_commands(bin_root)
                if {name: command_fingerprint(path) for name, path in commands.items()} != current["record"]["commands"]:
                    uv_install(uv, current["wheel"], python, force=True)
            else:
                uv_install(uv, current["wheel"], python, force=True)
        except BaseException:
            rollback_errors.append("cli")
        try:
            if skill_backed_up:
                durable_replace(skill_backup, skill_root)
            if state_backed_up:
                durable_replace(state_backup, state_root)
            refresh_command_record(current, state_root, bin_root)
        except BaseException:
            rollback_errors.append("state")
        if rollback_errors:
            raise InstallError(
                "UNINSTALL_ROLLBACK_FAILED",
                "the Agent uninstall failed and rollback needs repair: " + ", ".join(rollback_errors),
            ) from error
        finish_transaction(agent_home)
        if isinstance(error, InstallError):
            raise
        raise InstallError("UNINSTALL_FAILED", "the Agent tools could not be uninstalled") from error
    cleanup_tree(skill_backup)
    cleanup_tree(state_backup)
    finish_transaction(agent_home)
    return "uninstalled"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument(
        "--agent-home",
        type=Path,
        help="the Agent home to install into, e.g. ~/.claude or ~/.codex",
    )
    parser.add_argument("--codex-home", type=Path, help="deprecated alias for --agent-home")
    parser.add_argument("--uv", default=shutil.which("uv"))
    parser.add_argument("--python")
    parser.add_argument(
        "--adopt",
        action="store_true",
        help=(
            "take over an existing unmanaged orangecut-cli UV tool in place "
            "instead of refusing; replaces it with this verified wheel and "
            "discards any unmanaged Skill and state left beside it"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--uninstall", action="store_true")
    arguments = parser.parse_args()
    # Named, never guessed: on a machine with several Agents installed, choosing
    # one silently puts the Skill somewhere real that the Agent they meant will
    # never look in. Whoever runs this knows the answer.
    agent_home = arguments.agent_home or arguments.codex_home
    if agent_home is None:
        emit(
            False,
            "failed",
            code="AGENT_HOME_REQUIRED",
            message="--agent-home is required: name the Agent home to install into",
        )
        return 2
    arguments.agent_home = agent_home
    if not arguments.uv:
        emit(False, "failed", code="UV_UNAVAILABLE", message="UV is required")
        return 2
    agent_home = Path(os.path.abspath(arguments.agent_home.expanduser()))
    bin_root_result: Path | None = None
    recovery_result: str | None = None
    try:
        payload = verify_payload(arguments.payload)
        if (
            not re.fullmatch(r"sha256:[0-9a-f]{64}", arguments.expected_sha256)
            or payload["payloadSha256"] != arguments.expected_sha256
        ):
            raise InstallError(
                "PAYLOAD_TAMPERED",
                "the Agent payload does not match the signed installer digest",
            )
        if not arguments.check and not arguments.uninstall:
            if path_is_link(agent_home):
                raise InstallError(
                    "AGENT_HOME_UNSAFE",
                    "the explicit Agent home must not be a directory link",
                )
            agent_home.mkdir(parents=True, exist_ok=True)
        if agent_home.is_dir() and not path_is_link(agent_home):
            with installation_lock(agent_home):
                recovery_result = recover_interrupted_transaction(
                    agent_home, arguments.uv, arguments.python
                )
                if arguments.check:
                    status = check(payload, agent_home, arguments.uv)
                elif arguments.uninstall:
                    status = uninstall(agent_home, arguments.uv, arguments.python)
                else:
                    status = install(
                        payload,
                        agent_home,
                        arguments.uv,
                        arguments.python,
                        adopt=arguments.adopt,
                    )
        elif arguments.check:
            status = check(payload, agent_home, arguments.uv)
        elif arguments.uninstall:
            status = uninstall(agent_home, arguments.uv, arguments.python)
        else:
            status = install(
                payload,
                agent_home,
                arguments.uv,
                arguments.python,
                adopt=arguments.adopt,
            )
        if not arguments.uninstall:
            bin_root_result = uv_bin_directory(arguments.uv)
    except InstallError as error:
        details: dict[str, object] = {"code": error.code, "message": error.message}
        if error.remediation:
            details["remediation"] = error.remediation
        emit(False, "failed", **details)
        return 2
    except OSError:
        emit(
            False,
            "failed",
            code="INSTALL_IO_FAILED",
            message="the Agent installer could not access a required filesystem path",
        )
        return 2
    details: dict[str, object] = {
        "version": payload["version"],
        "skill": SKILL_NAME,
        "cli": CLI_PACKAGE,
        "commands": list(COMMANDS),
    }
    if recovery_result is not None:
        details["recovery"] = recovery_result
    if not arguments.uninstall:
        assert bin_root_result is not None
        path_entries = {
            Path(os.path.abspath(Path(entry).expanduser()))
            for entry in os.environ.get("PATH", "").split(os.pathsep)
            if entry
        }
        details["binDirectory"] = str(bin_root_result)
        details["pathReady"] = bin_root_result in path_entries
    emit(True, status, **details)
    return 0


if __name__ == "__main__":
    sys.exit(main())
