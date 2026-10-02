import sys
sys.stdout.reconfigure(encoding='utf-8')
import solver as S
from test_solver import FakeBoard

# 复现局8 第4轮读到的棋盘
raw = [
    '....1####',
    '....1####',
    '...12##2#',
    '...1#####',
    '12121####',
    '#########',
    '#########',
    '#########',
    '#########',
]
cells = []
for line in raw:
    row = []
    for ch in line:
        if ch == '#':
            row.append(('hidden', None))
        elif ch == '.':
            row.append(('open', 0))
        else:
            row.append(('open', int(ch)))
    cells.append(row)

bd = FakeBoard(cells, 10)
st = S.State(bd)
safe, mines = S._deduce(st)
print('deduce safe :', sorted(safe or []))
print('deduce mines:', sorted(mines or []))
probs = S.enumerate_probs(st)
if probs:
    print('概率:')
    for g in sorted(probs):
        print('   ', g, round(probs[g], 4))
