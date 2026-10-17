"""Unpack an Elektron .syx (modern 126-byte transport) into its container sections.

Pure-Python port of the decode half of vendor/elektron-firmware-tool
(transport.c, container.c, aplib.c) from rytm1_mods-main, so it runs on Windows
without the C tool.

    python tools/unpack.py stock/Analog-Four_Analog-Keys_OS1.55.syx build/extract
"""
import hashlib
import struct
import sys
from collections import Counter
from pathlib import Path

SYX_PKT = 126
SYX_ENC_PAY = 116


def messages(buf):
    pos = 0
    while True:
        s = buf.find(b"\xf0", pos)
        if s < 0:
            return
        e = buf.find(b"\xf7", s + 1)
        if e < 0:
            return
        yield buf[s + 1:e]
        pos = e + 1


def decode_8in7(p):
    out = bytearray()
    for k in range(0, len(p), 8):
        ms = p[k]
        for n, b in enumerate(p[k + 1:k + 8]):
            out.append(b | (0x80 if (ms >> (6 - n)) & 1 else 0))
    return out


def transport_decode(buf):
    msgs = list(messages(buf))
    sizes = Counter(len(m) for m in msgs if len(m) > 5 and m[5] == 0x7E)
    pkt = sizes.most_common(1)[0][0]
    if pkt != SYX_PKT:
        raise SystemExit(f"legacy transport (packet body {pkt}) not supported")
    dev = msgs[0][3]
    dec = bytearray()
    for m in msgs:
        if len(m) == SYX_PKT and m[5] == 0x7E:
            dec += decode_8in7(m[9:9 + SYX_ENC_PAY])
    return dev, bytes(dec)


class Bits:
    def __init__(self, src, pos):
        self.s, self.p, self.tag = src, pos, 0

    def byte(self):
        if self.p >= len(self.s):
            raise EOFError
        b = self.s[self.p]
        self.p += 1
        return b

    def bit(self):
        self.tag = (self.tag << 1) & 0xFFFFFFFF
        if self.tag & 0xFF == 0:
            by = self.byte()
            self.tag = (by << 1) | 1
            return (by >> 7) & 1
        return (self.tag >> 8) & 1

    def gamma(self):
        v = 1
        while True:
            v = (v << 1) + self.bit()
            if self.bit():
                return v


def ap_depack(src):
    """src starts at the 8-byte [len][sum] header."""
    b = Bits(src, 8)
    out = bytearray()
    last = 1
    try:
        while True:
            if b.bit():
                out.append(b.byte())
                continue
            g = b.gamma()
            if g == 2:
                off = last
            else:
                off = ((g << 8) + b.byte()) & 0xFFFFFFFF
                if off == 767:
                    break
                off = (off - 767) & 0xFFFFFFFF
                last = off
            sl = 2 * b.bit() + b.bit()
            L = sl if sl else b.gamma() + 2
            if off > 3328:
                L += 1
            n = L + 1
            if off == 0 or off > len(out):
                raise ValueError("bad offset")
            for _ in range(n):
                out.append(out[-off])
    except EOFError:
        pass
    return bytes(out)


def be32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def parse_container(stream):
    c = stream[8:]  # skip [size][checksum] preamble
    size = be32(stream, 0)
    magic = c[:4]
    secs = []
    if magic == b"ELE3":
        n = be32(c, 0x1C)
        for i in range(n):
            sid, off, clen, dest = struct.unpack_from(">IIII", c, 0x20 + 16 * i)
            secs.append((sid, off, clen, dest))
    elif magic == b"ELE2":
        clen = be32(c, 0x18) + 8
        secs.append((3, 0x18, clen, be32(c, 0x14)))
    else:
        raise SystemExit(f"unknown container magic {magic!r}")
    return magic, c[:size], secs


def main():
    src, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    raw = src.read_bytes()
    print(f"{src.name}: sha256 {hashlib.sha256(raw).hexdigest()}")
    dev, stream = transport_decode(raw)
    magic, c, secs = parse_container(stream)
    print(f"device 0x{dev:02x}, container {magic.decode()}, {len(c)} B")
    print("header:", c[:0x20])
    for sid, off, clen, dest in secs:
        data = c[off:off + clen]
        try:
            body = ap_depack(data)
            kind = "aplib"
        except Exception:
            body, kind = data, "raw"
        if not body:
            body, kind = data, "raw"
        p = outdir / f"section_{sid}.bin"
        p.write_bytes(body)
        print(f"  section {sid}: off 0x{off:x} stored {clen} -> {len(body)} B ({kind}) "
              f"dest 0x{dest:08x}  sha256 {hashlib.sha256(body).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
