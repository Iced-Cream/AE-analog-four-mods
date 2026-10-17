# Porting the mods to OS 1.56 (2026-10-17)

**Status: ported** on this branch (OS-1.56): every target builds and
verifies (`make control scale slide fxhrd fxslot`, PASS; `control` rebuilds stock 1.56
byte for byte). Emulator (a "modified 1.56" profile rule added): NOISE page labels and
chord types (HDX, SW2), the DIST page in both builds (CHR in the full one), chords
with DIG on while playing - all as on 1.55, no faults. Hardware: the HARD-only build (`make hard`) ran the whole first-flash checklist on an Analog Four MK1 with nothing out of the ordinary (2026-10-17); the full build is emulator-checked only. NOTE SETUP
(the scale lock's menu) was not reached in the emulator; its patch sites are
byte-identical to 1.55's. New in 1.56: a EUCL page (NOTE pressed twice), the
Euclidean sequencer; a coverage session over it left the dead-code pools untouched.

The rest of this file is the research it was based on. It records what the stock
1.56 image looks like against
1.55 for everything the shipped mods (0001 0002 0006 0007 0008 0010) depend on.
Scripts and the full address map: `re/os156/` (run with `P156_WORK` pointing at a
folder holding `x155/` and `x156/` from `tools/unpack.py`, and `p156/m155.dis`,
`p156/m156.dis` disassembled as `tools/disasm.sh` does).

## Summary

| what | result |
|---|---|
| Patch sites (40 detours / patches) | **all found**, bytes identical apart from embedded addresses |
| Firmware symbols the stubs call / jump to | **all mapped**, identical listings |
| SRAM (voice frame, noise, fade, NCO words) | **unchanged** addresses |
| DDR globals | moved **+4** (project_ptr 0x415cba24 -> 0x415cba28, FX state 0x415c0004 -> 0x415c0008) |
| Data tables (page_info, slot lists, scale tables, LEN ticks) | moved, contents identical |
| Free DDR for mod state (0x46803000..0x4680ffff) | still free: same FX buffer bases (0x46800000, 0x46810000, 0x468a0000) |
| Sound / kit / project layouts | unchanged (same converter and copier code, same project size 0x3de9c) |
| `cave` (1,952 B) | **unchanged**: same constructor table end, same zeros up to `__bss_start` (0x40235000) |
| `cave3`, the chorus gap (1,024 B) | **present**, at 0x401eeb08 (+1424); nothing points into it |
| `cave2` (1,472 B) | **gone**: the embedded bootstrap grew 1,424 B and now ends at 0x40233fc0 |

So the port itself is mechanical, but **1.56 has 1,472 B less code space** (2,976 B
against 4,448 B), and the mods need about 4.1 KB (HARD-only) / 4.4 KB (full).

## Where things moved

Code shifts grow through the image: 0 (sound copiers, 0x40008xxx), -6 (fx_copy_v2),
+148 .. +446 (0x4002xxxx UI), +758 (sequencer), +832..+840 (scale library, labels),
+964..+1148 (project / pages / NOTE SETUP), +1172 (audio engine 0x400fxxxx),
+1174..+1188 (singletons, views), +1412..+1426 (tables 0x4018xxxx-0x401fxxxx).
The bootstrap image itself moved and grew; `__bss_start`, the .bss end
(0x4260fb10) and the SRAM copy start are unchanged; the SRAM initialiser grew 8 B
(0x4023c4a0 -> 0x4023c4a8), which is why the image is 8 B longer.

Two places changed in substance:

- **The encoder handler** (1.55 0x400257xx) was restructured. Both hooks still exist
  with the same instruction bytes: 0007's vtable +88 call at 0x40025a56 (resume
  0x40025a5c), 0008's held-trig +124 call at 0x40025a06 (resume 0x40025a0c), and the
  exit at 0x40025a68 (it now returns `fp@(-29)` instead of d7). The +88 call's third
  argument (0007 reads it as the delta) now passes through a new routine,
  0x40023580, which changes it only for parameter ids 40 and 53; the mods' ids are
  untouched, so the gate's meaning holds.
- **ppv_ctor** is at 0x40024f16 (+324), code identical (the automatic match landed
  10 B off; checked by hand).

Full table: `re/os156/map.json`; site check: `re/os156/sites156.py` (all 40 "ok").

## The space problem

