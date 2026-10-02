"""求解器单元测试（动态尺寸/雷数）。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import solver as S

H, O, F = 'hidden', 'open', 'flag'


class FakeBoard:
    def __init__(self, cells, total):
        self.cells = cells
        self.rows = len(cells)
        self.cols = len(cells[0])
        self.total = total

    def opened(self):
        out = {}
        for r in range(self.rows):
            for c in range(self.cols):
                st, v = self.cells[r][c]
                if st == 'open':
                    out[(c, r)] = v
        return out

    def flagged(self):
        return {(c, r) for r in range(self.rows) for c in range(self.cols)
                if self.cells[r][c][0] == 'flag'}

    def unknown(self):
        return {(c, r) for r in range(self.rows) for c in range(self.cols)
                if self.cells[r][c][0] in ('hidden', 'question')}

    def total_mines(self):
        return self.total


def grid(rows, cols, fill=(O, 0)):
    return [[fill for _ in range(cols)] for _ in range(rows)]


def test_basic():
    """任意尺寸：数字 1 周围只剩 1 个未知格 -> 必为雷"""
    cells = grid(5, 7)
    cells[2][3] = (O, 1)
    for (c, r) in [(2, 1), (3, 1), (4, 1), (2, 2), (4, 2), (2, 3), (3, 3), (4, 3)]:
        cells[r][c] = (O, 0)
    cells[1][2] = (H, None)
    st = S.State(FakeBoard(cells, 1))
    safe, mines = S._deduce(st)
    assert safe is not None
    assert (2, 1) in mines, (safe, mines)
    assert (2, 1) not in safe
    print('test_basic 通过')


def test_diff():
    """子集差分：3x3 与 7 格约束相减"""
    cells = grid(6, 6)
    cells[0][0] = (O, 1)
    cells[1][0] = (H, None)
    cells[0][1] = (H, None)
    cells[1][1] = (O, 1)
    for (c, r) in [(2, 0), (2, 1), (1, 2), (0, 2), (2, 2)]:
        cells[r][c] = (H, None)
    st = S.State(FakeBoard(cells, 1))
    safe, mines = S._deduce(st)
    assert safe is not None
    assert {(2, 0), (2, 1), (1, 2), (0, 2), (2, 2)} <= safe, safe
    assert not mines, mines
    print('test_diff 通过')


def test_probs():
    """概率：1 周围两个未知格各 50%"""
    cells = grid(8, 8)
    for r in range(3, 8):
        for c in range(3, 8):
            cells[r][c] = (O, 0)
    cells[5][5] = (O, 1)
    cells[4][5] = (H, None)
    cells[4][4] = (H, None)
    st = S.State(FakeBoard(cells, 1))
    probs = S.enumerate_probs(st)
    assert probs is not None, '枚举失败'
    assert abs(probs[(5, 4)] - 0.5) < 1e-9, probs
    assert abs(probs[(4, 4)] - 0.5) < 1e-9, probs
    print('test_probs 通过')


def test_total_mines():
    """全局雷数约束：非前沿格概率必须为 1"""
    cells = grid(10, 10)
    cells[5][5] = (O, 1)
    cells[5][4] = (H, None)     # 格子 (4,5)
    cells[4][4] = (H, None)     # 格子 (4,4)
    cells[2][7] = (H, None)     # 格子 (7,2) 非前沿
    st = S.State(FakeBoard(cells, 2))
    probs = S.enumerate_probs(st)
    assert probs is not None
    assert len(probs) == 3, probs
    assert abs(probs[(4, 5)] - 0.5) < 1e-9, probs
    assert abs(probs[(4, 4)] - 0.5) < 1e-9, probs
    assert abs(probs[(7, 2)] - 1.0) < 1e-9, probs
    print('test_total_mines 通过')


def test_chord():
    """chord 判定"""
    cells = grid(6, 6)
    cells[2][2] = (O, 1)
    cells[1][1] = (F, None)      # 旗子
    cells[2][1] = (H, None)      # 未翻开
    cells[3][2] = (O, 0)
    st = S.State(FakeBoard(cells, 1))
    ch = S.chordable(st)
    assert (2, 2) in ch, ch
    cells[2][1] = (F, None)
    st = S.State(FakeBoard(cells, 1))
    assert (2, 2) not in S.chordable(st), '旗满但无未知格时不该 chord'
    print('test_chord 通过')


def test_consistency():
    """随机局面下 deduce 结论自洽"""
    import random
    random.seed(11)
    for t in range(20):
        rows, cols = 16, 30
        cells = [[(H, None) for _ in range(cols)] for _ in range(rows)]
        for _ in range(120):
            c, r = random.randrange(cols), random.randrange(rows)
            cells[r][c] = (O, 0)
        for r in range(rows):
            for c in range(cols):
                if cells[r][c][0] == O:
                    n = sum(1 for (nc, nr) in S.neighbors(c, r, cols, rows)
                            if cells[nr][nc][0] in (H, F))
                    cells[r][c] = (O, min(n, 8))
        st = S.State(FakeBoard(cells, 99))
        safe, mines = S._deduce(st)
        if safe is None:
            continue
        assert not (safe & mines), f'第{t}例冲突 {safe & mines}'
    print('test_consistency 通过')


for f in (test_basic, test_diff, test_probs, test_total_mines, test_chord, test_consistency):
    f()
print('全部通过')
