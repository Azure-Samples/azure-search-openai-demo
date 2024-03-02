#!/bin/sh

# Processes PDF link collections in current directory,
# and downloads them to respective subfolders 

# Check that required commands exist on user system
if ! command -v wget >/dev/null 2>&1;
then
  echo "This script needs wget to run!"
  exit 1
fi

if ! command -v basename >/dev/null 2>&1;
then
  echo "This script needs basename to run!"
  exit 1
fi

# Find and process link collections
for filename in data-collections/*.urls; do
  collectionname=$(basename "${filename}" .urls)
  echo "Fetching collection: ${collectionname}"

  outputdir="../data/collections/${collectionname}"
  mkdir -p "${outputdir}"

  # Rate limit to 500kB/s and wait 2 seconds between each file.
  wget -i "${filename}" -nc -P "${outputdir}" \
    -e robots=on --accept '*.pdf' \
    --limit-rate=500k --wait=2 \
    -q --show-progress

done
