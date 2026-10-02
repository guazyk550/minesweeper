"""按窗口标题查找任意窗口并截图（测试用）。"""
import ctypes
import sys
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.WinDLL('user32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]


def find(title_part):
    found = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(h, l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            if title_part in buf.value and user32.IsWindowVisible(h):
                found.append((h, buf.value))
        return True

    user32.EnumWindows(CB(cb), 0)
    return found


def shot(title_part, out):
    ws = find(title_part)
    if not ws:
        print('找不到窗口:', title_part)
        return None
    h = ws[0][0]
    user32.SetForegroundWindow(h)
    r = RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True)
    img.save(out)
    print('saved', out, img.size, 'from', ws[0][1], (r.left, r.top))
    return h


if __name__ == '__main__':
    title = sys.argv[1] if len(sys.argv) > 1 else '扫雷'
    out = sys.argv[2] if len(sys.argv) > 2 else r'D:\gua550\minesweeper\shot.png'
    print(find(title))
    shot(title, out)
