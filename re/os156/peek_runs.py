#!/usr/bin/env python3
"""peek_runs.py VER LO-HI ...: the first instructions of each routine in the ranges,
with the calls they make and the strings they point at."""
import os, re, sys
W = os.environ.get('P156_WORK', '.')
v = sys.argv[1]
B = 0x40000400
img = open(f'{W}/x{v}/section_3.bin', 'rb').read()
RX = re.compile(r'^([0-9a-f]{8}):\t([0-9a-f ]+?)\s*\t(.*)$')
lines = [(int(m.group(1), 16), m.group(3)) for m in map(RX.match, open(f'{W}/p156/m{v}.dis')) if m]


def cstr(a):
    o = a - B
    if not (0 <= o < len(img)):
        return None
    e = img.find(b'\0', o, o + 48)
    s = img[o:e] if e > o else b''
    return s.decode('latin1') if len(s) >= 4 and all(32 <= c < 127 for c in s) else None


for rng in sys.argv[2:]:
    lo, hi = (int(x, 16) for x in rng.split('-'))
    body = [(a, t) for a, t in lines if lo <= a < hi]
    calls = sorted({re.search(r'0x[0-9a-f]+', t).group(0) for a, t in body if t.startswith(('jsr', 'bsr')) and '0x' in t})
    strs = sorted({s for a, t in body for h in re.findall(r'0x(4[0-9a-f]{7})', t) if (s := cstr(int(h, 16)))})
    print(f'== {lo:#x}..{hi:#x} ({hi - lo} B, {len(body)} insns)')
    for a, t in body[:6]:
        print(f'   {a:08x} {t[:70]}')
    print(f'   calls: {" ".join(calls[:10])}')
    if strs:
        print(f'   strings: {strs[:6]}')
