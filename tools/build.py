#!/usr/bin/env python3
"""Build cursor themes for macOS (Mousecape), Windows (.cur/.ani + install.inf) and Linux (Xcursor)
from the extracted macOS sources in ../source.

Requires: Python 3.9+, Pillow, poppler-utils (pdftocairo, pdfinfo).
Usage:    python3 tools/build.py            # writes ./themes
"""
import io, json, os, plistlib, shutil, struct, subprocess, tempfile
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_HIS = os.path.join(ROOT, 'source', 'hiservices')
SRC_SKY = os.path.join(ROOT, 'source', 'skylight')
OUT = os.path.join(ROOT, 'themes')
THEME = 'macOS27-GoldenGate'
TMP = tempfile.mkdtemp(prefix='cursors-')

# SkyLight ids used by macOS 27 (see docs/SOURCES.md)
SKYLIGHT_USED = {'arrow': 100, 'ibeam': 101, 'wait': 7}


class Cursor:
    def __init__(self, name, w, h, hx, hy, frames, delay, render):
        self.name, self.w, self.h, self.hx, self.hy = name, w, h, hx, hy
        self.frames, self.delay, self.render = frames, delay, render


def pdf_cursor(name, folder):
    """Vector cursor from HIServices: cursor.pdf (frames stacked vertically) + info.plist.
    The shadow described in info.plist is drawn at runtime by macOS, so we bake it in."""
    p = plistlib.load(open(os.path.join(folder, 'info.plist'), 'rb'))
    frames = int(p.get('frames', 1) or 1)
    info = subprocess.run(['pdfinfo', os.path.join(folder, 'cursor.pdf')], capture_output=True, text=True).stdout
    size = [l for l in info.splitlines() if l.startswith('Page size')][0].split(':')[1].split('pts')[0]
    pw, ph = (float(v) for v in size.split('x'))
    blur = float(p.get('blur', 0) or 0)
    color = p.get('shadowcolor')
    ox, oy = float(p.get('shadowoffsetx', 0) or 0), -float(p.get('shadowoffsety', 0) or 0)
    cache = {}

    def render(scale):
        if scale in cache:
            return cache[scale]
        W, H = max(1, round(pw * scale)), max(1, round(ph * scale))
        out = os.path.join(TMP, f'{name}_{scale}')
        subprocess.run(['pdftocairo', '-png', '-transp', '-singlefile', '-scale-to-x', str(W), '-scale-to-y', str(H),
                        os.path.join(folder, 'cursor.pdf'), out], check=True)
        sheet = Image.open(out + '.png').convert('RGBA')
        fh, result = H / frames, []
        for i in range(frames):
            f = sheet.crop((0, round(i * fh), W, round((i + 1) * fh)))
            if color and blur > 0:
                a = f.getchannel('A').point(lambda v: int(v * color[-1]))
                sh = Image.new('RGBA', f.size, (0, 0, 0, 0)); sh.putalpha(a)
                sh = sh.filter(ImageFilter.GaussianBlur(blur * scale / 2))
                base = Image.new('RGBA', f.size, (0, 0, 0, 0))
                base.alpha_composite(sh, (round(ox * scale), round(oy * scale)))
                base.alpha_composite(f); f = base
            result.append(f)
        cache[scale] = result
        return result

    return Cursor(name, pw, ph / frames, float(p['hotx']), float(p['hoty']), frames,
                  float(p.get('delay', 0) or 0), render)


def skylight_cursor(name, cid):
    """Bitmap cursor from SkyLight CursorAsset (already includes its shadow)."""
    info = json.load(open(os.path.join(SRC_SKY, 'info.json')))[str(cid)]
    reps, frames = info['reps'], info['frames']

    def render(scale):
        tw, th = round(info['w'] * scale), round(info['h'] * scale)
        exact = [r for r in reps if r[0] == tw]
        r = exact[0] if exact else reps[-1]               # otherwise downsample the largest
        sheet = Image.open(os.path.join(SRC_SKY, f'id{cid}_{r[0]}x{r[1]}.png')).convert('RGBA')
        out = []
        for k in range(frames):
            f = sheet.crop((0, k * r[1], r[0], (k + 1) * r[1]))
            out.append(f if f.size == (tw, th) else f.resize((tw, th), Image.LANCZOS))
        return out

    return Cursor(name, info['w'], info['h'], info['hot'][0], info['hot'][1], frames, info['delay'], render)


