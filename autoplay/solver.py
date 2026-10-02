"""扫雷求解器：约束传播 + 分量枚举 + 全局雷数约束下的精确概率。

行列数与总雷数都来自棋盘本身（自动识别），因此支持初级/中级/高级/自定义/残局。
"""
from collections import defaultdict


def neighbors(c, r, cols, rows):
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            nc, nr = c + dc, r + dr
            if 0 <= nc < cols and 0 <= nr < rows:
                yield nc, nr


class State:
    """从 board.Board 构建的求解状态。"""

    def __init__(self, bd):
        self.cols = bd.cols
        self.rows = bd.rows
        self.open = bd.opened()            # {(c,r): 数字}
        self.flags = bd.flagged()
        self.unknown = bd.unknown()        # 未翻开（含问号）
        self.total_mines = bd.total_mines()

    def nb(self, c, r):
        return neighbors(c, r, self.cols, self.rows)

    def frontier(self):
        """紧邻已翻开数字格的未知格。"""
        f = set()
        for (c, r), v in self.open.items():
            if v > 0:
                for n in self.nb(c, r):
                    if n in self.unknown:
                        f.add(n)
        return f


def _cons(st, extra_flags, extra_safe=frozenset()):
    """返回 [(U, need)]：U = 仍未知的候选格，need = 该数字格还缺几颗雷。

    U 必须排除所有已知雷与已知安全格，否则 need 会被重复扣减。
    """
    fl = st.flags | set(extra_flags)
    sf = set(extra_safe)
    out = []
    for (c, r), v in st.open.items():
        if v == 0:
            continue
        U = frozenset(n for n in st.nb(c, r)
                      if n in st.unknown and n not in fl and n not in sf)
        m = sum(1 for n in st.nb(c, r) if n in fl)
        need = v - m
        if not U:
            if need != 0:
                return None      # 矛盾（旗插错了）
            continue
        out.append((U, need))
    return out


def _deduce(st):
    safe, mines = set(), set()
    for _ in range(100):
        cs = _cons(st, mines, safe)
        if cs is None:
            return None, None
        new_safe, new_mines = set(), set()
        for U, need in cs:
            if need > len(U) or need < 0:
                return None, None
            if need == 0:
                new_safe |= U
            elif need == len(U):
                new_mines |= U
        # 子集（差分）规则：只比较共享格子的约束对
        lst = [(set(U), need) for U, need in cs]
        by_cell = defaultdict(list)
        for idx, (U, _) in enumerate(lst):
            for g in U:
                by_cell[g].append(idx)
        pairs = set()
        for g, idxs in by_cell.items():
            if len(idxs) < 2:
                continue
            for i in range(len(idxs)):
                for j in range(i + 1, len(idxs)):
                    pairs.add((idxs[i], idxs[j]))
        for i, j in pairs:
            Ui, ni = lst[i]
            Uj, nj = lst[j]
            if Ui < Uj:
                diff = Uj - Ui
                nd = nj - ni
            elif Uj < Ui:
                diff = Ui - Uj
                nd = ni - nj
            else:
                continue
            if nd == 0:
                new_safe |= diff
            elif nd == len(diff):
                new_mines |= diff
        news = new_safe - safe - mines - st.flags
        newm = new_mines - safe - mines - st.flags - news
        if not news and not newm:
            break
        safe |= news
        mines |= newm
    return safe, mines


class _DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


MAX_ENUM = 22


def enumerate_probs(st, extra_mines=frozenset()):
    """精确枚举前沿 + 全局雷数约束，返回 {cell: prob_mine}；失败返回 None。"""
    mines_known = st.flags | set(extra_mines)
    unknown = st.unknown - set(extra_mines)
    if not unknown:
        return {}
    total = st.total_mines
    if total is None:
        total = int(round(len(unknown) * 0.206)) + len(mines_known)
    R = total - len(mines_known)
    cs = _cons(st, mines_known, set())
    if cs is None:
        return None
    cons = [(set(U), need) for U, need in cs]
    frontier = set()
    for U, _ in cons:
        frontier |= U
    nonfront = unknown - frontier
    if R < 0 or R > len(unknown):
        return None

    dsu = _DSU()
    for U, _ in cons:
        lu = list(U)
        for x in lu[1:]:
            dsu.union(lu[0], x)
    groups = defaultdict(list)
    for g in frontier:
        groups[dsu.find(g)].append(g)

    comps = []
    for root, cells in groups.items():
        k = len(cells)
        if k > MAX_ENUM:
            return None
        idx = {g: i for i, g in enumerate(cells)}
        cellset = set(cells)
        mycons = [(U, need) for U, need in cons if U <= cellset]
        sols = []
        for mask in range(1 << k):
            ok = True
            for U, need in mycons:
                cnt = 0
                for g in U:
                    if mask >> idx[g] & 1:
                        cnt += 1
                if cnt != need:
                    ok = False
                    break
            if ok:
                sols.append((mask, bin(mask).count('1')))
        if not sols:
            return None
        counts = defaultdict(int)
        for _, pc in sols:
            counts[pc] += 1
        comps.append({'cells': cells, 'idx': idx, 'sols': sols, 'counts': counts})

    nf = len(nonfront)
    lo = max(0, R - nf)
    hi = min(R, len(frontier))
    if lo > hi:
        return None

    def convolve(a, b):
        out = defaultdict(int)
        for ka, va in a.items():
            for kb, vb in b.items():
                out[ka + kb] += va * vb
        return out

    m = len(comps)
    left = [defaultdict(int) for _ in range(m + 1)]
    left[0][0] = 1
    for i, cp in enumerate(comps):
        left[i + 1] = convolve(left[i], cp['counts'])
    right = [defaultdict(int) for _ in range(m + 1)]
    right[m][0] = 1
    for i in range(m - 1, -1, -1):
        right[i] = convolve(right[i + 1], comps[i]['counts'])

    total_valid = sum(c for k, c in left[m].items() if lo <= k <= hi)
    if total_valid == 0:
        return None

    probs = {}
    for i, cp in enumerate(comps):
        pair = convolve(left[i], right[i + 1])
        pc = defaultdict(int)
        for mask, x in cp['sols']:
            w = 0
            for t in range(lo - x, hi - x + 1):
                if t in pair:
                    w += pair[t]
            if w == 0:
                continue
            for g in cp['cells']:
                if mask >> cp['idx'][g] & 1:
                    pc[g] += w
        for g in cp['cells']:
            probs[g] = pc[g] / total_valid

    if nf:
        acc = 0
        for k, cnt in left[m].items():
            if lo <= k <= hi:
                acc += cnt * (R - k)
        p = acc / total_valid / nf
        for g in nonfront:
            probs[g] = p
    return probs


def solve(st):
    """返回 (safe[], mines[], probs or None)。safe/mines 为建议下一步操作的格子。"""
    safe, mines = _deduce(st)
    if safe is None:
        return [], [], None
    if safe or mines:
        return sorted(safe), sorted(mines), None
    probs = enumerate_probs(st)
    return [], [], probs


def chordable(st):
    """可以安全使用“左右键同时按(chord)”翻开的已翻开数字格列表。

    条件：周围插旗数 == 数字，且周围仍有未翻开的非旗格。
    """
    out = []
    for (c, r), v in st.open.items():
        if v <= 0:
            continue
        fl = 0
        un = 0
        for n in st.nb(c, r):
            if n in st.flags:
                fl += 1
            elif n in st.unknown:
                un += 1
        if fl == v and un > 0:
            out.append((c, r))
    return out
