# 0002 SLIDE 303 - design (re-only)

A per-track toggle that makes slide trigs behave like a TB-303: a slide on step N
means "glide from N into the next note", and N's note is held into the next one
automatically - no more stretching LEN by hand so the notes overlap.

Stock A4 semantics ("slide to"): the slide trig sits on the destination step, and the
glide only happens legato, i.e. when the previous note is still sounding - which in
practice means raising the previous trig's LEN until it overlaps.

## What was found (OS 1.55)

### Trig flags

A 16-bit word per step at the start of the track's storage, `track + step * 2`
(read by `0x400b0e54(track, step, mask)`, written by `0x400b3cb2(track, step, mask,
value)`, both clamping step to 0..63). Bit masks with their own get/set/toggle
thunks at 0x400b4188.. : 0x04, 0x08, **0x10 = note slide** (the NOTE SLIDE menu's
"CLEAR NOTE SLIDE" at 0x400d669a calls `0x400b422c(track, step, 0)` for steps
0..63), 0x20 = parameter slide (ParamSlideMenuView). Bits 0..1 are the trig itself
(the next-trig search below tests `& 3`).

### The trig-firing routine (0x400777dc..)

Reads one track of the pattern RAM (`0x4096ff4e + pattern * 94170 + track * 945`,
a2 + a3) for step d2. Per-step bytes, -1 meaning "use the track default":

| step array | default | what |
|---|---|---|
| +128 + step | +0x1c0 | NOTE |
| +192 + step | +0x1c1 | VEL |
| +256 + step | +0x1c2 | **LEN** (kept in `%sp@(84)`) |
| +320 + step | - | micro timing |
| +384 + step | - | trig condition (0x40076140) |
| +532 / +596 / +660 + step | - | chord notes 2..4, as offsets from NOTE |

The step's flag word is loaded into d3 at 0x40077bae and carried into the trig
event, so bit 0x10 (slide) reaches the voice engine through d3. The routine also
already has a "find the next trig" walk (0x40077d7e, for parameter slide): from
step + 1, wrapping at the track length `%sp@(80)`, until `flags & 3`.

## Design

Both changes are made inside the trig-firing routine, only on tracks with the
toggle on:

1. **Slide from:** replace bit 0x10 of the event flags (d3) with the slide bit of
   the *previous* trig step (walk back from step - 1, wrapping, until `flags & 3`).
   The voice engine then glides into this note exactly as it does for a stock slide
   trig - unchanged.
2. **Tie:** if *this* step has the slide bit, override its LEN (`%sp@(84)`) so the
   note lasts until the next trig plus a small overlap (the same next-trig walk stock
   uses for parameter slide). The next note then arrives legato, which is the
   condition the engine already needs for a glide.

So a 303 line is programmed exactly as on a 303: put slide on the note you slide
*from*; its length no longer matters. Slide time stays the sound's SLI parameter.

Toggle storage: TRANSPOSABLE (+0x1ca) is sanitised to 0/1 on load (0x40009750) and
KEY SCALE (+0x1c9) to 0..35 by 0001's patch, so either a spare bit plus a change to
that sanitiser, or a new NOTE SETUP item. Recommended: a NOTE SETUP item "SLIDE
MODE: A4 / 303", stored in bit 6 of KEY SCALE (0001's load clamp masks it out
instead of resetting), shown and edited by the same kind of stub 0001 uses for
KEY SCALE's text. Needs: the NOTE SETUP item table (constructor around 0x400d5e14)
to add one item, or else putting the toggle on an existing item.

## Still to find before building

- The exact instructions to hook: where LEN in `%sp@(84)` is turned into ticks, and
  the last point where d3 can be changed before it is stored into the event.
- How LEN maps to ticks (to compute "until the next trig"), and INF (127).
- Whether retrigs, trig conditions and the arpeggiator interact (a slide-from step
  whose next trig fails its condition should probably still release).

Estimate: moderate - one routine, two small hooks, one setting. Comparable to 0001.
