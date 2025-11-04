"""Synchronize shared ingestion library and unify dependencies across all
Azure Function projects prior to packaging.

Actions:
1. Copy `prepdocslib` into each function directory.
2. Overwrite each function's `requirements.txt` with the backend
   `requirements.txt` (full set of pins) for consistent dependency versions.
3. Preserve the original function `requirements.txt` (if it existed) as
   `requirements.functions.txt` for rollback/reference.
4. Also copy the backend requirements as `requirements.backend.txt` for audit.

Note: Using the full backend dependency set will increase package size and may
slightly impact cold start, but ensures all transitive imports (e.g. azure.core)
are available without manual curation.
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

        # 2. Preserve original requirements if present
        original_req = func_dir / "requirements.txt"
        if original_req.exists():
            backup_req = func_dir / "requirements.functions.txt"
            # Only backup if we haven't already
            if not backup_req.exists():
                shutil.copy2(original_req, backup_req)

        # 3. Overwrite with backend requirements
        shutil.copy2(backend_requirements, original_req)

        # 4. Copy backend requirements for explicit provenance
        dest_req = func_dir / "requirements.backend.txt"
        shutil.copy2(backend_requirements, dest_req)


if __name__ == "__main__":
    main()
