#!/usr/bin/env bash
set -euo pipefail

# Directory containing files to index
SO_DIR="data"

# POSIX extended regex patterns for file-name classification
# Solution Objects: slide decks 1-7, plus other technical assets (Gateway, Monitoring, Security, Fabric, etc.)
SO_PATTERN='((^[1-7] - )|(Premium|Fabric|Gateway|Monitoring|Security|Storage|Data Governance))'
# Employee Info: HR / policy / benefit docs
# Enable case-insensitive regex matching
shopt -s nocasematch
EI_PATTERN='(Employee|Handbook|Enrollment|Bonus|Career|Guide|Benefit|Onboarding|Periodic|Essentials|OE|[Gg]lossary)'

# Build file lists by inspecting basenames
SO_FILES=()
EI_FILES=()
while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  if [[ $base =~ ${EI_PATTERN} ]]; then
    EI_FILES+=("$f")
  else
    SO_FILES+=("$f")
  fi
done < <(find "$SO_DIR" -maxdepth 1 -type f -print0)

if [[ ${#SO_FILES[@]} -eq 0 && ${#EI_FILES[@]} -eq 0 ]]; then
  echo "No files found in $SO_DIR" >&2
  exit 1
fi

PREPDOCS_SCRIPT="app/backend/prepdocs.py"
if [[ ! -f $PREPDOCS_SCRIPT ]]; then
  echo "prepdocs.py not found at $PREPDOCS_SCRIPT" >&2
  exit 1
fi

# Unset ADLS Gen2 variables to force local ingestion
unset AZURE_ADLS_GEN2_STORAGE_ACCOUNT AZURE_ADLS_GEN2_FILESYSTEM AZURE_ADLS_GEN2_FILESYSTEM_PATH

# Index Solution Objects one-by-one
for f in "${SO_FILES[@]}"; do
  echo "Indexing Solution Object: $f"
  env LOADING_MODE_FOR_AZD_ENV_VARS=no-override \
      AZURE_ADLS_GEN2_STORAGE_ACCOUNT="" \
      AZURE_ADLS_GEN2_FILESYSTEM="" \
      AZURE_ADLS_GEN2_FILESYSTEM_PATH="" \
      python "$PREPDOCS_SCRIPT" -v --category "Solution Objects" "$f"
done

# Index Employee Info one-by-one
for f in "${EI_FILES[@]}"; do
  echo "Indexing Employee Info: $f"
  env LOADING_MODE_FOR_AZD_ENV_VARS=no-override \
      AZURE_ADLS_GEN2_STORAGE_ACCOUNT="" \
      AZURE_ADLS_GEN2_FILESYSTEM="" \
      AZURE_ADLS_GEN2_FILESYSTEM_PATH="" \
      python "$PREPDOCS_SCRIPT" -v --category "Employee Info" "$f"
done

echo "Reindexing complete." 