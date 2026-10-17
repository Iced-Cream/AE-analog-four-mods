#!/bin/bash
# Run the coverage sessions on an image (default: stock 1.56) in parallel; writes
# cover_<name>.txt (DTEMU_COVER ranges) and <name>_end.png into OUT.
# usage: cover_run.sh [SYX] [OUT]
HERE=$(cd "$(dirname "$0")" && pwd)
A=$(cd "$HERE/../.." && pwd)
SYX=${1:-$A/stock/Analog-Four_Analog-Keys_OS1.56.syx}
OUT=${2:-$PWD/cover}
R=~/emu-target/release
mkdir -p "$OUT" ~/emu/a4
cd ~/emu/a4
[ -f a4mk1.img ] || $R/dtcard a4mk1.img format > /dev/null
while read -r name instr args; do
  cp a4mk1.img "cov_$name.img"
  ( DTEMU_COVER="$OUT/cover_$name.txt" DTBOOT_END_PNG="$OUT/${name}_end.png" \
      timeout 1500 $R/dtboot "$SYX" --instr "$instr" --card "cov_$name.img" $args \
      > "$OUT/$name.log" 2>&1; echo "$name done: $(grep -ac . "$OUT/cover_$name.txt" 2>/dev/null) ranges" ) &
done < <(python3 "$HERE/cover_sessions.py")
wait   # (the loop must run in this shell, or wait has no children to wait for)
