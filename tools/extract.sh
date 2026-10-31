#!/usr/bin/env bash
# Reproduce the extraction from Apple's public macOS 27 restore image (IPSW) on Linux.
#
# Requirements: python3 (+ tools/requirements.txt), blacktop/ipsw, apfs-fuse, FUSE (root),
#               ~30 GB free disk. See docs/EXTRACTION.md for details.
#
# Usage: tools/extract.sh [IPSW_URL] [WORKDIR]
set -euo pipefail

IPSW_URL="${1:-https://updates.cdn-apple.com/2026FallFCS/59241290-5d51-4ca8-9df4-31624b9a4eac/UniversalMac_27.0.1_26A434_Restore.ipsw}"
WORK="${2:-./work}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNT="$WORK/mnt"
mkdir -p "$WORK" "$MNT"

echo "==> 1/4 Download the root filesystem DMG (largest entry, ~11 GB, AEA-encrypted)"
python3 "$ROOT/tools/fetch_ipsw_entry.py" "$IPSW_URL" --largest "$WORK/fs.dmg.aea"

echo "==> 2/4 Decrypt AEA (key is fetched from Apple's public key service by ipsw)"
ipsw fw aea -o "$WORK" "$WORK/fs.dmg.aea"
rm -f "$WORK/fs.dmg.aea"

echo "==> 3/4 Mount the APFS image read-only"
sudo apfs-fuse -o allow_other "$WORK/fs.dmg" "$MNT"
SYS="$MNT/root/System/Library"

echo "==> 4/4 Copy cursor sources"
OUT="$ROOT/source"
rm -rf "$OUT/hiservices" "$OUT/skylight" "$OUT/accessibility"
mkdir -p "$OUT/accessibility"
sudo cp -R "$SYS/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/HIServices.framework/Versions/A/Resources/cursors" "$OUT/hiservices"
AF="$SYS/PrivateFrameworks/AccessibilitySupport.framework/Versions/A/Frameworks/AccessibilityFoundation.framework/Versions/A/Resources"
sudo cp -R "$AF/Cursors" "$OUT/accessibility/current"
sudo cp -R "$AF/Cursors-macOS16" "$OUT/accessibility/macOS16"
sudo cp "$SYS/PrivateFrameworks/SkyLight.framework/Versions/A/Resources/CursorAsset" "$WORK/CursorAsset"
sudo chown -R "$(id -u):$(id -g)" "$OUT" "$WORK/CursorAsset"
python3 "$ROOT/tools/dump_skylight.py" "$WORK/CursorAsset" "$OUT/skylight"

sudo umount "$MNT"
echo "Done. Sources are in $OUT. Build the themes with: python3 tools/build.py"
