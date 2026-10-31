#!/usr/bin/env python3
"""Download a single file out of a remote IPSW (a zip) without fetching the whole 25 GB archive.

Usage:
  python3 fetch_ipsw_entry.py URL --list            # list the DMGs inside the IPSW
  python3 fetch_ipsw_entry.py URL --largest OUT     # download the biggest DMG (the root filesystem)
  python3 fetch_ipsw_entry.py URL NAME OUT          # download a specific entry
Only stored (uncompressed) entries are supported, which is how IPSWs keep their encrypted DMGs.
"""
import shutil, struct, sys
import requests
from remotezip import RemoteZip

def main():
    url = sys.argv[1]
    z = RemoteZip(url)
    dmgs = [i for i in z.infolist() if i.filename.endswith(('.dmg', '.dmg.aea'))]
    if sys.argv[2] == '--list':
        for i in sorted(dmgs, key=lambda i: i.file_size):
            print(f'{i.file_size/1e9:7.2f} GB  {i.filename}')
        return
    if sys.argv[2] == '--largest':
        info, out = max(dmgs, key=lambda i: i.file_size), sys.argv[3]
    else:
        info, out = z.getinfo(sys.argv[2]), sys.argv[3]
    if info.compress_type != 0:
        raise SystemExit(f'{info.filename} is compressed; use `ipsw extract` instead')
    head = requests.get(url, headers={'Range': f'bytes={info.header_offset}-{info.header_offset + 29}'}).content
    name_len, extra_len = struct.unpack('<HH', head[26:30])
    start = info.header_offset + 30 + name_len + extra_len
    end = start + info.file_size - 1
    print(f'Downloading {info.filename} ({info.file_size/1e9:.2f} GB) -> {out}', file=sys.stderr)
    with requests.get(url, headers={'Range': f'bytes={start}-{end}'}, stream=True) as r, open(out, 'wb') as f:
        r.raise_for_status()
        shutil.copyfileobj(r.raw, f, length=16 << 20)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main()
