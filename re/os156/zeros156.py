#!/usr/bin/env python3
"""Zero runs >= 96 B below __bss_start in both images, with pointers into them, and
the 1.55 -> 1.56 correspondence (by the run's neighbourhood)."""
import struct, bisect
W = __import__("os").environ.get("P156_WORK", ".")  # x155/ x156/ from tools/unpack.py, p156/m155.dis m156.dis
B = 0x40000400
BSS = 0x40235000
BOOT = {155: (0x40226958, 0x40233a30), 156: None}
img = {v: open(f'{W}/x{v}/section_3.bin', 'rb').read() for v in (155, 156)}


def runs(v, minlen=96):
    d = img[v][:BSS - B]
    out = []; o = 0
    while o < len(d):
        if d[o] == 0:
            s = o
            while o < len(d) and d[o] == 0:
                o += 1
            if o - s >= minlen:
                out.append((B + s, B + o))
        else:
            o += 1
    return out


def ptr_targets(v):
    d = img[v]
    t = []
    for o in range(0, len(d) - 3, 2):
        x = struct.unpack('>I', d[o:o + 4])[0]
        if B <= x < BSS:
            t.append(x)
    t.sort()
    return t


for v in (155, 156):
    pt = ptr_targets(v)
    print(f'===== {v}')
    tot = 0
    for s, e in runs(v):
        # pointers landing strictly inside (s+4 .. e) - a pointer to s itself may be a
        # table end; report both
        i = bisect.bisect_left(pt, s); j = bisect.bisect_left(pt, e)
        inside = pt[i:j]
        flag = '' if not inside else f'  {len(inside)} ptrs, first {inside[0]:#x}'
        print(f'  {s:#010x}..{e:#010x} {e - s:6} B{flag}')
        if not inside:
            tot += e - s
    print('  total with no pointer in:', tot)
