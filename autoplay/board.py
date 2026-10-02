"""棋盘读取：基于 layout 的全自动几何 + numpy 向量化状态识别。

支持任意行列数（初级/中级/高级/自定义）以及中途接手的残局。
"""
import ctypes, time, sys
import numpy as np
from PIL import Image, ImageGrab
import windows as W
import win as WIN
import layout as L

CN = {'hidden': '#', 'flag': 'F', 'question': '?', 'open': '.'}

DIGIT_COLORS = {
    1: (0, 0, 255), 2: (0, 128, 0), 3: (255, 0, 0), 4: (0, 0, 128),
    5: (128, 0, 0), 6: (0, 128, 128), 7: (0, 0, 0), 8: (128, 128, 128),
}


class Board:
    def __init__(self, lay, cells, counts, red_frac=None, black_frac=None):
        self.layout = lay
        self.cells = cells          # cells[r][c] = (state, value)
        self.counts = counts        # {'hidden':n, 'flag':n, 'open':n, 'question':n}
        self.red_frac = red_frac    # 每格内部红色像素占比（用于识别爆炸）
        self.black_frac = black_frac

    def boom_score(self):
        """最大单格红色占比（踩中的雷格 ≈0.45，数字3 ≈0.43，旗子 ≈0.12）。"""
        if self.red_frac is None:
            return 0.0
        return float(self.red_frac.max())

    def boom_cells(self):
        """踩中的雷格 = 红底(高红占比) + 黑雷(有黑色)。数字3只有红没有黑，不会误判。"""
        if self.red_frac is None or self.black_frac is None:
            return []
        m = (self.red_frac > 0.35) & (self.black_frac > 0.08)
        out = []
        for r in range(self.rows):
            for c in range(self.cols):
                if m[r, c]:
                    out.append((c, r))
        return out

    def is_boom(self):
        return len(self.boom_cells()) > 0

    @property
    def rows(self):
        return self.layout.rows

    @property
    def cols(self):
        return self.layout.cols

    def total_mines(self):
        """总雷数 = 计数器(剩余雷) + 已插旗数（对残局同样成立）。"""
        if self.layout.mines_left is None:
            return None
        return self.layout.mines_left + self.counts['flag']

    def unknown(self):
        return {(c, r) for r in range(self.rows) for c in range(self.cols)
                if self.cells[r][c][0] in ('hidden', 'question')}

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

    def render(self):
        lines = []
        for r in range(self.rows):
            s = ''
            for c in range(self.cols):
                st, v = self.cells[r][c]
                if st == 'open':
                    s += '.' if not v else str(v)
                else:
                    s += CN.get(st, 'X')
            lines.append(s)
        return '\n'.join(lines)


def _grab_once(settle=0.15, imgpath=None):
    h = W.ensure_front()
    if not h:
        raise RuntimeError('找不到扫雷窗口')
    l, t, r, b = W.window_rect(h)
    w, hh = r - l, b - t
    img = None
    for _ in range(8):
        img = ImageGrab.grab(bbox=(l, t, r, b), all_screens=True).convert('RGB')
        if img.size == (w, hh):
            break
        time.sleep(0.12)
    if img.size != (w, hh):
        img = img.resize((w, hh))
    if imgpath:
        img.save(imgpath)
    return img, (l, t)


def _same_image(a, b, step=3):
    """降采样比对（3x3 取一点），比整幅 array_equal 快约 9 倍。"""
    A = np.asarray(a)
    B = np.asarray(b)
    if A.shape != B.shape:
        return False
    return np.array_equal(A[::step, ::step], B[::step, ::step])


def grab(imgpath=None, settle=0.10, stable=False):
    """抓取扫雷主窗口（窗口句柄缓存 + 每次重新取位置）。

    stable=True 时连抓两张，内容一致才返回 —— 大棋盘上一次 chord 会翻开
    二三十格，重绘期间截图容易抓到中间态，导致下一轮基于过时棋盘推理而误判。
    """
    img, origin = _grab_once(settle, imgpath)
    if not stable:
        return img, origin
    for _ in range(3):
        time.sleep(0.04)
        cur, o2 = _grab_once(0.03, None)
        if _same_image(cur, img):
            return cur, o2
        img = cur
    return img, origin


