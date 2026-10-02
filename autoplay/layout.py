"""自动识别扫雷窗口布局：棋盘几何（任意行列）、雷数计数器、计时器。

不依赖窗口位置；每次调用都用当前截图重新检测，因此窗口移动、切换难度、
自定义雷区、载入残局都无需任何预设参数。
"""
import numpy as np

# ---- 七段数码管 ----
DIGIT_SEGS = {
    'abcdef': 0, 'bc': 1, 'abdeg': 2, 'abcdg': 3, 'bcfg': 4,
    'acdfg': 5, 'acdefg': 6, 'abc': 7, 'abcdefg': 8, 'abcdfg': 9,
}
SEG_POS = {
    # 采样点取在段的大致中心；比例特意选在「经典 13px 数码管」与
    # 「本项目 Java 版 16px 数码管」之间，两边都能采到。
    'a': (0.45, 0.04), 'b': (0.80, 0.22), 'c': (0.80, 0.73),
    'd': (0.45, 0.91), 'e': (0.13, 0.73), 'f': (0.13, 0.22), 'g': (0.47, 0.46),
}

CELL_DEFAULT = 16
MARGIN_X = 26      # 窗口宽 - 列数*格子
MARGIN_Y = 112     # 窗口高 - 行数*格子
PAD_R = 11         # 棋盘右侧留白
PAD_B = 11         # 棋盘底部留白


