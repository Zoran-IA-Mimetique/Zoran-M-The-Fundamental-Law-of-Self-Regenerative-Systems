#!/usr/bin/env bash
set -e
OUT=SHA512i.txt
echo "# SHA-512 checksums generated on $(date -u)" > "$OUT"
# Include files up to two levels deep, excluding .git and the checksum file itself
for f in $(find . -maxdepth 2 -type f -not -path "./.git/*" -not -name "$OUT"); do
  sha512sum "$f" >> "$OUT"
done

echo "SHA-512 sums written to $OUT"