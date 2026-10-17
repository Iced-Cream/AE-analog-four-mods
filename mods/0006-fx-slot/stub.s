        | Mod 0006 - kit FX persistence: the spare FX words survive every copy,
        | save and reload. See mod.toml. (The comb filter that used to live here
        | is shelved in comb_shelved.s.)

        .include "symbols.inc"

        .equ    SPARE_OFF,   4 + 2 * 10           | spare words 10..25: 32 bytes
        .equ    SPARE_LONGS, 8

        .text

        | ------------------------------------------------------------------
        | The FX block copiers, at their entries: the spare words travel too.
        |
        | Stock copies an FX block word by word and skips offsets 12..55
        | (12..23 by a separate loop), so words 10..25 were lost. There are
        | three such copiers, all fn(dst, src) with the same layout:
        |   fx_copy      no version check: kit to kit, the storage kit (FX at
        |                +1380) into the working kit (FX at +1432) on load,
        |                SysEx dumps;
        |   fx_copy_v2   a version-2 source (upgrades it to 3);
        |   fx_copy_v4   a version-4 source: the working kit out to the storage
        |                kit, i.e. the save. Missing this one is why settings
        |                survived kit switches but not a power cycle.
        | Each carries the 32 bytes at offset 24 when the stock copy would run
        | (same version test). Stock OS still drops them, so a kit saved here
        | loads on stock with the new settings ignored.
        | Stack untouched: (%sp) return, 4 dst, 8 src.
        | ------------------------------------------------------------------
        .align  2
copy_gate:
        moveq   #0,%d1
        bsr.s   spare_copy
        lea     -32(%sp),%sp                      | displaced
        movem.l %d2-%d4/%a2-%a6,(%sp)             | displaced
        jmp     fx_copy_body

        .align  2
copy2_gate:
        moveq   #2,%d1
        bsr.s   spare_copy
        lea     -36(%sp),%sp                      | displaced
        movem.l %d2-%d5/%a2-%a6,(%sp)             | displaced
        jmp     fx_copy_v2_body

        .align  2
copy4_gate:
        moveq   #4,%d1
        bsr.s   spare_copy
        lea     -32(%sp),%sp                      | displaced
        movem.l %d2-%d4/%a2-%a6,(%sp)             | displaced
        jmp     fx_copy_v4_body

        | spare_copy: the gate's (dst, src) at 8/12(%sp); d1 = the version the
        | source must have, 0 = any. Clobbers d0/a0/a1 only.
spare_copy:
        move.l  8(%sp),%d0
        beq.s   9f
        move.l  %d0,%a0
        move.l  12(%sp),%d0
        beq.s   9f
        move.l  %d0,%a1
        tst.l   %d1
        beq.s   1f
        cmp.l   (%a1),%d1
        bne.s   9f
1:      lea     SPARE_OFF(%a0),%a0
        lea     SPARE_OFF(%a1),%a1
        moveq   #SPARE_LONGS,%d0
2:      move.l  (%a1)+,(%a0)+
        subq.l  #1,%d0
        bne.s   2b
9:      rts
