#!/usr/bin/env python3
"""Dump the bitmap cursors embedded in SkyLight's CursorAsset.

macOS draws the arrow, I-beam and spinning wait cursor from
/System/Library/PrivateFrameworks/SkyLight.framework/Versions/A/Resources/CursorAsset,
a Mach-O dylib whose exported `_cursors` table points at raw premultiplied BGRA bitmaps.

Usage: python3 dump_skylight.py CursorAsset OUTDIR
Writes OUTDIR/id<N>_<w>x<h>.png (animation frames stacked vertically) and OUTDIR/info.json.
"""
import json, os, struct, sys
from PIL import Image

def arm64_slice(data):
    if data[:4] == b'\xca\xfe\xba\xbe':           # fat / universal binary
        n = struct.unpack('>I', data[4:8])[0]
        for i in range(n):
            cpu, sub, off, size, _ = struct.unpack('>IIIII', data[8 + 20*i:28 + 20*i])
            if cpu == 0x0100000C:
                return data[off:off + size]
        raise SystemExit('no arm64 slice')
    return data

def sections(m):
    """Return {(seg, sect): (addr, offset, size)} for a 64-bit Mach-O."""
    ncmds = struct.unpack('<I', m[16:20])[0]
    off, out = 32, {}
    for _ in range(ncmds):
        cmd, size = struct.unpack('<II', m[off:off + 8])
        if cmd == 0x19:  # LC_SEGMENT_64
            nsect = struct.unpack('<I', m[off + 64:off + 68])[0]
            for s in range(nsect):
                b = off + 72 + 80*s
                sect = m[b:b + 16].rstrip(b'\0').decode()
                seg = m[b + 16:b + 32].rstrip(b'\0').decode()
                addr, sz = struct.unpack('<QQ', m[b + 32:b + 48])
                fo = struct.unpack('<I', m[b + 48:b + 52])[0]
                out[(seg, sect)] = (addr, fo, sz)
        off += size
    return out

def main(src, outdir):
    m = arm64_slice(open(src, 'rb').read())
    _, table, tsize = sections(m)[('__DATA_CONST', '__const')]
    ptr = lambda o: struct.unpack('<Q', m[o:o + 8])[0] & 0xFFFFFFF   # strip chained-fixup bits
    os.makedirs(outdir, exist_ok=True)
    info, i = {}, 0
    while True:
        cid, raw = struct.unpack('<QQ', m[table + 16*i:table + 16*i + 16])
        if raw == 0:
            break
        rec = ptr(table + 16*i + 8)
        w, h, hx, hy = struct.unpack('<dddd', m[rec:rec + 32])
        frames, nreps = ptr(rec + 32), ptr(rec + 48)
        delay = struct.unpack('<f', m[rec + 40:rec + 44])[0]
        reps = []
        for k in range(nreps):
            rp = ptr(rec + 56 + 8*k)
            rw, rh = struct.unpack('<QQ', m[rp:rp + 16])
            rhx, rhy = struct.unpack('<dd', m[rp + 16:rp + 32])
            px = m[rp + 32:rp + 32 + rw*rh*4*frames]
            Image.frombytes('RGBA', (rw, rh*frames), px, 'raw', 'BGRa').save(f'{outdir}/id{cid}_{rw}x{rh}.png')
            reps.append([rw, rh, rhx, rhy])
        info[cid] = dict(w=w, h=h, hot=[hx, hy], frames=frames, delay=delay, reps=reps)
        print(f'id {cid:3}: {w:g}x{h:g} pt, hotspot ({hx:g},{hy:g}), {frames} frame(s), reps {[(r[0], r[1]) for r in reps]}')
        i += 1
    json.dump(info, open(f'{outdir}/info.json', 'w'), indent=1)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
