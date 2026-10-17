#!/usr/bin/env python3
"""Report candidate code caves in the stock A4 MAIN OS.

A deliberately small cousin of rytm-mods_latest/tools/cavescan.py (its passes 1 and
2; no dead-code pass). A candidate has to be below __bss_start - everything at or
above it is a SRAM load image and is then zeroed - and outside the embedded
bootstrap. Each run of one filler byte is reported with every 32-bit word in the
image that points into it or just past it, and with what the bytes on either side
look like, because a zero run can also be the tail of a live table.

    python tools/cavescan.py [--min 256]
"""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import symbols as symmod

# The startup code that defines the ceiling, with the opcode that introduces each
# operand as a guard: if the image is not the one this was read from, stop.
BOOT_SITES = {
    "sram1_src": (0x40000dca, 0x40000dc8, 0x45F9),   # lea   <src>,%a2
    "sram2_end": (0x40000e04, 0x40000e02, 0xB5FC),   # cmpal #<end>,%a2
    "bss_start": (0x40000e26, 0x40000e24, 0x207C),   # moveal #<start>,%a0
    "bss_end":   (0x40000e2c, 0x40000e2a, 0x223C),   # movel  #<end>,%d1
}


def boot_layout(img, base):
    out = {}
    for name, (opnd, op, want) in BOOT_SITES.items():
        got = struct.unpack_from(">H", img, op - base)[0]
        if got != want:
            raise SystemExit(f"{name}: opcode at 0x{op:08x} is 0x{got:04x}, expected "
                             f"0x{want:04x} - not the image this tool was written for")
        out[name] = struct.unpack_from(">I", img, opnd - base)[0]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min", type=int, default=256)
    a = ap.parse_args()
    meta = symmod.load(ROOT / "re" / "symbols.toml")["meta"]
    base = meta["base"]
    img = (ROOT / "build" / "stock_mainos.bin").read_bytes()
    lay = boot_layout(img, base)
    ceil = lay["bss_start"]
    bs_lo, bs_hi = meta["embedded_bootstrap_start"], meta["embedded_bootstrap_end"]
    print(" ".join(f"{k}=0x{v:08x}" for k, v in lay.items()))
    print(f"embedded bootstrap 0x{bs_lo:08x}..0x{bs_hi:08x}")

    words = [(i + base, struct.unpack_from(">I", img, i)[0]) for i in range(0, len(img) - 3, 2)]
    i, upto = 0, ceil - base
    while i < upto:
        j = i
        while j < upto and img[j] == img[i]:
            j += 1
        if j - i >= a.min and img[i] in (0x00, 0xFF):
            lo, hi = i + base, j + base
            if lo < bs_hi and bs_lo < hi:
                print(f"skip 0x{lo:08x}..0x{hi:08x}: overlaps the embedded bootstrap")
            else:
                refs = [(at, v) for at, v in words if lo - 16 <= v <= hi + 16]
                print(f"0x{lo:08x}..0x{hi:08x} {hi - lo:6d} B fill 0x{img[i]:02x}"
                      f"  before {img[i - 8:i].hex()} after {img[j:j + 8].hex()}")
                for at, v in refs[:12]:
                    print(f"      ref 0x{v:08x} from 0x{at:08x}")
                if len(refs) > 12:
                    print(f"      ... {len(refs) - 12} more")
        i = j


if __name__ == "__main__":
    main()
