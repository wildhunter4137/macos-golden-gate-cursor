#!/usr/bin/env python3
"""Derive a Mousecape-compatible cape (macOS Sonoma / Sequoia) from the main cape.

Why: Mousecape (release 1813 and current master) refuses any cursor with more than 24 frames
("Frame count ... out of range [1...24]") and then aborts the *whole* cape ("Bailing out"), so
every cursor not yet processed stays at the system default. The Wait cursor of macOS 27 has 30
frames, which made the main cape apply only partially.

Changes relative to themes/macos/macOS27-GoldenGate.cape:
  * com.apple.coregraphics.Wait: every second frame is kept (30 -> 15 frames) and the frame
    duration is doubled, so the spin speed is unchanged.
  * com.apple.coregraphics.IBeamXOR is added (same artwork as the I-beam).
  * com.apple.cursor.39 ("Resize Square", the four-way diamond) is added (same artwork as Move),
    because macOS 27 does not ship a separate Golden Gate version of it.
Both additions exist in a stock Sequoia cursor dump; the main cape does not define them.

Requires: Python 3.9+, Pillow.
Usage:    python tools/build_cape_compat.py
"""
import copy, io, os, plistlib, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'themes', 'macos', 'macOS27-GoldenGate.cape')
DST = os.path.join(ROOT, 'themes', 'macos', 'macOS27-GoldenGate-Compat.cape')
MAX_FRAMES = 24                       # Mousecape limit


def reduce_frames(cursor, keep_every):
    """Keep every `keep_every`-th frame of the stacked sprite sheets, scale the frame duration."""
    n = cursor['FrameCount']
    idx = list(range(0, n, keep_every))
    reps = []
    for data in cursor['Representations']:
        sheet = Image.open(io.BytesIO(data)).convert('RGBA')
        fh = sheet.height // n
        assert fh * n == sheet.height, 'sprite sheet height is not a multiple of the frame count'
        out = Image.new('RGBA', (sheet.width, fh * len(idx)), (0, 0, 0, 0))
        for j, i in enumerate(idx):
            out.paste(sheet.crop((0, i * fh, sheet.width, (i + 1) * fh)), (0, j * fh))
        buf = io.BytesIO(); out.save(buf, 'PNG'); reps.append(buf.getvalue())
    cursor['Representations'] = reps
    cursor['FrameCount'] = len(idx)
    cursor['FrameDuration'] = float(cursor['FrameDuration']) * keep_every


if __name__ == '__main__':
    cape = plistlib.load(open(SRC, 'rb'))
    cur = cape['Cursors']

    wait = cur['com.apple.coregraphics.Wait']
    k = 1
    while -(-wait['FrameCount'] // k) > MAX_FRAMES:
        k += 1
    if k > 1:
        reduce_frames(wait, k)

    cur['com.apple.coregraphics.IBeamXOR'] = copy.deepcopy(cur['com.apple.coregraphics.IBeam'])
    cur['com.apple.cursor.39'] = copy.deepcopy(cur['com.apple.coregraphics.Move'])

    for key, v in cur.items():                      # nothing may exceed Mousecape's limit
        assert 1 <= v['FrameCount'] <= MAX_FRAMES, key

    cape['CapeName'] = 'macOS 27 Golden Gate (Compat)'
    cape['Identifier'] = 'local.macos27.goldengate.compat'
    plistlib.dump(cape, open(DST, 'wb'), fmt=plistlib.FMT_XML)
    print(f'Wrote {DST}: {len(cur)} cursors, Wait = {wait["FrameCount"]} frames @ {wait["FrameDuration"]:.4f}s')
