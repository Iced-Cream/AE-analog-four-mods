# Research notes: the digital path (how 0006 and 0007 came about)

> Working notes kept for anyone extending the mods. They were written while the
> work was in progress and refer to two measuring builds that are not in this
> release: "0004", a DSP load probe (it measured the audio interrupt at about 71%
> average, 89% peak, and proved a voice's analog dry path can be muted while its
> digitised copy stays), and "0005", a kit-storage probe. The comb filter mentioned
> here is not in this release either. What shipped is described in docs/MANUAL.md.

# 0003 DIGITAL FX - architecture (re-only, waiting on the 0004 probe)

Goal: digital effect blocks on the A4 MK1 - a distortion (DIST/SRR/BRR, Machinedrum
style) and alternatives to the chorus (flanger, phaser, ...) - and a per-track choice
between the analog dry path and a "snatched" digital path that runs the voice through
those blocks.

## The audio engine (OS 1.55)

One interrupt does all digital audio: `audio_isr` 0x400fb0d6 (vector slot
0x400002fc, installed at 0x400fe8c8). Per 32-sample block it:

1. reads the playback DMA position to pick one of four buffers;
2. runs the control block - envelopes, LFOs and `track_levels` 0x400f4114, which
   turns each track's volume into **(a)** a send gain (ring 0x80006460, via
   0x400f40ee) plus a pan pair (0x800062e0), and **(b)** the analog **dry VCA words**,
   volume x pan L/R, at `0x800032b0 + 26 * track + 22/24`;
3. generates the four digital noise sources (0x400f9912);
4. runs the FX block 0x400f849c: the codec's receive frames (8 slots per sample,
   six used - four voices and the stereo input) are mixed into three stereo send
   buses at 0x800070a0.. with coefficients = send level^2 x the ring's send gain x
   pan, ramped per block; then chorus (0x400f7f50, RAM 0x46800000), delay
   (0x400f6bfc, 0x46c00000) and reverb (0x400f75ce, 0x46810000/0x468a0000) run, and
   **only their summed returns** are written out to the DAC;
5. sends the CV frame at 0x800032b0 to the hardware (0x40061834).

**Correction to the first version of this note:** the ring at 0x80006460 is not
audio. It holds per-track gains. The audio is the FX block's argument, the codec
receive frame.

## What that means for the plan

- The dry voice is analog to the outputs; the digital side gets a captured copy and
  returns only the FX through the DAC.
- **"AMP VOL 0 kills the sends" does not settle where the capture is.** The FX block
  multiplies every send by the track's volume in software. If the codec captures the
  voice *before* the analog output VCA, that multiply is the only reason the send
  dies.
- The dry level and the send gain are computed separately from the same volume, so
  a mod can **silence a track's dry path** (dry VCA words computed with volume 0, as
  for VOL 0) **while its send keeps the real volume** - at `dry_volume_load`
  0x400f445a.
- If the capture is pre-VCA, a snatched track is then: dry muted; its captured
  samples x volume x pan -> the selected effect block -> added into the FX block's
  output. It reaches the main out through the same DAC as the effect returns, a
  couple of milliseconds late, which does not matter because its dry is silent.
- If the capture is post-VCA, snatching is impossible (muting the dry also empties
  the capture) and only send-side effects remain - including replacing the chorus
  with another block, which works either way.

## What the 0004 probe answers (`make probe`)

1. **Capture point:** track 1's dry is muted in software, its sends untouched. Turn
   up track 1's delay or reverb send: echoes with no dry = pre-VCA (snatching works).
   Silence = post-VCA.
2. **Headroom:** the interrupt's run time over its period, average and peak, shown in
   NOTE SETUP's two quantize values in tenths of a percent.

## Probe results (hardware, 2026-10-09)

**Capture point: before the analog output VCA.** With track 1's dry muted in
software, its delay/reverb sends still carry the voice. Snatching works.

**Load** (tenths of a percent of the interrupt period; average / peak per window):

| state | average | peak |
|---|---|---|
| A. sequencer stopped | 71.1 % | 76.5 % |
| B. track 1 playing, reverb send | 71.3 % | 79.4 % |
| C. track 1 playing, all three sends | 71.3 % | 80.9 % |
| D. all tracks, all sends, reverb decay near max | 71.3 % | 82-89 % |

Reading: the FX run whether or not anything plays (the average barely moves), so
the cost is mostly fixed; the peaks come from block-to-block variation and from
whatever preempts the audio interrupt. Worst case seen: ~11 % of the period left,
and that remainder is also what the UI and sequencer run on. Budget rule for new
blocks: stay well under ~5 % at peak, and prefer replacing work (chorus slot) to
adding it.

