"""Repository-safe file and test tools exposed to the local model."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any


class ToolPolicyError(RuntimeError):
    pass


class FileTools:
    def __init__(
        self,
        root: Path,
        *,
        mutable_paths: list[str],
        protected_paths: list[str],
        public_check_argv: list[str],
        navigation_budget: int,
    ) -> None:
        self.root = root.resolve()
        self.mutable_paths = tuple(PurePosixPath(item) for item in mutable_paths)
        self.protected_paths = tuple(PurePosixPath(item) for item in protected_paths)
        self.public_check_argv = public_check_argv
        self.navigation_budget = navigation_budget
        self.navigation_calls = 0
        self.tool_calls = 0
        self.write_count = 0
        self.first_write_at: str | None = None
        self.changed_files: set[str] = set()

    def _parts(self, relative: str) -> PurePosixPath:
        if not isinstance(relative, str) or not relative:
            raise ToolPolicyError("path must be a non-empty string")
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ToolPolicyError("path must stay inside the workspace")
        return path

    @staticmethod
    def _under(path: PurePosixPath, prefix: PurePosixPath) -> bool:
        return path == prefix or prefix in path.parents

    def _resolve(self, relative: str, *, for_write: bool = False) -> Path:
        logical = self._parts(relative)
        path = self.root.joinpath(*logical.parts)
        current = self.root
        for part in logical.parts:
            current = current / part
            if current.is_symlink():
                raise ToolPolicyError("symlink paths are not allowed")
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError as error:
            raise ToolPolicyError("path must stay inside the workspace") from error
        if for_write:
            if any(self._under(logical, prefix) for prefix in self.protected_paths):
                raise ToolPolicyError("protected paths cannot be written")
            if not any(self._under(logical, prefix) for prefix in self.mutable_paths):
                raise ToolPolicyError("path is outside the mutable allowlist")
        return path

    def _navigate(self) -> None:
        if self.navigation_calls >= self.navigation_budget:
            raise ToolPolicyError("navigation budget exhausted")
        self.navigation_calls += 1
        self.tool_calls += 1

    def reset_navigation_budget(self) -> None:
        """Start a fresh bounded navigation phase without resetting evidence counts."""
        self.navigation_calls = 0

    def list_files(self, relative: str = ".") -> list[str]:
        self._navigate()
        path = self._resolve(relative)
        if not path.is_dir():
            raise ToolPolicyError("list_files target must be a directory")
        rows = []
        for item in sorted(path.rglob("*")):
            if item.is_symlink():
                continue
            if item.is_file():
                rows.append(item.relative_to(self.root).as_posix())
            if len(rows) >= 100:
                break
        return rows

    def search_text(self, needle: str, relative: str = ".") -> list[str]:
        self._navigate()
        if not needle:
            raise ToolPolicyError("search needle must be non-empty")
        base = self._resolve(relative)
        files = [base] if base.is_file() else sorted(base.rglob("*"))
        rows: list[str] = []
        for path in files:
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 1_000_000:
                continue
            try:
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if needle in line:
                        rows.append(f"{path.relative_to(self.root).as_posix()}:{number}:{line[:240]}")
                        if len(rows) >= 80:
                            return rows
            except UnicodeDecodeError:
                continue
        return rows

    def read_file(self, relative: str, start_line: int = 1, end_line: int = 240) -> str:
        self._navigate()
        path = self._resolve(relative)
        if not path.is_file():
            raise ToolPolicyError("read_file target must be a file")
        if start_line < 1 or end_line < start_line or end_line - start_line > 400:
            raise ToolPolicyError("invalid read line range")
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        return "".join(lines[start_line - 1 : end_line])

    @staticmethod
    def _validate_content(path: Path, content: str) -> None:
        if path.suffix == ".py":
            try:
                ast.parse(content)
            except SyntaxError as error:
                raise ToolPolicyError(f"Python syntax rejected: {error.msg} at line {error.lineno}") from error

    def _accept_write(self, relative: str, content: str) -> None:
        path = self._resolve(relative, for_write=True)
        self._validate_content(path, content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.tool_calls += 1
        self.write_count += 1
        self.changed_files.add(self._parts(relative).as_posix())
        if self.first_write_at is None:
            self.first_write_at = datetime.now(timezone.utc).isoformat()

    def write_file(self, relative: str, content: str) -> str:
        self._accept_write(relative, content)
        return f"wrote {relative}"

    def replace_text(
        self,
        relative: str,
        old: str,
        new: str,
        *,
        line: int,
        anchor: str,
    ) -> str:
        path = self._resolve(relative, for_write=True)
        lines = path.read_text(encoding="utf-8").splitlines()
        if line < 1 or line > len(lines) or anchor not in lines[line - 1]:
            raise ToolPolicyError("anchor does not match the declared exact line")
        content = path.read_text(encoding="utf-8")
        if content.count(old) != 1:
            raise ToolPolicyError("replace_text old value must occur exactly once")
        self._accept_write(relative, content.replace(old, new, 1))
        return f"replaced text in {relative}"

    def run_public_tests(self) -> dict[str, Any]:
        if self.write_count == 0:
            raise ToolPolicyError("public tests are unavailable before the first accepted write")
        self.tool_calls += 1
        process = subprocess.run(
            self.public_check_argv,
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=1800,
        )
        return {
            "passed": process.returncode == 0,
            "exit_code": process.returncode,
            "stdout_tail": process.stdout[-4000:],
            "stderr_tail": process.stderr[-6000:],
        }
