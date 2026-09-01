from pathlib import Path


SOURCE_EXTENSIONS = {".c", ".h"}
DEFAULT_IGNORES = {".git", ".norm_fixer_backup", "build", "dist"}


def discover_files(root: Path, excludes: set[str] | None = None) -> list[Path]:
    root = root.resolve()
    excluded = DEFAULT_IGNORES | (excludes or set())
    files: list[Path] = []

    if root.is_file():
        return [root] if root.suffix in SOURCE_EXTENSIONS else []

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_EXTENSIONS:
            continue
        if any(part in excluded for part in path.relative_to(root).parts):
            continue
        files.append(path)

    return sorted(files)