class Layout:
    def __init__(self, cols, rows, cell, gx, gy, mines_left=None, timer=None, source='formula'):
        self.cols = cols
        self.rows = rows
        self.cell = cell
        self.gx = gx
        self.gy = gy
        self.mines_left = mines_left   # 计数器当前显示值（游戏中=剩余雷数）
        self.timer = timer
        self.source = source

    def __repr__(self):
        return (f'<Layout {self.cols}x{self.rows} cell={self.cell} '
                f'origin=({self.gx},{self.gy}) mines_left={self.mines_left} '
                f'timer={self.timer} src={self.source}>')

    def cell_box(self, c, r):
        x = self.gx + c * self.cell
        y = self.gy + r * self.cell
        return x, y, x + self.cell, y + self.cell

    def center_in_window(self, c, r):
        return (self.gx + c * self.cell + self.cell // 2,
                self.gy + r * self.cell + self.cell // 2)


def find_panels(a):
    """找窗口上方的数码管面板（深色背景）。返回 [(x0,x1,y0,y1), ...]。

    搜索区间按窗口高度取比例，避免写死坐标 —— 经典版和 Java 版的
    面板高度/位置都不一样。
    """
    h, w = a.shape[:2]
    y0 = max(15, int(h * 0.03))
    y1 = min(h, int(h * 0.45))
    if y1 - y0 < 12:
        y0, y1 = 15, min(h, 120)
    sub = a[y0:y1].astype(np.int32)
    dark = sub.sum(axis=2) < 350
    colcnt = dark.sum(axis=0)
    need = 8
    panels = []
    i = 0
    while i < w:
        if colcnt[i] >= need:
            j = i
            while j + 1 < w and colcnt[j + 1] >= need:
                j += 1
            if j - i + 1 >= 20:          # 面板是整块黑底，不会只有几个像素宽
                rows = dark[:, i:j + 1].sum(axis=1)
                nz = np.nonzero(rows >= (j - i + 1) * 0.4)[0]
                if len(nz) >= 8:
                    panels.append((i, j, y0 + int(nz.min()), y0 + int(nz.max())))
            i = j + 1
        else:
            i += 1
    return panels


def _try_read(red, ox, oy, cw, ch):
    """按给定的字符起点/宽高尝试识别三位数字，任何一位辨不出就返回 None。"""
    H, W = red.shape
    out = ''
    for i in range(3):
        cx = ox + i * cw
        lit = []
        for k, (fx, fy) in SEG_POS.items():
            px = int(round(cx + fx * cw))
            py = int(round(oy + fy * ch))
            if px < 2 or py < 2 or px > W - 3 or py > H - 3:
                return None
            frac = red[py - 2:py + 3, px - 2:px + 3].mean()   # 5x5，容忍两版数码管的比例差
            if frac > 0.25:
                lit.append(k)
        d = DIGIT_SEGS.get(''.join(sorted(lit)))
        if d is None:
            return None
        out += str(d)
    return out


def read_digits(a, panel):
    """读一个三位数码管面板。

    先用亮红像素的包围盒定位数字区域，再在「字符起点 + 字符宽度」上搜索，
    把所有能识别成功的组合拿来**加权投票**（越接近理想宽度/起点的权重越高），
    取票数最高的那个 —— 单看第一个成功的组合很容易命中错误参数。
    """
    x0, x1, y0, y1 = panel
    red = (a[:, :, 0] > 150) & (a[:, :, 1] < 120) & (a[:, :, 2] < 120)
    sub = red[y0:y1 + 1, x0:x1 + 1]
    ys, xs = np.nonzero(sub)
    if xs.size == 0:
        return None
    ry0, ry1 = int(ys.min()), int(ys.max())
    rx0 = int(xs.min())
    ch = ry1 - ry0 + 1
    if ch < 8:
        return None
    oy = y0 + ry0
    start = x0 + rx0
    ideal_cw = (x1 - x0 + 1) / 3.0

    votes = {}
    for cw in range(12, 26):
        w_cw = 1.0 / (1.0 + abs(cw - ideal_cw))
        for ox in range(start - 17, start + 3):
            got = _try_read(red, ox, oy, cw, ch)
            if got is None:
                continue
            w = w_cw / (1.0 + abs(ox - start))
            votes[got] = votes.get(got, 0.0) + w
    if not votes:
        return None
    best = max(votes.items(), key=lambda kv: kv[1])[0]
    return int(best)


def _project_peaks(mask, axis, min_frac=0.5, min_abs=110):
    """沿指定轴投影，返回候选边线与它们的高度。

    阈值取得比较高（峰值的 50%）：真正的格子边线在整列/整行上都是白，计数接近
    「格子数 × 格子高」，而菜单栏、按钮高光这类界面白色只有零散几十个像素。
    阈值太低会把二者粘成一大片，边线位置就全偏了。
    """
    proj = mask.sum(axis=axis)
    if proj.size == 0 or proj.max() == 0:
        return [], []
    thr = max(min_abs, proj.max() * min_frac)
    idx = np.nonzero(proj > thr)[0]
    if idx.size == 0:
        return [], []
    edges, heights = [], []
    cur = [int(idx[0])]
    for i in idx[1:]:
        i = int(i)
        if i - cur[-1] <= 2:
            cur.append(i)
        else:
            edges.append(cur[0])
            heights.append(int(proj[cur[0]]))
            cur = [i]
    edges.append(cur[0])
    heights.append(int(proj[cur[0]]))
    return edges, heights


def _longest_equidistant(edges):
    """从候选边线里抽出最长的等距子序列 —— 那才是棋盘真正的网格。"""
    if len(edges) < 3:
        return None, None
    diffs = [b - a for a, b in zip(edges, edges[1:])]
    cand = [d for d in diffs if 6 <= d <= 64]
    if not cand:
        return None, None
    cell = int(np.bincount(cand).argmax())
    best = []
    for s in range(len(edges)):
        seq = [edges[s]]
        for e in edges[s + 1:]:
            if abs(e - seq[-1] - cell) <= 1:
                seq.append(e)
        if len(seq) > len(best):
            best = seq
    if len(best) < 3:
        return None, None
    return best, cell


def _aligns_grid(v, origin, cell, tol=2):
    """v 是否落在网格线上（格子右边线在 origin + k*cell - 2 附近）。"""
    r = (v - origin) % cell
    return r <= tol or r >= cell - tol


def _grid_span(white_edges, gray_edges, origin, cell):
    """白色边线定网格，再逐格用深灰边线向右/向下延伸。

    已翻开的格子没有白边，但一定有深灰网格线。只有当"下一格的右边线"确实存在时
    才继续延伸，这样既能补回被吞掉的列，又不会被窗口底部控制条的深灰带跑偏。
    """
    n = len(white_edges)
    if n == 0:
        return 0
    last = white_edges[-1]
    gray = [v for v in gray_edges if v > last + 3 and _aligns_grid(v, origin, cell)]
    while gray:
        want_right = origin + n * cell + cell - 1      # 下一格的右边线位置
        if any(abs(v - want_right) <= 3 for v in gray):
            n += 1
        else:
            break
    return n


def detect_grid_projection(a):
    """通用网格检测（白色定网格 + 深灰补边界），返回单个结果或 None。

    保留这个入口是给「只要一个最可能的几何」的调用方用的；
    残局等容易认错的场景请改用 detect_candidates + board.read_best。
    """
    Wm = (a[:, :, 0] > 240) & (a[:, :, 1] > 240) & (a[:, :, 2] > 240)
    Dm = ((np.abs(a[:, :, 0] - 128) < 30) & (np.abs(a[:, :, 1] - 128) < 30)
          & (np.abs(a[:, :, 2] - 128) < 30))
    xw, _ = _project_peaks(Wm, 0)
    yw, _ = _project_peaks(Wm, 1)
    xd, _ = _project_peaks(Dm, 0)
    yd, _ = _project_peaks(Dm, 1)
    xg, cw = _longest_equidistant(xw)
    yg, ch = _longest_equidistant(yw)
    if not xg or not yg or cw is None or ch is None:
        return None
    if abs(cw - ch) > 2 or not (6 <= cw <= 64):
        return None
    cols = _grid_span(xg, xd, xg[0], cw)
    rows = _grid_span(yg, yd, yg[0], ch)
    return cols, rows, cw, xg[0], yg[0], 'projection'


def detect_grid(a, win_w, win_h):
    """返回 (cols, rows, cell, gx, gy, source)。"""
    cell = CELL_DEFAULT
    cols = max(1, int(round((win_w - MARGIN_X) / cell)))
    rows = max(1, int(round((win_h - MARGIN_Y) / cell)))
    gx = win_w - cols * cell - PAD_R
    gy = win_h - rows * cell - PAD_B
    source = 'formula'
    # 公式自洽性检查：棋盘必须落在窗口内且留白合理
    sane = (0 <= gx <= 40) and (0 <= gy <= 200) and (cols >= 5) and (rows >= 5)
    if sane:
        return cols, rows, cell, gx, gy, source
    # 兜底：靠“未翻开格左上角”的像素模式直接找网格
    Wm = (a[:, :, 0] > 245) & (a[:, :, 1] > 245) & (a[:, :, 2] > 245)
    Dm = ((np.abs(a[:, :, 0] - 128) < 30) & (np.abs(a[:, :, 1] - 128) < 30)
          & (np.abs(a[:, :, 2] - 128) < 30))
    tl = Wm[:-1, :-1] & Wm[:-1, 1:] & Wm[1:, :-1] & Wm[1:, 1:]
    br = Dm[:-1, :-1] & Dm[:-1, 1:] & Dm[1:, :-1] & Dm[1:, 1:]
    H, W = a.shape[:2]
    hc, wc = H - 15, W - 15
    cand = tl[:hc, :wc] & br[14:14 + hc, 14:14 + wc]
    pts = np.argwhere(cand)
    if len(pts) < 4:
        return max(1, cols), max(1, rows), cell, max(0, gx), max(0, gy), 'guess'
    xs = np.unique(pts[:, 1])
    ys = np.unique(pts[:, 0])
    diffs = np.diff(xs)
    diffs = diffs[diffs > 3]
    if len(diffs):
        cell = int(np.bincount(diffs).argmax())
    gx = int(xs.min())
    gy = int(ys.min())
    if cell <= 4:
        cell = CELL_DEFAULT
    cols = max(1, (int(xs.max()) - gx) // cell + 1)
    rows = max(1, (int(ys.max()) - gy) // cell + 1)
    return cols, rows, cell, gx, gy, 'pixel'


def detect_candidates(a):
    """给出若干候选布局（含数码管读数），按可信度从高到低。

    为什么要多个候选：投影法靠**未翻开格的白边**，但如果这一局已经展开了一大半，
    白边所剩无几，投影就会失败；此时若直接退化到经典公式法（那套 16px + 固定边距的
    假设对别的实现是错的），就会读出完全错误的行列数 —— 残局接手时的乱点多半源于此。

    所以这里把「白色主导」「深灰主导」「经典公式」三路结果都交出来，由调用方
    （board.read_best）用「读盘结果是否自洽」来挑真正正确的那一个。
    """
    a = np.asarray(a.convert('RGB')).astype(np.int32)
    win_h, win_w = a.shape[:2]
    panels = find_panels(a)
    mines_left = read_digits(a, panels[0]) if panels else None
    timer = read_digits(a, panels[1]) if len(panels) > 1 else None
    out = []

    def add(cols, rows, cell, gx, gy, src):
        if cols < 2 or rows < 2 or not (5 <= cell <= 64):
            return
        if gx < 0 or gy < 0 or gx + cols * cell > win_w + 2 or gy + rows * cell > win_h + 2:
            return
        for c in out:
            if (c.cols, c.rows, c.cell, c.gx, c.gy) == (cols, rows, cell, gx, gy):
                return
        out.append(Layout(cols, rows, cell, gx, gy, mines_left, timer, src))

    Wm = (a[:, :, 0] > 240) & (a[:, :, 1] > 240) & (a[:, :, 2] > 240)
    Dm = ((np.abs(a[:, :, 0] - 128) < 30) & (np.abs(a[:, :, 1] - 128) < 30)
          & (np.abs(a[:, :, 2] - 128) < 30))
    xw, _ = _project_peaks(Wm, 0)
    yw, _ = _project_peaks(Wm, 1)
    xd, _ = _project_peaks(Dm, 0, min_frac=0.35, min_abs=25)
    yd, _ = _project_peaks(Dm, 1, min_frac=0.35, min_abs=25)

    # A) 白色主导 —— 新手局最准
    xg, cw = _longest_equidistant(xw)
    yg, ch = _longest_equidistant(yw)
    if xg and yg and cw and ch and abs(cw - ch) <= 2:
        add(_grid_span(xg, xd, xg[0], cw), _grid_span(yg, yd, yg[0], ch),
            cw, xg[0], yg[0], 'projection-white')

    # B) 深灰主导 —— 残局的靠山（每个格子无论翻开与否都有深灰边线）
    xgd, cwd = _longest_equidistant(xd)
    ygd, chd = _longest_equidistant(yd)
    if xgd and ygd and cwd and chd and abs(cwd - chd) <= 2:
        # 深灰落在格子右边线上，左边界要往左退 cell-2。
        # 首条边线有可能是棋盘外框，所以横竖两个方向各自「用/不用首条」都试一遍
        # —— 比如 Java 版的竖向外框会被算进来，而横向不会。
        xs = (0, 1) if len(xgd) >= 4 else (0,)
        ys = (0, 1) if len(ygd) >= 4 else (0,)
        for di in xs:
            for dj in ys:
                add(len(xgd) - di, len(ygd) - dj, cwd,
                    xgd[di] - cwd + 2, ygd[dj] - chd + 2,
                    f'projection-gray{di}{dj}')

    # C) 经典公式法 —— 只对经典 saolei.exe 有效，当兜底
    try:
        f = detect_grid(a, win_w, win_h)
        if f:
            add(f[0], f[1], f[2], f[3], f[4], f[5])
    except Exception:                            # noqa: BLE001
        pass

    return out


def detect(img):
    """识别布局，返回可信度最高的那个候选（不做读盘自洽性校验）。"""
    cands = detect_candidates(img)
    if cands:
        return cands[0]
    a = np.asarray(img.convert('RGB')).astype(np.int32)
    win_h, win_w = a.shape[:2]
    cols, rows, cell, gx, gy, src = detect_grid(a, win_w, win_h)
    return Layout(cols, rows, cell, gx, gy, None, None, src)


if __name__ == '__main__':
    import sys
    import board as B
    sys.stdout.reconfigure(encoding='utf-8')
    img, origin = B.grab()
    lay = detect(img)
    print(origin, img.size)
    print(lay)
    print('panels:', find_panels(img))
