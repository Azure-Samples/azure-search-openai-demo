"""Synchronize prepdocslib ingestion library to function apps.
This script ensures that the latest version of the prepdocslib library used
by backend ingestion is copied into each of the Azure Function apps that
also rely on this library.

Steps:
1. Copy `prepdocslib` into each function directory.
2. Overwrite each function's `requirements.txt` with backend `requirements.txt`.
"""

import shutil
from pathlib import Path


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    prep_source = repo_root / "app" / "backend" / "prepdocslib"
    if not prep_source.exists():
        raise RuntimeError(f"Source prepdocslib directory not found: {prep_source}")

    backend_requirements = repo_root / "app" / "backend" / "requirements.txt"
    if not backend_requirements.exists():
        raise RuntimeError(f"Backend requirements file not found: {backend_requirements}")

    targets = [
        repo_root / "app" / "functions" / "document_extractor" / "prepdocslib",
        repo_root / "app" / "functions" / "figure_processor" / "prepdocslib",
        repo_root / "app" / "functions" / "text_processor" / "prepdocslib",
    ]

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