def load_all():
    cur = {}
    for d in sorted(os.listdir(SRC_HIS)):
        path = os.path.join(SRC_HIS, d)
        if d != 'macos27' and os.path.isdir(path):
            cur[d] = pdf_cursor(d, path)
    for d in sorted(os.listdir(os.path.join(SRC_HIS, 'macos27'))):   # Golden Gate glove hands override
        cur[d] = pdf_cursor(d, os.path.join(SRC_HIS, 'macos27', d))
    for name, cid in SKYLIGHT_USED.items():
        cur[name] = skylight_cursor(name, cid)
    return cur


def square(c, scale, N):
    """Place a cursor on an NxN canvas (Windows/X11 want square images). Shifts or shrinks to fit."""
    frames = c.render(scale)
    hx, hy = c.hx * scale, c.hy * scale
    bb = None
    for f in frames:
        b = f.getbbox()
        if b:
            bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
    bb = bb or (0, 0, 1, 1)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    out = []
    if bw > N or bh > N:
        k = N / max(bw, bh)
        for f in frames:
            cv = Image.new('RGBA', (N, N), (0, 0, 0, 0))
            cv.alpha_composite(f.crop(bb).resize((max(1, round(bw * k)), max(1, round(bh * k))), Image.LANCZOS))
            out.append(cv)
        hx, hy = (hx - bb[0]) * k, (hy - bb[1]) * k
    else:
        dx = max(min(0, N - bb[2]), -bb[0]); dy = max(min(0, N - bb[3]), -bb[1])
        for f in frames:
            big = Image.new('RGBA', (max(N, f.width), max(N, f.height)), (0, 0, 0, 0))
            big.paste(f, (dx, dy), f)
            out.append(big.crop((0, 0, N, N)))
        hx, hy = hx + dx, hy + dy
    clamp = lambda v: min(N - 1, max(0, round(v)))
    return out, clamp(hx), clamp(hy)


# ---------------------------------------------------------------- Windows
WIN_SIZES = [32, 48, 64, 96, 128]          # 100% .. 400% scaling
# Windows refuses an .ani whose frames hold an image starting beyond byte 65535 of the frame
# ("could not be found or is corrupted"). With 32+48+64+96 px the last image starts at ~31 KB;
# adding 128 px pushes it past the limit, so animated cursors stop at 96 px.
ANI_SIZES = [32, 48, 64, 96]


