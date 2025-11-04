"""Synchronize shared ingestion library and backend requirements with each
Azure Function project prior to packaging.

What this script does:
1. Copies the `prepdocslib` directory into every function service directory so
    that relative imports succeed at build and runtime.
2. Copies the backend `requirements.txt` alongside the function code as
    `requirements.backend.txt` for traceability and potential future merges.

Why we don't overwrite the function's own `requirements.txt`:
Each function has a minimal dependency list to reduce cold start time. The
backend dependency set is larger (includes web framework, tracing, etc.) and
is preserved separately should we later decide to consolidate pins.
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
        target.parent.mkdir(parents=True, exist_ok=True)
        # Copy library tree
        copy_tree(prep_source, target)
        # Copy backend requirements next to the function-specific one for reference
        dest_req = target.parent / "requirements.backend.txt"
        shutil.copy2(backend_requirements, dest_req)


if __name__ == "__main__":
    main()
