#!/usr/bin/env python3
"""Build an enlarged Windows variant of the macOS 27 Golden Gate cursors.

Writes themes/windows/macOS27-GoldenGate-Large/ without touching the original theme.
Reuses the drawing / .cur / .ani code of build.py, but:
  * renders the artwork SCALE times larger inside the same pixel canvas (hotspots scale too),
  * renders PDFs with PyMuPDF, so poppler is not needed,
  * adds 192 and 256 px images to static cursors so very large pointer sizes stay sharp.

Requires: Python 3.9+, Pillow, PyMuPDF (pip install pymupdf).
Usage:    python tools/build_windows_large.py [scale]      # default scale 1.1
"""
import os, plistlib, shutil, struct, sys

try:
    import pymupdf as fitz        # PyMuPDF >= 1.24.3
except ImportError:
    import fitz                   # older PyMuPDF
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build                      # noqa: E402  (importing build has no side effects besides a temp dir)

SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 1.1
NAME = 'macOS27-GoldenGate-Large'
SCHEME = 'macOS 27 Golden Gate Large'
STATIC_SIZES = [32, 48, 64, 96, 128, 192, 256]    # pointer size 1 .. 15 (32 px per 100 %)
ANIMATED_SIZES = [32, 48, 64, 96, 128]            # animated files stay at the original sizes (file size)


def pdf_cursor_mupdf(name, folder):
    """Same as build.pdf_cursor, but rasterises with PyMuPDF instead of poppler."""
    p = plistlib.load(open(os.path.join(folder, 'info.plist'), 'rb'))
    frames = int(p.get('frames', 1) or 1)
    doc = fitz.open(os.path.join(folder, 'cursor.pdf'))
    page = doc[0]
    pw, ph = page.rect.width, page.rect.height
    blur = float(p.get('blur', 0) or 0)
    color = p.get('shadowcolor')
    ox, oy = float(p.get('shadowoffsetx', 0) or 0), -float(p.get('shadowoffsety', 0) or 0)
    cache = {}

    def render(scale):
        if scale in cache:
            return cache[scale]
        W, H = max(1, round(pw * scale)), max(1, round(ph * scale))
        pix = page.get_pixmap(matrix=fitz.Matrix(W / pw, H / ph), alpha=True)
        sheet = Image.frombytes('RGBA', (pix.width, pix.height), pix.samples)
        if sheet.size != (W, H):
            sheet = sheet.resize((W, H), Image.LANCZOS)
        # PyMuPDF returns straight (non-premultiplied) RGBA, same as the poppler path
        fh, result = H / frames, []
        for i in range(frames):
            f = sheet.crop((0, round(i * fh), W, round((i + 1) * fh)))
            if color and blur > 0:
                a = f.getchannel('A').point(lambda v: int(v * color[-1]))
                sh = Image.new('RGBA', f.size, (0, 0, 0, 0)); sh.putalpha(a)
                sh = sh.filter(build.ImageFilter.GaussianBlur(blur * scale / 2))
                base = Image.new('RGBA', f.size, (0, 0, 0, 0))
                base.alpha_composite(sh, (round(ox * scale), round(oy * scale)))
                base.alpha_composite(f); f = base
            result.append(f)
        cache[scale] = result
        return result

    return build.Cursor(name, pw, ph / frames, float(p['hotx']), float(p['hoty']), frames,
                        float(p.get('delay', 0) or 0), render)


def enlarge(c, k):
    """Same cursor drawn k times larger: render at scale*k, hotspot * k."""
    return build.Cursor(c.name, c.w * k, c.h * k, c.hx * k, c.hy * k, c.frames, c.delay,
                        lambda s: c.render(s * k))


def write_cursor(c, base):
    sizes = STATIC_SIZES if c.frames == 1 else ANIMATED_SIZES
    per = [build.square(c, N / 32, N) for N in sizes]
    if c.frames == 1:
        open(base + '.cur', 'wb').write(build._cur([(N, hx, hy, build._dib(fr[0])) for N, (fr, hx, hy) in zip(sizes, per)]))
        return
    icons = [build._cur([(N, hx, hy, build._dib(fr[k])) for N, (fr, hx, hy) in zip(sizes, per)]) for k in range(c.frames)]
    jiffies = max(1, round(c.delay * 60))
    chunk = lambda t, d: t + struct.pack('<I', len(d)) + d + (b'\0' if len(d) % 2 else b'')
    anih = struct.pack('<9I', 36, c.frames, c.frames, 0, 0, 0, 0, jiffies, 1)
    body = b'ACON' + chunk(b'anih', anih) + chunk(b'LIST', b'fram' + b''.join(chunk(b'icon', i) for i in icons))
    open(base + '.ani', 'wb').write(b'RIFF' + struct.pack('<I', len(body)) + body)


if __name__ == '__main__':
    root = build.ROOT
    orig = os.path.join(root, 'themes', 'windows', build.THEME)
    out = os.path.join(root, 'themes', 'windows', NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    build.pdf_cursor = pdf_cursor_mupdf            # load_all() looks the name up at call time
    cursors = build.load_all()
    for n, c in cursors.items():
        write_cursor(enlarge(c, SCALE), os.path.join(out, n))
        print('built', n)

    # installer: same script as the original, pointed at its own folder and scheme name
    bat = open(os.path.join(orig, 'install.bat'), 'rb').read().decode('utf-8')
    bat = bat.replace(build.THEME, NAME).replace('macOS 27 Golden Gate', SCHEME)
    assert NAME in bat and SCHEME in bat
    open(os.path.join(out, 'install.bat'), 'w', newline='').write(bat)

    open(os.path.join(out, 'README.txt'), 'w', newline='').write(
        f'macOS 27 Golden Gate cursors for Windows 10 / 11 - LARGE ({SCALE:g}x)\r\n\r\n'
        'Same cursors as the normal Windows package, drawn slightly larger.\r\n\r\n'
        'Double-click install.bat and confirm the administrator prompt.\r\n'
        'It copies the cursors, registers the "' + SCHEME + '" scheme, activates it and reloads the\r\n'
        'live cursor set - no further steps needed. It can be installed next to the normal package.\r\n\r\n'
        'Static cursors contain 32-256 px images (pointer size 1-15); animated cursors contain 32-128 px.\r\n\r\n'
        'Undo: choose "Windows Default" (or the normal scheme) in Mouse settings > Pointers and click Apply.\r\n')
    shutil.rmtree(build.TMP, ignore_errors=True)
    print(f'Wrote {out} (scale {SCALE})')