1.55 usage: `cave` full (0001 720, 0006 96, 0002 312, 0008 212, 0007's UI helpers
436, 0010's gates 176), `cave3` full (0010's oscillator, 1,022 B), `cave2` = 0007's
main code: the distortion engine (dry mute, capture, drive: 846 B full / ~490 B
HARD-only) and the knob / label machinery the DIST page and the oscillator's NOISE
page knobs use (626 B).

Everything except 0007's main code fills 1.56's two pools to within 2 B. What fits
in 1.56 as-is: scale lock + 303 slide (always on) + kit persistence. The DIST page,
the digital path and the oscillator (which needs 0007's knob machinery) need
1,114 B (HARD-only) or 1,472 B (full) more.

The other zero runs in 1.56 are the same as in 1.55 (none new): table tails and
glyph rows of 113-203 B, and a 2 KB run at 0x401f11f8 that is the zero tail of a
4 KB lookup table the audio engine indexes (0x400f6868 points at its start). None is
usable as it stands.

## Dead code in 1.56 (2026-10-17)

`re/os156/deadscan.py` splits the code (below 0x401694a0, the bootstrap excluded)
into routines at every unconditional end and keeps those nothing reaches: no branch
or call target, no 32-bit word anywhere in the image (vtables, pointer tables,
immediates, lea/pea operands), no case of the 63 switch tables (16-bit offset tables
after `jmp %pc@(T,%dN:l)`, decoded). The code region has no other computed-jump form
(the odd ones the disassembler shows are all in the data above 0x4016e000).
Result: 454 runs, 17.2 KB.

Coverage (`re/os156/cover_run.sh`, emulator `DTEMU_COVER`, a coverage bitmap added to
analog-emu-main): six sessions on stock 1.56, 80 G instructions - every page of every
track type with every encoder, FUNC + every key with menu navigation, sequencer
(record, p-locks, pattern change, chain, song mode), keyboard / arp / PERF, playback
with random knob moves. 540 KB of code ran; **none of the 17.2 KB did**, and no code
the scan calls unreferenced ran (the scan missed nothing the sessions reached).

The usable pieces, all coherent code (whole functions or runs of them):

| 1.56 range | size | what |
|---|---|---|
| 0x400916c2..0x400919b8 | 758 B | one self-contained function (64-bit arithmetic); its 1.55 twin 0x40091382 is dead too (the one word pointing at it in 1.55 lies inside the embedded bootstrap: a coincidence) |
| 0x40167326..0x40167486 | 352 B | 8 small string helpers beside string_from_cstr |
| 0x4008e264..0x4008e3bc | 344 B | 12 wrapper functions |
| 0x400550a8..0x400551e6 | 318 B | 11 small accessors |
| 0x4009a35c..0x4009a478 | 284 B | 8 routines |
| then 240, 218, 210, 204, 202, 198 B ... | | |

These are what a C++ build keeps without dead-stripping: overloads and helpers
nothing calls. The same routines are unreferenced in 1.55 (the scan gives the same
list there, shifted).

How 0007's main code would fit:

- HARD-only (1,114 B): the distortion engine (dry mute, capture, output: ~490 B) in
  the 758 B function, the knob / label machinery (626 B) split over the 352 and 344 B
  runs.
- Full (1,472 B): capture (670 B) in the 758 B function, dry mute + output (176 B)
  in the 318 B run, the knob / label machinery in the 352 + 344 B runs.

Risk: static + emulator evidence, like the existing pools before their first
hardware run. If one of these routines were ever called after all (from a path the
emulator can't reach and through an address the scan can't see), it would run mod
code instead and most likely crash; a reinstall of stock fixes that. "probably-
verified" until hardware.

## Options for the missing ~1.1-1.5 KB

1. **Reuse dead code.** 1.55 had about 10.6 KB of code nothing references (94
   runs), but 3 of 97 such runs did execute in an emulator session, so a static scan
   is not enough. A candidate must be: never called or pointed to (including
   vtables and computed tables), never executed across long emulator sessions
   (boot, every page, playing, save/load, MIDI), and large and contiguous. Most
   promising for keeping every mod; it needs a careful verification pass.
2. **A reduced 1.56 set.** Scale + slide + kit persistence fit today. Adding the
   oscillator alone would need its NOISE page knobs reimplemented without 0007
   (~600 B), so it still needs new space.
3. **Shrink the mods.** Realistically 100-300 B, not 1.1 KB.
