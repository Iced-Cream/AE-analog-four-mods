#!/usr/bin/env python3
"""Check every shipped detour/patch at its 1.56 address: the 1.56 bytes must equal the
registry's expect bytes, except 32-bit words that are image addresses in both (those
moved with the code; printed old -> new)."""
import json, struct, tomllib
A = __import__('os').environ.get('A4_PROJECT', '.')  # the project root (this repo)
W = __import__("os").environ.get("P156_WORK", ".")  # x155/ x156/ from tools/unpack.py, p156/m155.dis m156.dis
B = 0x40000400
img5 = open(f'{W}/x155/section_3.bin', 'rb').read()
img6 = open(f'{W}/x156/section_3.bin', 'rb').read()
mp = {int(k, 16): v for k, v in json.load(open(f'{W}/p156/map.json')).items()}
FIX = {0x40024dd2: 0x40024f16, 0x40025898: 0x40025a56, 0x4002589e: 0x40025a5c,
       0x400258ac: 0x40025a06, 0x400258b2: 0x40025a0c, 0x400258ba: 0x40025a68}
reg = tomllib.load(open(A + '/registry/allocations.toml', 'rb'))
SHIP = ('0001', '0002', '0006', '0007', '0008', '0010')


def isaddr(v):
    return 0x40000000 <= v < 0x42000000


bad = 0
for kind in ('detour', 'patch'):
    for e in reg[kind]:
        if not e['owner'].startswith(SHIP):
            continue
        x = e['addr']
        y = FIX.get(x) or (mp.get(x) or {}).get('to')
        exp = bytes.fromhex(e['expect'])
        if y is None:
            print(f'{kind:6} {x:#x}: NOT MAPPED'); bad += 1; continue
        y = int(y)
        got = img6[y - B:y - B + len(exp)]
        moved = []
        ok = True
        k = 0
        while k < len(exp):
            if k + 4 <= len(exp):
                v5 = struct.unpack('>I', exp[k:k + 4])[0]; v6 = struct.unpack('>I', got[k:k + 4])[0]
                if isaddr(v5) and isaddr(v6) and v5 != v6:
                    moved.append(f'{v5:#x}->{v6:#x}'); k += 4; continue
            if exp[k] != got[k]:
                ok = False
            k += 1
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {kind:6} {e['owner'][:4]} {x:#010x} -> {y:#010x} ({y - x:+5d})  {e.get('gate', ''):7} {' '.join(moved)}")
print('bad:', bad)
