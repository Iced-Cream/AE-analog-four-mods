#!/usr/bin/env python3
"""Re-derive the three 1.55 code pools in 1.56 with the same evidence."""
import re, struct
W = __import__("os").environ.get("P156_WORK", ".")  # x155/ x156/ from tools/unpack.py, p156/m155.dis m156.dis
B = 0x40000400
img = {v: open(f'{W}/x{v}/section_3.bin', 'rb').read() for v in (155, 156)}


def L(v, a):
    return struct.unpack('>I', img[v][a - B:a - B + 4])[0]


def zero_run(v, a):
    """the zero run containing a: [start, end)"""
    d = img[v]; o = a - B
    s = o
    while s > 0 and d[s - 1] == 0:
        s -= 1
    e = o
    while e < len(d) and d[e] == 0:
        e += 1
    return B + s, B + e


def pointers_into(v, lo, hi):
    d = img[v]; out = []
    for o in range(0, len(d) - 3, 2):
        x = struct.unpack('>I', d[o:o + 4])[0]
        if lo <= x < hi:
            out.append((B + o, x))
    return out


def dis_find(v, rx):
    r = re.compile(rx)
    return [l.rstrip() for l in open(f'{W}/p156/m{v}.dis') if r.search(l)]


for v in (155, 156):
    print(f'=================== {v}')
    # cave: constructor table (count, entries) just below the zero run before 0x40235000
    s, e = zero_run(v, 0x40234f00)
    print(f'cave  zero run {s:#x}..{e:#x} ({e - s} B)')
    # the ctor table reader: find 'count' by scanning back for a long equal to the
    # number of longs between it and the zero run
    for cnt_at in range(s - 4, s - 4 * 400, -4):
        n = L(v, cnt_at)
        if cnt_at + 4 + 4 * n == s:
            print(f'      ctor table: count {n} at {cnt_at:#x}, ends {s:#x}')
            break
    print('      pointers into it:', pointers_into(v, s, e)[:5])
    # cave2: after the embedded bootstrap
    bound = [l for l in dis_find(v, r'cmpil #10760[0-9]{5},%d4')]
    print('cave2 flasher bound:', bound[:3])
    s2, e2 = zero_run(v, 0x40233c00)
    print(f'      zero run {s2:#x}..{e2:#x} ({e2 - s2} B)')
    print('      pointers into it:', [(hex(a), hex(x)) for a, x in pointers_into(v, s2 + 8, e2)][:5])
    # cave3: chorus gap - 0x401ee578 + shift
    sh = 0 if v == 155 else 1424
    s3, e3 = zero_run(v, 0x401ee778 + sh)
    print(f'cave3 zero run {s3:#x}..{e3:#x} ({e3 - s3} B)')
    print('      pointers into it:', [(hex(a), hex(x)) for a, x in pointers_into(v, s3, e3)][:5])
    print('      refs to the chorus tables:', [l[:70] for l in dis_find(v, '0x401e[de][0-9a-f]78')][:6])
