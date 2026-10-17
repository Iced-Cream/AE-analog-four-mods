# 0001 SCALE LOCK - design

Restrict a track's notes to a key and scale, Digitone II style: live playing (trig
keys in KEYBOARD mode), live and grid recording, and the TRIG page NOTE encoder.
User-facing description: `docs/MANUAL.md`. Status: `built` (verifies in software,
not yet flashed).

## What 1.55 already has

### A full scale library, linked but never called

| symbol | what |
|---|---|
| `in_scale` 0x4007ea50 | `(note - key) mod 12` looked up in `scale_table`; -1 = chromatic |
| `scale_quantize` 0x4007ec2a | first of n, n-1, n+1, n-2, n+2 in the scale |
| `scale_short_names` 0x401ed978 | CHRO, ION, DOR ... LO37 |
| `scale_table` 0x401817fc | 35 rows x 13 B, degree + 1 at in-scale intervals; row r = name r + 1 |

No jsr, lea or data word refers to any of them: shared Elektron library code. The
mod reads `scale_table` and `scale_short_names` directly and carries no scale data.
It does not call `in_scale`/`scale_quantize`: they refuse notes outside 0..127, and
the note events this mod sees are not on that scale (below).

### Per-track key settings (NOTE SETUP)

TrackPattern +0x1c8 KEY NOTE (0..11), +0x1c9 KEY SCALE (0..2 = OFF/MAJ/MIN). Stock
uses KEY SCALE only in `key_offset` 0x4007771c, a transposition offset (MAJ 12 - key,
MIN 21 - key, else 0). Pattern load resets KEY SCALE > 2 to OFF (0x40009730); the
menu setter clamps 0..2 (0x400b25e0).

## Design

### Setting: KEY SCALE, extended

0 = OFF, 1 = MAJ, 2 = MIN, 3..35 = DOR, PHRY, LYD, MIXO, LOCR, then the rest of the
library in its order (the remap table in the stub). Anything but OFF locks the track
- MAJ/MIN included, by choice: existing patterns may start restricting notes.

- Patches: the setter's two `moveq #2` and the load sanitiser's `moveq #2` -> 35.
- KEY SCALE text: detour at 0x400d604a, where stock pushes names[v] from a 3-entry
  stack copy (which would read past it for v > 2). MAJ/MIN keep their names; 3..35
  show the library short name.
- Transposition: two branch patches in `key_offset` give 3..35 the MAJ arm
  (12 - key); 0 still gives 0, 2 still MIN.
- A pattern saved with a new scale reads OFF on stock 1.55.

### Hook 1 - played notes (`track_play_note` 0x400b942c)

**Revised after the first hardware test.** The first build hooked
`ViewController::handleNoteEvent`, assuming every played note was a note event. On
the unit the scales changed nothing: in KEYBOARD mode the trig keys arrive as *key
events* and the track view's key handler calls `track_play_note` directly
(0x400ba1e4). Note events reach the same function through `live_note_handler`
(0x400b9976).

`track_play_note(view, raw, final, velocity)` is therefore the one choke point, and
`final` is an absolute pitch (stock refuses it above 127), so it is snapped as is:
the first of 0, -1, +1, -2, +2 semitones that lands in the scale (stock
`scale_quantize`'s order). No row has a gap above four semitones, so one always
does (checked over all 35 scales and 12 keys). The held-note entry stores the
snapped `final`; note-off finds the entry by `raw` and releases what was stored, so
no note can hang. Live recording records what `track_play_note` is given.

### Hook 3 - step entry (`set_step_note` 0x400ac540)

Hold a trig and play a key: the keyboard handlers store `final - 60 - KEY NOTE`, an
offset from the key's root, so it is snapped with a key of 0 before stock's ±36
clamp.

### Hook 2 - NOTE encoder (three sites)

**Revised after the second hardware test**, where the encoder stayed chromatic: the
first two builds compared the parameter id with 0x1e, which is a field of NOTE's
record (its CC), not its id. The page encoder handler (0x40025530) indexes the
56-byte records at 0x4016952c by id, and NOTE ("Main Note") is **id 19**; 30 is the
track's Level. The FUNC test is gone too: the lock applies with or without FUNC.

The handler reaches a NOTE value by one of three routes, each now caught where the
delta meets the value:

| route | site | done |
|---|---|---|
| no trig held | `param_apply_delta` entry 0x40022f20 | value from `page_get_value` (vtable +0x54), delta rewritten |
| trigs held, per trig | `lock_delta_apply` entry 0x40023444 (vtable +0x78) | value from the step's lock (vtable +0x70), delta rewritten |
| one lock edited directly | `addl %d5,%d0` at 0x40023afc in the +0x7c routine | the add replaced |

All three call `note_step(value, delta)`: whole steps are delta / 256, a smaller
nonzero delta still counts as one, and each step walks to the next in-scale note
(stopping at 0..127). Values are 8.8 on the 0..127 scale; 1..127 would be taken as a
plain note. The NOTE value is absolute (record default 48 = C), so its pitch class
is `value mod 12`.

## Space

719 B in `cave` at 0x40234860 (claim 0x2e0). `cave2` (1472 B) is untouched.

## Hardware log

- 2026-10-09, first build (hooking handleNoteEvent): boots, KEY SCALE menu and names
  correct, `cave` pool runs code fine. No restriction from any scale; the only
  difference heard between OFF, MAJ, MIN and the new values was stock's
  transposition offset (`key_offset`), which 3..35 share with MAJ. Cause above.
- 2026-10-09, second build (track_play_note + set_step_note): playing on the trig
  keys and hold-a-trig entry restricted to the scale, all scales distinct. NOTE
  encoder still chromatic, FUNC or not - the wrong id (above). Changing the scale
  does not move notes already sequenced (by design).

## What only hardware can settle

The checklist in `docs/MANUAL.md`. The open points behind it:

- the `cave` pool's first run (static case only, see allocations.toml);
- that trig-key events are the ones `live_note_handler` plays as `note + 30 + ...`
  (read statically; a wrong pitch-class bias would show as the lock using the wrong
  key, a fixed offset of the root);
- whether external MIDI notes come through the event queue at all;
- that `page_get_value` returns the held trig's lock while a trig is held.