def _dib(im):
    w, h = im.size; px = im.load()
    header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    xor, mask, row_bytes = bytearray(), bytearray(), ((w + 31) // 32) * 4
    for y in range(h - 1, -1, -1):
        row = bytearray(row_bytes)
        for x in range(w):
            r, g, b, a = px[x, y]
            xor += bytes((b, g, r, a))
            if a == 0:
                row[x // 8] |= 0x80 >> (x % 8)
        mask += row
    return header + bytes(xor) + bytes(mask)


def _cur(entries):
    offset, dirs, body = 6 + 16 * len(entries), b'', b''
    for N, hx, hy, data in entries:
        dirs += struct.pack('<BBBBHHII', N % 256, N % 256, 0, 0, hx, hy, len(data), offset + len(body))
        body += data
    return struct.pack('<HHH', 0, 2, len(entries)) + dirs + body


def write_windows_cursor(c, base):
    sizes = WIN_SIZES if c.frames == 1 else ANI_SIZES
    per = [square(c, N / 32, N) for N in sizes]
    if c.frames == 1:
        open(base + '.cur', 'wb').write(_cur([(N, hx, hy, _dib(fr[0])) for N, (fr, hx, hy) in zip(sizes, per)]))
        return os.path.basename(base) + '.cur'
    icons = [_cur([(N, hx, hy, _dib(fr[k])) for N, (fr, hx, hy) in zip(sizes, per)]) for k in range(c.frames)]
    jiffies = max(1, round(c.delay * 60))
    chunk = lambda t, d: t + struct.pack('<I', len(d)) + d + (b'\0' if len(d) % 2 else b'')
    anih = struct.pack('<9I', 36, c.frames, c.frames, 0, 0, 0, 0, jiffies, 1)
    body = b'ACON' + chunk(b'anih', anih) + chunk(b'LIST', b'fram' + b''.join(chunk(b'icon', i) for i in icons))
    open(base + '.ani', 'wb').write(b'RIFF' + struct.pack('<I', len(body)) + body)
    return os.path.basename(base) + '.ani'


WIN_ROLES = [  # registry value, cursor (None = keep Windows default; macOS has no equivalent)
    ('Arrow', 'arrow'), ('Help', 'help'), ('AppStarting', 'busybutclickable'), ('Wait', 'wait'),
    ('Crosshair', 'cross'), ('IBeam', 'ibeam'), ('NWPen', None), ('No', 'notallowed'),
    ('SizeNS', 'resizenorthsouth'), ('SizeWE', 'resizeeastwest'), ('SizeNWSE', 'resizenorthwestsoutheast'),
    ('SizeNESW', 'resizenortheastsouthwest'), ('SizeAll', 'move'), ('UpArrow', None), ('Hand', 'pointinghand'),
    ('Pin', None), ('Person', None)]


def build_windows(cursors):
    d = os.path.join(OUT, 'windows', THEME); os.makedirs(d)
    files = {n: write_windows_cursor(c, os.path.join(d, n)) for n, c in cursors.items()}
    P = '%10%\\%CUR_DIR%\\'
    path = lambda n: (P + files[n]) if n else ''
    lines = ['; macOS 27 Golden Gate cursor scheme for Windows 10 / 11',
             '; Right-click > Install (Windows 11: Show more options > Install)', '',
             '[Version]', 'signature="$CHICAGO$"', '',
             '[DefaultInstall]', 'CopyFiles = Scheme.Cur', 'AddReg    = Scheme.Reg, Wreg', '',
             '[DestinationDirs]', 'Scheme.Cur = 10,"%CUR_DIR%"', '',
             '[Scheme.Reg]',
             'HKCU,"Control Panel\\Cursors\\Schemes","%SCHEME_NAME%",,"' + ','.join(path(v) for _, v in WIN_ROLES) + '"', '',
             '[Wreg]', 'HKCU,"Control Panel\\Cursors",,0x00020000,"%SCHEME_NAME%"']
    lines += [f'HKCU,"Control Panel\\Cursors",{k},0x00020000,"{path(v)}"' for k, v in WIN_ROLES]
    lines += ['', '[Scheme.Cur]'] + sorted(files.values()) + ['', '[Strings]',
              f'CUR_DIR     = "Cursors\\{THEME}"', 'SCHEME_NAME = "macOS 27 Golden Gate"']
    open(os.path.join(d, 'install.inf'), 'w', newline='\r\n').write('\n'.join(lines) + '\n')


# ---------------------------------------------------------------- Linux (Xcursor)
X_SIZES = [24, 32, 48, 64, 96]
X_ALIASES = {
    'arrow': ['default', 'left_ptr', 'top_left_arrow', 'arrow', 'right_ptr'],
    'ibeam': ['text', 'xterm', 'ibeam'],
    'ibeamvertical': ['vertical-text'],
    'wait': ['wait', 'watch'],
    'busybutclickable': ['progress', 'left_ptr_watch', 'half-busy',
                         '08e8e1c95fe2fc01f976f1e063a24ccd', '3ecb610c1bf2410f44200f48c40d3599'],
    'pointinghand': ['pointer', 'hand', 'hand1', 'hand2',
                     '9d800788f1b08800ae810202380a0822', 'e29285e634086352946a0e7090d73106'],
    'openhand': ['grab', 'openhand', '5aca4d189052212118709018842178c0', '9141b49c8149039304290b508d208c40'],
    'closedhand': ['grabbing', 'closedhand', 'dnd-none', '208530c400c041818281048008011002'],
    'cross': ['crosshair', 'cross', 'tcross', 'cross_reverse', 'diamond_cross'],
    'notallowed': ['not-allowed', 'no-drop', 'forbidden', 'crossed_circle', 'circle', '03b6e0fcb3499374a867c041f52298f0'],
    'help': ['help', 'question_arrow', 'whats_this', 'left_ptr_help',
             'd9ce0ab605698f320427677b458ad60b', '5c6cd98b3f3ebcb1f9c7f1c204630408'],
    'copy': ['copy', 'dnd-copy', '1081e37283d90000800003c07f3ef6bf', '6407b0e94181790501fd1e167b474872'],
    'makealias': ['alias', 'link', 'dnd-link', '3085a0e285430894940527032f8b26df', '640fb0e74195791501fd1ed57b41487f'],
    'contextualmenu': ['context-menu'],
    'move': ['move', 'fleur', 'all-scroll', 'size_all', 'dnd-move',
             '4498f0e0c1937ffe01fd06f973665830', '9081237383d90e509aa00f00170e968f'],
    'resizeleftright': ['col-resize', 'split_h', 'sb_h_double_arrow', '14fef782d02440884392942c11205230'],
    'resizeupdown': ['row-resize', 'split_v', 'sb_v_double_arrow', '2870a09082c103050810ffdffffe0204'],
    'resizeeastwest': ['ew-resize', 'h_double_arrow', 'size_hor', 'we-resize', '028006030e0e7ebffc7f7070c0600140'],
    'resizenorthsouth': ['ns-resize', 'v_double_arrow', 'size_ver', '00008160000006810000408080010102'],
    'resizenorthwestsoutheast': ['nwse-resize', 'size_fdiag', 'c7088f0f3e6c8088236ef8e1e3e70000'],
    'resizenortheastsouthwest': ['nesw-resize', 'size_bdiag', 'fcf1c3c7cd4491d801f1e1c78f100000'],
    'resizenorth': ['n-resize', 'top_side'], 'resizesouth': ['s-resize', 'bottom_side'],
    'resizeeast': ['e-resize', 'right_side'], 'resizewest': ['w-resize', 'left_side'],
    'resizenortheast': ['ne-resize', 'top_right_corner'], 'resizenorthwest': ['nw-resize', 'top_left_corner'],
    'resizesoutheast': ['se-resize', 'bottom_right_corner'], 'resizesouthwest': ['sw-resize', 'bottom_left_corner'],
    'resizeup': ['up-arrow', 'sb_up_arrow'], 'resizedown': ['sb_down_arrow'],
    'resizeleft': ['sb_left_arrow'], 'resizeright': ['sb_right_arrow'],
    'zoomin': ['zoom-in'], 'zoomout': ['zoom-out'], 'cell': ['cell', 'plus'],
}


def write_xcursor(c, path):
    images = []
    for N in X_SIZES:
        frames, hx, hy = square(c, N / 32, N)
        images += [(N, hx, hy, f) for f in frames]
    delay = max(1, round(c.delay * 1000)) if c.frames > 1 else 0
    pos, toc, chunks = 16 + 12 * len(images), b'', b''
    for N, hx, hy, f in images:
        toc += struct.pack('<III', 0xFFFD0002, N, pos + len(chunks))
        chunks += struct.pack('<9I', 36, 0xFFFD0002, N, 1, N, N, hx, hy, delay) + f.tobytes('raw', 'BGRa')
    open(path, 'wb').write(b'Xcur' + struct.pack('<III', 16, 0x10000, len(images)) + toc + chunks)


def build_linux(cursors):
    d = os.path.join(OUT, 'linux', THEME); cd = os.path.join(d, 'cursors'); os.makedirs(cd)
    for n, c in cursors.items():
        write_xcursor(c, os.path.join(cd, n))
    for src, names in X_ALIASES.items():
        for a in names:
            if not os.path.lexists(os.path.join(cd, a)):
                os.symlink(src, os.path.join(cd, a))
    open(os.path.join(d, 'index.theme'), 'w').write(
        f'[Icon Theme]\nName={THEME}\nComment=macOS 27 Golden Gate cursors\n')
    sh = os.path.join(d, 'install.sh')
    open(sh, 'w').write(f'''#!/bin/sh
# Install for the current user:  sh install.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.icons"
rm -rf "$HOME/.icons/{THEME}"
cp -a "$DIR" "$HOME/.icons/{THEME}"
command -v gsettings >/dev/null 2>&1 && gsettings set org.gnome.desktop.interface cursor-theme '{THEME}' 2>/dev/null || true
command -v plasma-apply-cursortheme >/dev/null 2>&1 && plasma-apply-cursortheme {THEME} || true
echo "Installed to ~/.icons/{THEME}. If it did not switch automatically, select it in your cursor settings and log in again."
''')
    os.chmod(sh, 0o755)


# ---------------------------------------------------------------- macOS (Mousecape .cape)
CAPE_IDS = {
    'arrow': ['com.apple.coregraphics.Arrow'], 'ibeam': ['com.apple.coregraphics.IBeam'],
    'wait': ['com.apple.coregraphics.Wait'], 'move': ['com.apple.coregraphics.Move'],
    'copy': ['com.apple.coregraphics.Copy', 'com.apple.cursor.5'],
    'makealias': ['com.apple.coregraphics.Alias', 'com.apple.cursor.2'],
    'contextualmenu': ['com.apple.coregraphics.ArrowCtx', 'com.apple.cursor.24'],
    'notallowed': ['com.apple.cursor.3'], 'busybutclickable': ['com.apple.cursor.4'],
    'cross': ['com.apple.cursor.7', 'com.apple.cursor.8'], 'screenshotselection': ['com.apple.cursor.9'],
    'screenshotwindow': ['com.apple.cursor.10'], 'closedhand': ['com.apple.cursor.11'],
    'openhand': ['com.apple.cursor.12'], 'pointinghand': ['com.apple.cursor.13'],
    'countinguphand': ['com.apple.cursor.14'], 'countingdownhand': ['com.apple.cursor.15'],
    'countingupandownhand': ['com.apple.cursor.16'], 'resizeleft': ['com.apple.cursor.17'],
    'resizeright': ['com.apple.cursor.18'], 'resizeleftright': ['com.apple.cursor.19'],
    'cell': ['com.apple.cursor.20', 'com.apple.cursor.41'], 'resizeup': ['com.apple.cursor.21'],
    'resizedown': ['com.apple.cursor.22'], 'resizeupdown': ['com.apple.cursor.23'],
    'poof': ['com.apple.cursor.25'], 'ibeamvertical': ['com.apple.cursor.26'],
    'resizeeast': ['com.apple.cursor.27'], 'resizeeastwest': ['com.apple.cursor.28'],
    'resizenortheast': ['com.apple.cursor.29'], 'resizenortheastsouthwest': ['com.apple.cursor.30'],
    'resizenorth': ['com.apple.cursor.31'], 'resizenorthsouth': ['com.apple.cursor.32'],
    'resizenorthwest': ['com.apple.cursor.33'], 'resizenorthwestsoutheast': ['com.apple.cursor.34'],
    'resizesoutheast': ['com.apple.cursor.35'], 'resizesouth': ['com.apple.cursor.36'],
    'resizesouthwest': ['com.apple.cursor.37'], 'resizewest': ['com.apple.cursor.38'],
    'help': ['com.apple.cursor.40'], 'zoomin': ['com.apple.cursor.42'], 'zoomout': ['com.apple.cursor.43'],
}


def build_macos(cursors):
    d = os.path.join(OUT, 'macos'); os.makedirs(d)
    entries = {}
    for name, ids in CAPE_IDS.items():
        c, reps = cursors[name], []
        for s in (1, 2, 5, 10):
            frames = c.render(s)
            sheet = Image.new('RGBA', (frames[0].width, frames[0].height * len(frames)), (0, 0, 0, 0))
            for k, f in enumerate(frames):
                sheet.paste(f, (0, k * frames[0].height))
            buf = io.BytesIO(); sheet.save(buf, 'PNG'); reps.append(buf.getvalue())
        entry = {'FrameCount': c.frames, 'FrameDuration': float(c.delay if c.frames > 1 else 1.0),
                 'HotSpotX': float(c.hx), 'HotSpotY': float(c.hy),
                 'PointsWide': float(c.w), 'PointsHigh': float(c.h), 'Representations': reps}
        for i in ids:
            entries[i] = entry
    cape = {'Author': 'Apple Inc. (extracted)', 'CapeName': 'macOS 27 Golden Gate', 'CapeVersion': 1.0,
            'Cloud': False, 'Cursors': entries, 'HiDPI': True, 'Identifier': 'local.macos27.goldengate',
            'MinimumVersion': 2.0, 'Version': 2.0}
    plistlib.dump(cape, open(os.path.join(d, f'{THEME}.cape'), 'wb'), fmt=plistlib.FMT_XML)


if __name__ == '__main__':
    shutil.rmtree(OUT, ignore_errors=True)
    cursors = load_all()
    build_macos(cursors)
    build_windows(cursors)
    build_linux(cursors)
    readmes = {
        os.path.join(OUT, 'macos', 'README.txt'):
            'macOS 27 Golden Gate cursors for older macOS\n\n'
            '1. Install Mousecape: https://github.com/alexzielenski/Mousecape\n'
            '2. Double-click macOS27-GoldenGate.cape (or File > Import in Mousecape).\n'
            '3. Select it and press Cmd+Return to apply.\n'
            'Undo: Mousecape > Reset to Default.\n',
        os.path.join(OUT, 'windows', THEME, 'README.txt'):
            'macOS 27 Golden Gate cursors for Windows 10 / 11\r\n\r\n'
            '1. Right-click install.inf > Install (Windows 11: Show more options > Install).\r\n'
            '2. Settings > Bluetooth & devices > Mouse > Additional mouse settings > Pointers.\r\n'
            '3. Choose the "macOS 27 Golden Gate" scheme and click Apply.\r\n'
            'Undo: choose "Windows Default" and click Apply.\r\n',
        os.path.join(OUT, 'linux', THEME, 'README.txt'):
            'macOS 27 Golden Gate cursors for Linux\n\n'
            'Run: sh install.sh\n'
            'Or copy this folder to ~/.icons/ and select macOS27-GoldenGate in your cursor settings.\n',
    }
    for path, text in readmes.items():
        open(path, 'w', newline='').write(text)
    shutil.rmtree(TMP, ignore_errors=True)
    print(f'Built {len(cursors)} cursors into {OUT}')