def read(img, lay):
    """把窗口截图解析成 Board。"""
    a = np.asarray(img.convert('RGB')).astype(np.int16)
    H, Wd = a.shape[:2]
    cell, cols, rows = lay.cell, lay.cols, lay.rows
    gx, gy = lay.gx, lay.gy
    need_w, need_h = cols * cell, rows * cell
    if gx < 0 or gy < 0 or gx + need_w > Wd or gy + need_h > H:
        # 几何越界：夹到图内
        gx = max(0, min(gx, Wd - need_w)) if need_w <= Wd else 0
        gy = max(0, min(gy, H - need_h)) if need_h <= H else 0
        need_w = min(need_w, Wd - gx)
        need_h = min(need_h, H - gy)
    region = a[gy:gy + need_h, gx:gx + need_w]
    rows = need_h // cell
    cols = need_w // cell
    g = region.reshape(rows, cell, cols, cell, 3).transpose(0, 2, 1, 3, 4)

    tl = g[:, :, 1, 1, :]
    br = g[:, :, cell - 2, cell - 2, :]
    hidden = ((tl > 240).all(axis=-1) & (np.abs(br - 128) <= 32).all(axis=-1))

    inner = g[:, :, 2:cell - 2, 2:cell - 2, :].astype(np.int16)
    r_ch, g_ch, b_ch = inner[:, :, :, :, 0], inner[:, :, :, :, 1], inner[:, :, :, :, 2]
    red = (r_ch > 170) & (g_ch < 110) & (b_ch < 110)
    black = (r_ch < 70) & (g_ch < 70) & (b_ch < 70)
    red_n = red.sum(axis=(2, 3))
    black_n = black.sum(axis=(2, 3))

    counts = {'hidden': 0, 'flag': 0, 'question': 0, 'open': 0}
    cells = [[('hidden', None)] * cols for _ in range(rows)]
    # 数字颜色计数（只对已翻开格有意义）
    color_n = {}
    for d, rgb in DIGIT_COLORS.items():
        m = ((np.abs(r_ch - rgb[0]) <= 26) & (np.abs(g_ch - rgb[1]) <= 26)
             & (np.abs(b_ch - rgb[2]) <= 26))
        color_n[d] = m.sum(axis=(2, 3))

    for rr in range(rows):
        for cc in range(cols):
            if hidden[rr, cc]:
                if red_n[rr, cc] >= 5:
                    cells[rr][cc] = ('flag', None)
                    counts['flag'] += 1
                elif black_n[rr, cc] >= 5:
                    cells[rr][cc] = ('question', None)
                    counts['question'] += 1
                else:
                    cells[rr][cc] = ('hidden', None)
                    counts['hidden'] += 1
            else:
                best, bn = 0, 0
                for d in range(1, 9):
                    n = int(color_n[d][rr, cc])
                    if n > bn:
                        best, bn = d, n
                # 采样偶尔会蹭到棋盘边框的深灰(128)，那种杂点只有很少几个像素；
                # 真数字有几十个像素，所以用最小像素数挡掉误判。
                if best == 8 and bn < 8:
                    best = 0
                elif bn < 4:
                    best = 0
                cells[rr][cc] = ('open', best)
                counts['open'] += 1
    return Board(lay, cells, counts,
                 red_frac=red_n / float(inner.shape[2] * inner.shape[3]),
                 black_frac=black_n / float(inner.shape[2] * inner.shape[3]))


def read_auto(imgpath=None):
    """抓图 + 检测布局 + 读盘，一步到位。"""
    img, origin = grab(imgpath)
    lay = L.detect(img)
    bd = read(img, lay)
    return bd, img, origin


def score_layout(bd, wmask=None):
    """用读盘结果的自洽性打分（越小越好，0 = 完全自洽）。

    三组判据：
      1. 扫雷规则本身必然成立的约束 —— 数字格周围的旗数不能超过该数字，
         且「旗 + 未知格」必须装得下它要求的雷。布局识别错时采样整体错位，
         读出来的数字和旗帜会大量互相矛盾。
      2. 几何贴合 —— 布局起点附近应该确实有一条未翻开格的白边高光。
      3. 覆盖完整 —— 只能覆盖棋盘一部分的「子网格」（比如少算最左一列）
         本身可能毫无矛盾，得靠「最左侧那条深灰网格线有没有被第一格包住」
         来识别。
    """
    bad = 0
    cells = bd.cells
    cols, rows = bd.cols, bd.rows
    for (c, r), v in bd.opened().items():
        if v <= 0:
            continue
        fl = un = 0
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = c + dc, r + dr
                if not (0 <= nc < cols and 0 <= nr < rows):
                    continue
                s = cells[nr][nc][0]
                if s == 'flag':
                    fl += 1
                elif s in ('hidden', 'question'):
                    un += 1
        if fl > v or fl + un < v:
            bad += 1

    lay = bd.layout
    tol = max(2, lay.cell // 2)

    if wmask is not None and wmask.any():
        cprof = wmask.sum(axis=0)
        rprof = wmask.sum(axis=1)
        cols_w = np.nonzero(cprof > max(3, cprof.max() * 0.4))[0]
        rows_w = np.nonzero(rprof > max(3, rprof.max() * 0.4))[0]
        # 列方向：未翻开格白边的起点是可靠的横向锚点，布局从这儿开始才对。
        # 起点偏出一格以上，就说明要么把棋盘外当成了一列，要么漏掉了最左一列。
        if cols_w.size >= 3 and abs(int(cols_w[0]) - lay.gx) > lay.cell:
            bad += 15
        # 行方向：窗口顶部（菜单栏/边框）也会在行投影里冒出尖峰，位置是噪声，
        # 所以这里只问「起点附近有没有白边」，不拿第一条当基准。
        if rows_w.size >= 3 and not np.any(np.abs(rows_w - lay.gy) <= tol):
            bad += 10
    return bad


def read_best(img):
    """在所有候选布局里挑一个读盘最自洽的，返回 (layout, board)。

    这是残局接手的关键：棋盘展开大半之后白边所剩无几，投影法可能失效，
    这时靠打分能把「经典公式法猜错的 16px 行列数」以及「少算一列的子网格」
    都挡掉，选回正确几何。
    """
    arr = np.asarray(img.convert('RGB'))
    wmask = (arr[:, :, 0] > 240) & (arr[:, :, 1] > 240) & (arr[:, :, 2] > 240)
    dmask = ((np.abs(arr[:, :, 0] - 128) < 30) & (np.abs(arr[:, :, 1] - 128) < 30)
             & (np.abs(arr[:, :, 2] - 128) < 30))
    cands = L.detect_candidates(img)
    best = None
    for lay in cands:
        try:
            bd = read(img, lay)
        except Exception:                        # noqa: BLE001
            continue
        s = score_layout(bd, wmask)
        if best is None or s < best[0]:
            best = (s, lay, bd)
        if s == 0:
            break
    if best is None:
        lay = L.detect(img)
        return lay, read(img, lay)
    return best[1], best[2]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    bd, img, origin = read_auto('auto_board.png')
    print('窗口原点', origin, '截图', img.size)
    print(bd.layout)
    print('总雷数', bd.total_mines(), '统计', bd.counts)
    print(bd.render())
