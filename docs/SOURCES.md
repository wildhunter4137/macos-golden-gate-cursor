# Sources and file formats

All files in [`source/`](../source) were copied unmodified from the root filesystem of Apple's public restore image:

| | |
|---|---|
| Image | `UniversalMac_27.0.1_26A434_Restore.ipsw` |
| URL | `https://updates.cdn-apple.com/2026FallFCS/59241290-5d51-4ca8-9df4-31624b9a4eac/UniversalMac_27.0.1_26A434_Restore.ipsw` |
| macOS | 27.0.1 Golden Gate, build 26A434 (Apple silicon) |
| Root filesystem DMG | `043-70867-640.dmg.aea` (11.27 GB, AEA-encrypted APFS) |

## 1. HIServices vector cursors → `source/hiservices/`

```
/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/
    HIServices.framework/Versions/A/Resources/cursors/
```

One folder per cursor, each containing:

- `cursor.pdf` – vector artwork. Animated cursors stack their frames vertically on one page (for example `busybutclickable` is 28 × 600 pt = 15 frames of 28 × 40 pt).
- `info.plist` – metadata read by the window server:

| Key | Meaning |
|---|---|
| `hotx`, `hoty` | Hotspot in points from the top-left corner |
| `frames`, `delay` | Frame count and seconds per frame for animated cursors |
| `blur`, `shadowcolor`, `shadowoffsetx`, `shadowoffsety` | Drop shadow drawn at runtime (not part of the PDF) |
| `vectoronly` | Rendered from the PDF at any scale |

`cursors/macos27/` is new in macOS 27 and contains only `pointinghand`, `openhand` and `closedhand`: the glove-style hands that replace the Tahoe versions still present one level up. All other cursors in this folder are unchanged from macOS 26 Tahoe.

`screenshotselection/cursor_1only_.png` is a raster copy shipped by Apple alongside the PDF.

## 2. SkyLight bitmap cursors → `source/skylight/`

```
/System/Library/PrivateFrameworks/SkyLight.framework/Versions/A/Resources/CursorAsset
```

The arrow, the text I-beam and the spinning wait cursor are not in HIServices. The window server draws them from `CursorAsset`, a universal Mach-O dylib with no code. Its single exported symbol `_cursors` (in `__DATA_CONST,__const`) is a table of `(id, pointer)` pairs; each record is:

```
double  width, height        // points
double  hotX, hotY           // points
uint64  frameCount
float   frameDuration        // seconds (padded to 8 bytes)
uint64  representationCount
ptr     representations[n]   // into __TEXT,__const
```

and each representation is

```
uint64  pixelWidth, pixelHeight
double  hotX, hotY           // pixels
uint8   pixels[w * h * 4 * frameCount]   // premultiplied BGRA, frames stacked vertically
```

[`tools/dump_skylight.py`](../tools/dump_skylight.py) decodes it into `id<N>_<w>x<h>.png` plus `info.json`. The ids found in macOS 27:

| id | Size (pt) | Content | Used by the themes |
|---|---|---|---|
| 100 | 28 × 40 | Arrow (current design) | ✔ `arrow` |
| 101 | 23 × 22 | I-beam (current design) | ✔ `ibeam` |
| 7 | 24 × 24, 30 frames @ 60 fps | Spinning wait cursor | ✔ `wait` |
| 0 | 17 × 23 | Arrow (legacy design) | – |
| 1 | 9 × 18 | I-beam (legacy design) | – |
| 5 | 11 × 16 | Small legacy arrow | – |
| 2, 3, 4, 6, 8 | 4–8 | Tiny placeholder / empty cursors | – |

`CursorAsset_base`, which sits next to it, contains exactly the same images in a different layout and is not included.

## 3. Accessibility colour layers → `source/accessibility/`

```
/System/Library/PrivateFrameworks/AccessibilitySupport.framework/Versions/A/Frameworks/
    AccessibilityFoundation.framework/Versions/A/Resources/Cursors
    AccessibilityFoundation.framework/Versions/A/Resources/Cursors-macOS16
```

When a custom pointer outline or fill colour is chosen in **System Settings → Accessibility → Display → Pointer**, macOS rebuilds cursors from these single-colour masks: each cursor has a `-top` and a `-bottom` PDF layer (and an `-overlay` for the coloured badge on *copy* and *not allowed*) that are tinted separately. The two folders hold two designs: `Cursors-macOS16` matches the rounded arrow and hands introduced with macOS 26, while `Cursors` uses the classic sharp arrow and glove hands; `default-pointer-*.png` and `default-iBeam-*.png` are pre-rendered previews.

These layers are included for completeness and for anyone who wants to generate recoloured variants. They are not used by the default themes.

## Light and dark mode

macOS has no separate cursor artwork for light and dark appearance. The window server draws the same black-filled, white-outlined pointers in both modes; the only colour changes come from the Accessibility options described above.

## How the themes are generated

[`tools/build.py`](../tools/build.py) renders every cursor from the sources above:

- HIServices PDFs are rasterised with poppler (`pdftocairo`) at each target scale, and the shadow described in `info.plist` is baked in (macOS adds it at runtime).
- SkyLight bitmaps are used at their native scale when available, otherwise downsampled from the largest representation.
- For Windows and Linux each image is placed on a square canvas (32 px = 100 %); the hotspot is carried over and, where the artwork would overflow the canvas, the image is shifted rather than cropped.
- Animated cursors become `.ani` (Windows), multi-frame Xcursor (Linux) and multi-frame cape entries (Mousecape), keeping Apple's frame timing.
