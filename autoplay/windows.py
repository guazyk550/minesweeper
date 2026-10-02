"""窗口管理：按进程找出扫雷主窗口与所有对话框（不依赖窗口位置/标题的偶然状态）。"""
import ctypes, sys, time
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsIconic.argtypes = [wintypes.HWND]

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WM_CLOSE = 0x0010
SW_RESTORE = 9
SW_SHOW = 5


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]


def window_rect(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def text_of(h):
    n = user32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, b, n + 1)
    return b.value


def class_of(h):
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, b, 256)
    return b.value


def pid_of(h):
    p = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(p))
    return p.value


def exe_of(pid):
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return None
    finally:
        kernel32.CloseHandle(h)


def enum_top_windows():
    out = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(h, l):
        out.append(h)
        return True
    user32.EnumWindows(CB(cb), 0)
    return out


def saolei_pids():
    pids = set()
    for h in enum_top_windows():
        p = pid_of(h)
        exe = exe_of(p)
        if exe and exe.lower().endswith('saolei.exe'):
            pids.add(p)
    return pids


def list_windows(exe_suffix='saolei.exe', title_contains=None):
    """列出某个进程的顶层窗口。

    exe_suffix=None 表示不限进程；title_contains 可按标题关键字再过滤。
    """
    rows = []
    for h in enum_top_windows():
        p = pid_of(h)
        exe = exe_of(p)
        if exe_suffix is not None:
            if not exe or not exe.lower().endswith(exe_suffix.lower()):
                continue
        t = text_of(h)
        if title_contains is not None and title_contains not in t:
            continue
        rows.append({
            'hwnd': h, 'title': t, 'cls': class_of(h),
            'pid': p, 'rect': window_rect(h),
            'visible': bool(user32.IsWindowVisible(h)),
            'iconic': bool(user32.IsIconic(h)),
        })
    return rows


def find_main(exe_suffix='saolei.exe', title_contains=None, strict=False):
    """主窗口：目标进程里可见的顶层窗口（排除 #32770 对话框）。

    strict=True 时要求标题确实像扫雷 —— java.exe / javaw.exe 上可能挂着
    一堆别的 Java 程序，不能随便挑第一个。
    """
    cands = [w for w in list_windows(exe_suffix, title_contains)
             if w['visible'] and w['cls'] != '#32770']
    if not cands:
        return 0
    for w in cands:
        t = w['title'].lower()
        if '扫雷' in w['title'] or 'mine' in t or 'sweep' in t:
            return w['hwnd']
    return 0 if strict else cands[0]['hwnd']


def find_any(patterns=None):
    """依次尝试若干进程名，返回第一个找到的扫雷主窗口。

    默认覆盖三种启动方式：
      · 经典版            -> saolei.exe
      · 本项目安装/绿色版 -> Minesweeper.exe
      · 本项目 jar 方式   -> java.exe / javaw.exe（要求标题像扫雷）
    """
    if patterns is None:
        patterns = ('saolei.exe', 'Minesweeper.exe', 'javaw.exe', 'java.exe')
    for exe in patterns:
        strict = exe.lower() in ('java.exe', 'javaw.exe')
        h = find_main(exe, strict=strict)
        if h:
            return h
    return 0


def dialogs(exe_suffix='saolei.exe'):
    return [w for w in list_windows(exe_suffix) if w['visible'] and w['cls'] == '#32770']


def close_dialogs(exe_suffix='saolei.exe'):
    """关闭目标进程的所有对话框窗口。返回关闭数量。"""
    n = 0
    for d in dialogs(exe_suffix):
        user32.PostMessageW(d['hwnd'], WM_CLOSE, 0, 0)
        n += 1
    if n:
        time.sleep(0.5)
    return n


user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.GetForegroundWindow.restype = wintypes.HWND

# 缓存主窗口句柄 —— 每次操作都重新枚举所有顶层窗口并查询进程路径非常贵
_front_hwnd = 0


def ensure_on_screen(h):
    """窗口被拖到屏幕外或部分超出时，拉回可见区域（否则抓图会缺内容）。"""
    l, t, r, b = window_rect(h)
    sw = user32.GetSystemMetrics(0)     # SM_CXSCREEN
    sh = user32.GetSystemMetrics(1)     # SM_CYSCREEN
    w, hh = r - l, b - t
    if l < 0 or t < 0 or r > sw or b > sh:
        nx = min(max(0, l), max(0, sw - w))
        ny = min(max(0, t), max(0, sh - hh))
        user32.MoveWindow(h, nx, ny, w, hh, True)
        time.sleep(0.2)
        return True
    return False


def ensure_front(hwnd=None):
    """确保窗口可见、在屏幕内且在前台。

    句柄会缓存：只有句柄失效时才重新枚举窗口。已经是前台就跳过 SetForegroundWindow。
    """
    global _front_hwnd
    h = hwnd or _front_hwnd
    if not h or not user32.IsWindow(h):
        h = find_any()
        _front_hwnd = h
    if not h:
        return 0
    if user32.IsIconic(h):
        user32.ShowWindow(h, SW_RESTORE)
        time.sleep(0.3)
    ensure_on_screen(h)
    if user32.GetForegroundWindow() != h:
        user32.SetForegroundWindow(h)
        time.sleep(0.03)
    return h


def forget_front():
    """目标窗口关了/换了时清掉缓存。"""
    global _front_hwnd
    _front_hwnd = 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('saolei pids:', saolei_pids())
    for w in list_windows():
        print(w)
    print('主窗口:', find_main())
    print('对话框:', dialogs())
