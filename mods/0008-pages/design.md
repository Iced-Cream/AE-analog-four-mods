# 0008 - extra pages

Status: the DIST page behind AMP is built and hardware-verified (2026-10-12): see
stub.s and mod.toml for what shipped (it also needed a short-name gate in 0007 for
the knob names). The pattern storage and Turing Machine parts below are future work.

## Research (2026-10-11)

Goal: real pages instead of FUNC layers - a DIST page behind AMP (the digital path
and drive settings) and a Turing Machine page behind NOTE/ARP (settings stored in the
pattern).

## How the A4 shows pages

- **Page descriptors** `page_info(p)` = 0x40194a14 + 44 * p: {name ptr, 10 parameter
  ids as longs}. 0 NONE, 1 PERF, 2 MIX, 3 ARP, 4 NOTE, 5 EUCL, 6 OSC1, 7 NOIS,
  8 OSC2, 9 OSC (shared osc), 10 FILT, 11 AMP, 12 ENVF, 13 ENV2, 14/15 LFO1/2,
  16 EXT, **17 blank**, 18 CHOR, 19 DEL, 20 REV, 21/22 FX LFO, 23..42 CV, 43..47.
- **Views** are built once at startup by the UI controller (0x400be1xx..0x400be9xx):
  each `new` 0x260 (0x420 for NOTE/EUCL), constructed as ParameterPageView
  (0x40024dd2(view, page, tag)) or a subclass (0x400c3440 for FILT/AMP/ENVF/ENV2,
  0x400c2422(view, 0/1) = NOTE page 4 / EUCL page 5, 0x400c22a4 = ARP, 0x400c19ec =
  PERF, 0x400c127c = MIX), wrapped in a shared_ptr (0x40155a52 / 0x40155a90 /
  0x40155a14) and inserted into a std::map at **controller + 436** keyed by a slot
  number (0x401564ae = operator[], 0x401559d2 = assign).
- **Slots** 0 PERF, 1 ARP, 2 NOTE, 3 EUCL, 4 MIX, 5 OSC1, 6 NOIS, 7 OSC2, 8 OSC,
  9 FILT, **10 AMP**, 11 ENVF, 12 ENV2, 13.. LFO/FX/CV ... 28: all 29 used.
- **Current slot**: `get_slot(state, track)` 0x400aa85e, state = controller + 120;
  stored per track type in the state's storage (vtable +0x28): synth +16, FX +20,
  CV +24. `set_slot` 0x400aa8c2 clamps to 0..28. `set_page(controller, slot)`
  0x400bab1a.
- **Current view**: 0x400bc388 - find(map, get_slot()) (0x400bab42), slot 4 if
  missing.
- **Page keys** (0x400c0130..0x400c022c): the key's binding in a std::map at
  **controller + 412** (0x401571b4 lookup) holds a **vector of slots**; a press finds
  the current slot in it (0x40155c96 = std::find) and goes to the next one - how
  NOTE/ARP/EUCL and OSC1/OSC cycle. End of list -> 0x400c0ee0 (wrap, to read).

## Plan for a page behind AMP

1. Startup hook after the builder: new a 0x260 view, construct it as page 17,
   shared_ptr-wrap it and insert it at a new slot (29) in the view map.
2. Raise set_slot's clamp to 29 (audit get_slot's callers first: no per-slot arrays).
3. Append slot 29 to the AMP key's slot vector (controller + 412).
4. Patch page_info(17): name "DIST", ids = AMP's (so the view has knobs), and move
   0007's FUNC-layer gates to key off "view page == 17" instead of FUNC.

## Open

- The key binding map's key format and where AMP's vector is filled.
- 0x400c0ee0 (end-of-list) behaviour.
- Pattern storage for the Turing page: spare bytes in the 94170-byte pattern and the
  pattern copy/save path (field-by-field copiers dropped kit spares; check the same).
