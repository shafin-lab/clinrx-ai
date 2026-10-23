#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_id=$(date -u '+%Y%m%dT%H%M%SZ')
out="$root/review-evidence/m10/builds/preview-$build_id"
mkdir -p "$(dirname -- "$out")"
if [ -e "$out" ]; then
  echo "Refusing to replace existing preview build: $out" >&2
  exit 1
fi

cd "$root/frontend"
VITE_SYNTHETIC_HOSTED=true \
VITE_SYNTHETIC_RF1=true \
VITE_SYNTHETIC_RF2=true \
VITE_SYNTHETIC_AUTHORING=true \
VITE_SYNTHETIC_WEIGHT_ENTRY=true \
VITE_SYNTHETIC_ANTIBIOTICS=true \
VITE_SYNTHETIC_M10=true \
npm run build -- --outDir "../review-evidence/m10/builds/preview-$build_id" --emptyOutDir

printf '%s\n' "$out"