Rough costs: a per-track DIST/SRR/BRR insert is a handful of instructions per
sample, ~1-2 % per snatched track; a flanger or phaser in the chorus slot replaces the
chorus's own cost, so roughly neutral. Both to be confirmed with the probe.

## Storage and UI findings (2026-10-10)

- **Kit storage:** the FX track's parameters are 74 words at `S + 4 + 2 * index`
  (container 7), S = the active kit's FxSetup storage = `*(project + 244 + 0x1030 +
  16)` - plain loads, usable from the audio interrupt. **Indices 10..25 belong to no
  parameter**: 16 spare words. Stock kits hold 0 there (to be confirmed by the 0005
  probe), so every new setting treats 0 as "off / chorus / neutral". Writes go
  through stock's notify (FxSetup vtable +0x10 with change info 0x4016f56c) so the
  kit counts as edited.
- **No spare parameter ids:** the 295-record table (0x4016952c) has no dead records,
  is bounded in 74 places, and other per-id structures (p-lock bitsets) are sized
  for 295 - new ids are unsafe. Hence: the FX slot reuses the chorus page's own ids
  (keeps p-locks, LFO, CC); extra pages are custom views with no p-locks/LFO/CC.
- **Labels:** a knob's label comes from `FxParameterSet` vtable +0x84 (0x4009b77c),
  which calls a formatter `std::function` stored at +24 of the parameter's 88-byte
  RAM record (`param_info(id)` = 0x415b25a0 + 88 * id). Relabelling the chorus knobs
  in comb mode = a gate there for ids 151..160 that writes our own text. Next step:
  the string API it writes through.
- **Chorus slot:** `chorus(in, out)` 0x400f7f50 - 32 stereo frames, 32-bit
  fractional (the FX block runs the EMAC with MACSR = 0xa0). Its delay RAM is 12 KB at
  0x46800000; 0x46803000..0x4680ffff is unreferenced and holds the comb's delay lines.

## Page findings (2026-10-10)

- **Page descriptors**: `page_info(p)` 0x400f01a0 = 0x40194a14 + 44 * p (p <= 47):
  {name, 10 parameter ids, 0 = empty knob}. 0 NONE, 1 PERF, 2 MIX, 3 ARP, 4 NOTE,
  5 EUCL, 6..15 synth pages, 16 EXT, **17 blank (no ids, no view)**, 18 CHOR, 19 DEL,
  20 REV, 21/22 FX LFO1/LFO2, 23.. CV/ENV/LFO/CTRL.
- **A view shows one page**: `ParameterPageView` ctor 0x40024dd2 (this, page, tag)
  stores the page at +128 (vtable +0x68 returns it) and its name as the title
  (std::string at +124, built by 0x40166fec(&str, cstr, &tmp)). A knob's id is
  `page_info(view->+128)->ids[knob]` (0x40022e80).
- **The FX views** are built once at startup (0x400be5xx..): 0x260-byte views
  registered by slot - 14 EXT (page 16), 15 CHOR (18), 16 DEL (19), 17 REV (20),
  18 LFO1 (21), 19 LFO2 (22). How a page key reaches its slot is NOT yet found;
  slot +0x10 (0x40024b6a) is the page draw, not a key handler.
- **Chosen page design**: page 17 = the CHOR view in an alternate mode (+128 flipped
  to 17, title swapped), its descriptor reusing the chorus ids, with page_get_value
  (+0x54), param_apply_delta (+0x58) and the held-trig paths redirected to the kit's
  spare words while the view shows page 17 (and refusing p-locks there). Labels via
  FxParameterSet +0x84 (0x4009b77c). Foreign ids on the FX set were rejected: the
  shared set path (0x4009e000) runs generic list machinery with unmapped side effects.
- **Missing**: the page-key dispatch (to flip on a second CHORUS press), and the
  string construction call's exact signature (labels, title).

## The architecture, once the probe says go

- **Effect blocks** as stub routines with one signature: `(in, out, state, params,
  32 frames)` on stereo 32-bit buffers, run inside the FX block. A per-kit "FX A"
  selector picks chorus (stock) or one of the new blocks for the chorus slot -
  reusing the chorus send and its 0x46800000 delay RAM, so no new send bus.
- **Snatch:** a per-track setting. Snatched tracks have their dry muted at 0x400f445a
  and their captured slot fed to an insert chain (DIST/SRR/BRR), then summed into the
  FX output after the returns. The insert's output can still feed the sends.
- **Storage and UI:** the kit's spare bytes (to be found, as rytm-mods did with the
  sound's free word) and a parameter page - the largest remaining unknown on the UI
  side.
- **Budget:** each new block is costed against the probe's peak reading before it
  ships.
