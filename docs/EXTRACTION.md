# Reproducing the extraction

This documents exactly how `source/` was produced, so anyone can verify or redo it from Apple's own download. It was done on Linux (Debian, arm64); the same steps work on x86-64 Linux and, with minor changes, on macOS.

## Requirements

| Tool | Purpose |
|---|---|
| Python 3.9+ with `pip install -r tools/requirements.txt` | download a single file from the IPSW, decode SkyLight, build themes |
| [blacktop/ipsw](https://github.com/blacktop/ipsw) | decrypt Apple Encrypted Archive (`.aea`) disk images |
| [sgan81/apfs-fuse](https://github.com/sgan81/apfs-fuse) | mount APFS read-only on Linux (requires FUSE and root) |
| poppler-utils (`pdftocairo`, `pdfinfo`) | render PDFs when building themes |
| ~30 GB free disk space | the root filesystem image is 11 GB encrypted, 14 GB decrypted |

On macOS you can skip apfs-fuse and simply double-click the decrypted DMG, or copy the folders straight from a Mac running macOS 27.

## Steps

`tools/extract.sh` runs all of these in order.

### 1. Find the IPSW

Apple publishes full restore images for Apple-silicon Macs on `updates.cdn-apple.com`. The URL for 27.0.1 (26A434) is the default in `extract.sh`; others can be found through the [ipsw.me API](https://api.ipsw.me/v4/device/Mac15,3?type=ipsw).

### 2. Download only the root filesystem

The IPSW is a 26.6 GB zip. The root filesystem is its largest entry and is stored uncompressed, so it can be fetched with an HTTP range request instead of downloading everything:

```sh
python3 tools/fetch_ipsw_entry.py "$IPSW_URL" --list
python3 tools/fetch_ipsw_entry.py "$IPSW_URL" --largest work/fs.dmg.aea   # 043-70867-640.dmg.aea
```

### 3. Decrypt

Since macOS 15 the disk images are wrapped in Apple Encrypted Archive. The decryption key is published by Apple's key service and retrieved automatically by `ipsw`:

```sh
ipsw fw aea -o work work/fs.dmg.aea        # -> work/fs.dmg (raw APFS)
```

### 4. Mount and copy

```sh
sudo apfs-fuse -o allow_other work/fs.dmg work/mnt
SYS=work/mnt/root/System/Library
cp -R "$SYS/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/HIServices.framework/Versions/A/Resources/cursors" source/hiservices
cp -R "$SYS/PrivateFrameworks/AccessibilitySupport.framework/Versions/A/Frameworks/AccessibilityFoundation.framework/Versions/A/Resources/Cursors" source/accessibility/current
cp -R "$SYS/PrivateFrameworks/AccessibilitySupport.framework/Versions/A/Frameworks/AccessibilityFoundation.framework/Versions/A/Resources/Cursors-macOS16" source/accessibility/macOS16
cp "$SYS/PrivateFrameworks/SkyLight.framework/Versions/A/Resources/CursorAsset" work/
sudo umount work/mnt
```

### 5. Decode SkyLight

```sh
python3 tools/dump_skylight.py work/CursorAsset source/skylight
```

### 6. Build the themes

```sh
python3 tools/build.py
```

## Making sure nothing was missed

The whole root filesystem was searched for cursor resources (`find / -iname '*cursor*'`). Apart from the three locations above, the only matches are app-specific images that are not system pointers (Screen Sharing's remote-cursor overlays, GLUT and ImageKit legacy cursors, GraphKit zoom cursors, the login-window and Stage Manager onboarding illustrations) and they are intentionally not included.

## Checksums

| File | SHA-256 (first 16 hex) |
|---|---|
| `SkyLight.framework/Versions/A/Resources/CursorAsset` | `c3f9d1d2528f4ae4` |
