#!/bin/sh
set -eu
for name in planning-report pipeline-map architecture; do
  rsvg-convert "docs/assets/$name.svg" -o "docs/assets/$name.png"
done
