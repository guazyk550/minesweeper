"""模拟真人操作 Java 扫雷窗口：点开格子、右键插旗、双键 chord，并截图。"""
import ctypes
import sys
import time

sys.path.insert(0, r'D:\gua550\saolei_bot')
sys.path.insert(0, r'D:\gua550\minesweeper\tools')
from ctypes import wintypes
from PIL import ImageGrab
import mouse
from shot_any import find, RECT, user32


def rect_of(h):
    r = RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def shot(h, out):
    l, t, r, b = rect_of(h)
    img = ImageGrab.grab(bbox=(l, t, r, b), all_screens=True)
    img.save(out)
    return img.size


def cell_xy(l, t, w, hh, gx_frac, gy_frac):
    return l + int(w * gx_frac), t + int(hh * gy_frac)


def main():
    ws = find('Minesweeper')
    if not ws:
        print('窗口没找到')
        return
    h = ws[0][0]
    user32.SetForegroundWindow(h)
    time.sleep(0.4)
    l, t, r, b = rect_of(h)
    w, hh = r - l, b - t
    print('窗口', (l, t, r, b), '尺寸', (w, hh))

    # 1) 点棋盘中心开局（生成雷区 + 展开）
    cx, cy = cell_xy(l, t, w, hh, 0.5, 0.55)
    print('点击棋盘中心', (cx, cy))
    mouse.left(cx, cy, delay=2.5)
    print('开局截图', shot(h, r'D:\gua550\minesweeper\manual1.png'))

    # 2) 右键插旗：找一个未翻开格（棋盘左侧区域）
    fx, fy = cell_xy(l, t, w, hh, 0.36, 0.45)
    print('右键插旗', (fx, fy))
    mouse.right(fx, fy, delay=0.5)
    print('插旗截图', shot(h, r'D:\gua550\minesweeper\manual2.png'))


main()
