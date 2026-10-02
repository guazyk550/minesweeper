import ctypes
from ctypes import wintypes
import os, sys, time

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]

def find_window(title='扫雷'):
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        # enumerate fallback
        found = []
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(h, l):
            n = user32.GetWindowTextLengthW(h)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(h, buf, n + 1)
                if '扫雷' in buf.value or 'mine' in buf.value.lower() or 'saolei' in buf.value.lower():
                    found.append((h, buf.value))
            return True
        user32.EnumWindows(CB(cb), 0)
        if found:
            hwnd = found[0][0]
    return hwnd

def window_rect(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]


def send_enter():
    """发送回车，用于确认模态对话框的默认按钮。"""
    user32.keybd_event(VK_RETURN, 0, 0, None)
    time.sleep(0.03)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, None)


def activate():
    h = find_window()
    if h:
        user32.SetForegroundWindow(h)
        time.sleep(0.08)
    return h


# ---- 键盘 ----
VK_CONTROL = 0x11
VK_DELETE = 0x2E
VK_TAB = 0x09
VK_RETURN_ = 0x0D
VK_ESCAPE = 0x1B

user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]


def key_down(vk):
    user32.keybd_event(vk, 0, 0, None)


def key_up(vk):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)


def press(vk, delay=0.04):
    key_down(vk)
    time.sleep(0.02)
    key_up(vk)
    time.sleep(delay)


def type_text(s, delay=0.04):
    """输入 ASCII 数字/字母（用 VK 码，逐字符）。"""
    for ch in str(s):
        vk = ord(ch.upper())
        key_down(vk)
        time.sleep(0.02)
        key_up(vk)
        time.sleep(delay)


def select_all(delay=0.05):
    key_down(VK_CONTROL)
    time.sleep(0.02)
    press(0x41, 0.02)
    key_up(VK_CONTROL)
    time.sleep(delay)


if __name__ == '__main__':
    hwnd = find_window()
    print('hwnd', hwnd)
    if hwnd:
        print('rect', window_rect(hwnd))
        print('title', end=' ')
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        print(buf.value)
