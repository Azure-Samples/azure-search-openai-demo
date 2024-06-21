#!/bin/bash

echo "deleting all md5 files"
find data -type f -name "*.md5" -delete

azd up