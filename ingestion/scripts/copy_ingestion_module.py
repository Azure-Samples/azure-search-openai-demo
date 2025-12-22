#!/usr/bin/env python3
"""
Copy the ingestion module to an Azure Function app directory for deployment.

This script copies the ingestion module (parsers, splitters, figures, embeddings,
storage, search, strategies, models, config, utils) to the specified function app
directory so it can be deployed with the function.

Usage:
    python copy_ingestion_module.py <function_name>

Example:
    python copy_ingestion_module.py document_extractor
"""

import os
import shutil
import sys
from pathlib import Path


def copy_ingestion_module(function_name: str) -> None:
    """Copy the ingestion module to the function app directory."""
    
    # Get the script directory and ingestion root
    script_dir = Path(__file__).parent.resolve()
    ingestion_root = script_dir.parent
    
    # Source: the ingestion module (excluding functions, infra, scripts)
    source_dir = ingestion_root
    
    # Destination: the function app directory
    function_dir = ingestion_root / "functions" / function_name
    dest_dir = function_dir / "ingestion"
    
    if not function_dir.exists():
        print(f"Error: Function directory not found: {function_dir}")
        sys.exit(1)
    
    # Remove existing ingestion module if it exists
    if dest_dir.exists():
        print(f"Removing existing ingestion module at {dest_dir}")
        shutil.rmtree(dest_dir)
    
    # Directories to copy
    dirs_to_copy = [
        "parsers",
        "splitters", 
        "figures",
        "embeddings",
        "storage",
        "search",
        "strategies",
    ]
    
    # Files to copy
    files_to_copy = [
        "__init__.py",
        "config.py",
        "models.py",
        "uploader.py",
        "utils.py",
    ]
    
    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy directories
    for dir_name in dirs_to_copy:
        src = source_dir / dir_name
        dst = dest_dir / dir_name
        if src.exists():
            print(f"Copying {src} -> {dst}")
            shutil.copytree(src, dst)
        else:
            print(f"Warning: Source directory not found: {src}")
    
    # Copy files
    for file_name in files_to_copy:
        src = source_dir / file_name
        dst = dest_dir / file_name
        if src.exists():
            print(f"Copying {src} -> {dst}")
            shutil.copy2(src, dst)
        else:
            print(f"Warning: Source file not found: {src}")
    
    print(f"Successfully copied ingestion module to {dest_dir}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python copy_ingestion_module.py <function_name>")
        print("Example: python copy_ingestion_module.py document_extractor")
        sys.exit(1)
    
    function_name = sys.argv[1]
    copy_ingestion_module(function_name)


if __name__ == "__main__":
    main()
