import ctypes, time
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]


def move(x, y):
    user32.SetCursorPos(int(x), int(y))


def _click(flag_down, flag_up, x, y, delay=0.012):
    move(x, y)
    user32.mouse_event(flag_down, 0, 0, 0, None)
    time.sleep(0.003)
    user32.mouse_event(flag_up, 0, 0, 0, None)
    time.sleep(delay)


def left(x, y, delay=0.012):
    _click(MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, x, y, delay)


def right(x, y, delay=0.012):
    _click(MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, x, y, delay)


def chord(x, y, delay=0.02):
    """both buttons pressed: middle-click style chord"""
    move(x, y)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, None)
    time.sleep(0.006)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
    user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, None)
    time.sleep(delay)
