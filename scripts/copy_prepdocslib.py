"""Synchronize prepdocslib ingestion library to function apps.
This script ensures that the latest version of the prepdocslib library used
by backend ingestion is copied into each of the Azure Function apps that
also rely on this library.

As an azd prepackage hook, azd sets the CWD to the service project directory
and runs the per-service hooks in parallel. When the CWD is one of the
function directories, only that function is synced — this avoids races
between parallel hook invocations. Otherwise all function directories are
synced.

Steps:
1. Copy `prepdocslib` into each function directory.
2. Overwrite each function's `requirements.txt` with backend `requirements.txt`.
"""

import shutil
from pathlib import Path

FUNCTION_NAMES = ("document_extractor", "figure_processor", "text_processor")


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def resolve_targets(repo_root: Path) -> list[Path]:
    functions_root = (repo_root / "app" / "functions").resolve()
    cwd = Path.cwd().resolve()
    if cwd.parent == functions_root and cwd.name in FUNCTION_NAMES:
        return [cwd / "prepdocslib"]
    return [functions_root / name / "prepdocslib" for name in FUNCTION_NAMES]


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    prep_source = repo_root / "app" / "backend" / "prepdocslib"
    if not prep_source.exists():
        raise RuntimeError(f"Source prepdocslib directory not found: {prep_source}")

    backend_requirements = repo_root / "app" / "backend" / "requirements.txt"
    if not backend_requirements.exists():
        raise RuntimeError(f"Backend requirements file not found: {backend_requirements}")

    targets = resolve_targets(repo_root)

    for target in targets:
        func_dir = target.parent
        func_dir.mkdir(parents=True, exist_ok=True)

        # 1. Library sync
        copy_tree(prep_source, target)

        # 2. Overwrite requirements.txt directly
        overwrite_req = func_dir / "requirements.txt"
        shutil.copy2(backend_requirements, overwrite_req)


if __name__ == "__main__":
    main()
