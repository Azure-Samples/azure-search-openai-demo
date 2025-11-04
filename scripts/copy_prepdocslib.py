"""Synchronize ingestion library and apply unified dependency pins.

Steps:
1. Copy `prepdocslib` into each function directory.
2. Overwrite each function's `requirements.txt` with backend `requirements.txt`.
3. Copy backend requirements again as `requirements.backend.txt` for audit.

No backups retained (per user request). The previous minimal requirements are
discarded. All functions now share identical pinned versions ensuring imports
like `azure.core` are available.
"""

from __future__ import annotations

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

        # 3. Copy backend requirements for explicit provenance
        audit_req = func_dir / "requirements.backend.txt"
        shutil.copy2(backend_requirements, audit_req)


if __name__ == "__main__":
    main()
