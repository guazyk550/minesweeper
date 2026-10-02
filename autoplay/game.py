"""扫雷游戏控制：难度切换、自定义雷区、对话框处理（全部基于 Win32 消息，无需点击坐标）。"""
import ctypes, sys, time
from ctypes import wintypes
import win
import windows
import mouse

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetLastActivePopup.argtypes = [wintypes.HWND]
user32.GetLastActivePopup.restype = wintypes.HWND
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]

WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5

MENU_NEW = 510
MENU_BEGINNER = 521
MENU_INTER = 522
MENU_EXPERT = 523
MENU_CUSTOM = 524
MENU_MARKS = 527
MENU_SOUND = 526
MENU_TOP = 528
MENU_EXIT = 512


def text_of(h):
    n = user32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, b, n + 1)
    return b.value


def class_of(h):
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, b, 256)
    return b.value


def enum_children(h):
    out = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(ch, l):
        out.append(ch)
        return True
    user32.EnumChildWindows(h, CB(cb), 0)
    return out


def dialog_of(hwnd=None):
    """当前属于扫雷进程的对话框（按进程枚举，不依赖 GetLastActivePopup）。"""
    ds = windows.dialogs()
    return ds[0]['hwnd'] if ds else None


def close_dialog(hwnd=None):
    return windows.close_dialogs() > 0


def send_menu(mid, hwnd=None):
    hwnd = hwnd or win.find_window()
    user32.PostMessageW(hwnd, WM_COMMAND, mid, 0)
    time.sleep(0.6)


def set_difficulty(mid, hwnd=None):
    close_dialog(hwnd)
    send_menu(mid, hwnd)


def set_custom(width, height, mines, hwnd=None):
    """打开自定义雷区对话框, 用真实键盘输入 高度/宽度/雷数 并点确定。

    注意: 这个程序只认键盘交互（WM_SETTEXT 不触发它的 EN_CHANGE 逻辑），
    所以这里点击输入框 + 全选 + 逐字符敲键盘。
    """
    hwnd = hwnd or windows.find_main()
    windows.close_dialogs()
    send_menu(MENU_CUSTOM, hwnd)
    d = dialog_of(hwnd)
    if not d:
        raise RuntimeError('自定义对话框没有出现')
    edits, ok_btn = [], None
    for ch in enum_children(d):
        cls = class_of(ch)
        if cls == 'Edit':
            edits.append(ch)
        elif cls == 'Button' and '确定' in text_of(ch):
            ok_btn = ch
    edits.sort(key=lambda e: win.window_rect(e)[1])   # 按 y 排序: 高度, 宽度, 雷数
    if len(edits) != 3 or ok_btn is None:
        user32.PostMessageW(d, WM_CLOSE, 0, 0)
        raise RuntimeError(f'控件不符合预期: edits={edits} ok={ok_btn}')
    windows.ensure_front(hwnd)
    for e, v in zip(edits, [height, width, mines]):
        x0, y0, x1, y1 = win.window_rect(e)
        mouse.left((x0 + x1) // 2, (y0 + y1) // 2)
        time.sleep(0.15)
        win.select_all()
        win.press(win.VK_DELETE)
        win.type_text(str(v))
    x0, y0, x1, y1 = win.window_rect(ok_btn)
    mouse.left((x0 + x1) // 2, (y0 + y1) // 2, delay=0.8)
    left = dialog_of(hwnd)
    if left:
        user32.PostMessageW(left, WM_CLOSE, 0, 0)
        time.sleep(0.4)
        raise RuntimeError('自定义参数未被接受（对话框仍在）')


def get_custom_values(hwnd=None):
    """读取当前自定义对话框里的三个值（对话框需已打开）。"""
    hwnd = hwnd or win.find_window()
    d = dialog_of(hwnd)
    if not d:
        return None
    edits = [ch for ch in enum_children(d) if class_of(ch) == 'Edit']
    edits.sort(key=lambda e: win.window_rect(e)[1])
    return [text_of(e) for e in edits]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('对话框:', dialog_of())
    close_dialog()
    print('已关闭 ->', dialog_of())
