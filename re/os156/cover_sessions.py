#!/usr/bin/env python3
"""Print dtboot argument lists for the coverage sessions, one per line:
NAME INSTR ARGS... (actions from 3040M, the main screen; 1M instr = 5 ms)."""
import random

PAGES = ['OSC1', 'OSC1', 'OSC2', 'FILTERS', 'AMP', 'AMP', 'ENV', 'LFO', 'LFO', 'NOTE', 'ARP', 'PERF']
TRACKS = ['TRACK1', 'TRACK2', 'TRACK3', 'TRACK4']
OTHER = ['FX', 'CV']
KEYS = ['PAGE', 'NOTE', 'OSC1', 'OSC2', 'FILTERS', 'AMP', 'ENV', 'LFO', 'TRACK1', 'TRACK2', 'TRACK3',
        'TRACK4', 'FX', 'CV', 'TEMPO', 'TRNS', 'YES', 'NO', 'LEFT', 'DOWN', 'RIGHT', 'UP', 'PERF', 'ARP',
        'RECORD', 'PLAY', 'STOP', 'BANKGROUP', 'SONGMODE', 'CHAIN', 'BANK_A', 'BANK_B', 'BANK_C', 'BANK_D'] + \
       [f'T{i}' for i in range(1, 17)] + [f'KB_{n}' for n in ('C1', 'D1', 'E1', 'F1', 'G1', 'A1', 'B1', 'C2')]


class S:
    def __init__(self, name):
        self.name, self.t, self.a = name, 3040, []

    def press(self, k, hold=None, dt=30):
        self.a += ['--press', f'{k}@{self.t}M' + (f':{hold}M' if hold else '')]
        self.t += dt

    def turn(self, enc, d, dt=12):
        self.a += ['--turn', f'{enc}:{d}@{self.t}M']
        self.t += dt

    def knobs(self, n=3):
        for e in range(10):
            self.turn(e, n); self.turn(e, -n)

    def line(self, tail=400):
        return f'{self.name} {self.t + tail}M ' + ' '.join(self.a)


out = []
s = S('pages_synth')
for tr in TRACKS:
    s.press(tr)
    for p in PAGES:
        s.press(p); s.knobs()
out.append(s)

s = S('pages_fxcv')
for tr in OTHER:
    s.press(tr)
    for p in PAGES:
        s.press(p); s.knobs(5)
s.press('TEMPO'); s.knobs(); s.press('NO')
s.press('TRNS'); s.knobs(); s.press('NO')
out.append(s)

s = S('sequencer')
s.press('RECORD')
for i in (1, 3, 5, 7, 9, 11, 13, 15):
    s.press(f'T{i}')
s.press('T5', hold=200, dt=10); s.turn(0, 9); s.turn(2, -9); s.t += 200   # p-locks
s.press('T9', hold=200, dt=10); s.turn(5, 7); s.t += 200
s.press('RECORD'); s.press('PLAY', dt=400)
for tr in TRACKS[1:] + OTHER:
    s.press(tr); s.press('RECORD')
    for i in (2, 6, 10, 14):
        s.press(f'T{i}')
    s.press('RECORD', dt=200)
s.press('BANK_A', hold=60, dt=10); s.press('T2', dt=400)
s.press('CHAIN', hold=100, dt=10); s.press('T1', dt=20); s.press('T2', dt=300)
s.press('SONGMODE', dt=300); s.press('SONGMODE', dt=100)
s.press('BANKGROUP', dt=200); s.press('NO')
s.press('STOP', dt=100); s.press('STOP', dt=100)
out.append(s)

s = S('menus')
for k in KEYS:
    if k == 'FUNC':
        continue
    s.press('FUNC', hold=60, dt=15); s.press(k, dt=120)
    s.press('DOWN', dt=40); s.press('DOWN', dt=40); s.turn(0, 2); s.press('UP', dt=40)
    s.press('RIGHT', dt=40); s.press('LEFT', dt=40)
    s.press('NO', dt=60); s.press('NO', dt=60)
out.append(s)

s = S('keyboard')
s.press('TRACK1')
for k in ('KB_C1', 'KB_E1', 'KB_G1', 'KB_C2', 'KB_D1', 'KB_F1', 'KB_A1', 'KB_B1'):
    s.press(k, hold=40, dt=60)
s.press('ARP'); s.knobs(); s.press('ARP', hold=60, dt=20); s.press('KB_C1', hold=300, dt=400)
s.press('PERF'); s.knobs(9)
s.press('TRNS', hold=60, dt=20); s.press('KB_G1', dt=200)
for tr in TRACKS:
    s.press(tr)
    for k in ('KB_C1', 'KB_G1'):
        s.press(k, hold=40, dt=60)
out.append(s)

s = S('playback')
s.press('RECORD')
for i in range(1, 17, 2):
    s.press(f'T{i}')
s.press('RECORD'); s.press('PLAY', dt=3000)
random.seed(156)
for _ in range(80):                                      # random knob moves while playing
    s.press(random.choice(PAGES), dt=20); s.turn(random.randrange(10), random.choice((-6, 6)), dt=25)
s.press('STOP')
out.append(s)

for s in out:
    print(s.line())
