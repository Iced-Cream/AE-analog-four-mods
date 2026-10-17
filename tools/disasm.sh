#!/bin/sh
# Whole-image disassembly of the stock MAIN OS with EMAC decoding (as rytm1_mods-main's
# `make disasm`). Run from analog_four_main/ after `make build` (which leaves
# build/stock_mainos.bin), or after tools/unpack.py on Windows.
set -e
P=$(python3 -c 'import sys; sys.path.insert(0,"tools"); from toolchain import prefix; print(prefix())')
[ -f build/stock_mainos.bin ] || cp build/extract/section_3.bin build/stock_mainos.bin
printf '\t.section .archtag,"a"\n\tmovclr.l %%acc0,%%d0\n\t.text\n\t.incbin "build/stock_mainos.bin"\n' > build/mainos_wrap.s
"${P}as" -mcpu=5475 build/mainos_wrap.s -o build/mainos_wrap.o
"${P}objdump" -d -j .text --adjust-vma=0x40000400 build/mainos_wrap.o | sed 's/^ *//' > build/mainos.dis
wc -l build/mainos.dis
