#!/usr/bin/env python3
"""rng.py VER START END [REGEX]: print the disassembly of VER (155/156) in [START, END],
optionally only lines matching REGEX."""
import re, sys
W = __import__("os").environ.get("P156_WORK", ".")  # x155/ x156/ from tools/unpack.py, p156/m155.dis m156.dis
v, s, e = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
rx = re.compile(sys.argv[4]) if len(sys.argv) > 4 else None
for line in open(f'{W}/m{v}.dis'):
    if len(line) < 9 or line[8] != ':':
        continue
    try:
        a = int(line[:8], 16)
    except ValueError:
        continue
    if s <= a <= e and (rx is None or rx.search(line)):
        print(line.rstrip()[:110])
