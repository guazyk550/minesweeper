"""扫雷自动玩 —— 双击 `扫雷自动玩.bat` 或独立 exe 即可运行。

自动识别桌面上正在运行的扫雷窗口（经典 saolei.exe、本项目 Java 版
Minesweeper.exe，或 java -jar 启动的），用「截图识别棋盘 + 虚拟鼠标点击」
实时游玩。所有输出都打在控制台上，**不会往程序目录写任何文件**。

用法示例：
    python autoplay.py                 # 接手当前局面，玩 1 局
    python autoplay.py --games 3       # 连玩 3 局（每局之间点笑脸重开）
    python autoplay.py --new           # 先点笑脸开一局新的
    python autoplay.py --list          # 只列出识别到的扫雷窗口
"""
import argparse
import os
import sys
import time

sys.dont_write_bytecode = True      # 别在程序目录里留 __pycache__

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LINE = '=' * 64
THIN = '-' * 64


def banner():
    print(LINE)
    print('   扫雷自动玩  ·  截图识别棋盘 + 虚拟鼠标实时游玩')
    print(LINE)
    print()


def check_deps():
    """返回缺失的依赖名列表。"""
    missing = []
    for mod, pkg in (('numpy', 'numpy'), ('PIL', 'Pillow')):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def find_windows():
    """列出可能的扫雷窗口：[(exe, 窗口信息), ...]。

    覆盖三种启动方式：经典 saolei.exe、本项目 Minesweeper.exe、
    以及用 java -jar 直接跑时的 java.exe / javaw.exe。
    """
    import windows as W
    found = []
    for exe in ('saolei.exe', 'Minesweeper.exe', 'javaw.exe', 'java.exe'):
        for w in W.list_windows(exe):
            if not w['visible'] or w['cls'] == '#32770' or not w['title'].strip():
                continue
            t = w['title'].lower()
            if '扫雷' in w['title'] or 'mine' in t or 'sweep' in t:
                found.append((exe, w))
    return found


def click_face(img, origin):
    """点笑脸重开：笑脸在窗口水平居中、数码管面板的纵向中心。"""
    import numpy as np
    import layout as L
    import mouse
    a = np.asarray(img.convert('RGB')).astype(np.int32)
    panels = L.find_panels(a)
    y = (panels[0][2] + panels[0][3]) // 2 if panels else 78
    x = img.size[0] // 2
    mouse.left(origin[0] + x, origin[1] + y, delay=0.7)


def describe(bd):
    return (f'{bd.cols} 列 x {bd.rows} 行，格子 {bd.layout.cell}px，'
            f'总雷数 {bd.total_mines()}')


def setup_console():
    """打包成 exe 双击运行时：把控制台切到 UTF-8，中文才不会乱码。"""
    if not getattr(sys, 'frozen', False):
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:                            # noqa: BLE001
        pass


# ---------------------------------------------------------------- 窗口大小记忆

def _cfg_path():
    """配置放在 %APPDATA% 下，不污染程序所在目录（比如桌面）。"""
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'MinesweeperAutoPlay', 'console.json')


def _console_hwnd():
    try:
        import ctypes
        return ctypes.windll.kernel32.GetConsoleWindow()
    except Exception:                            # noqa: BLE001
        return 0


def _console_size():
    """当前控制台窗口的 (左, 上, 宽, 高)，拿不到返回 None。"""
    try:
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

        h = _console_hwnd()
        if not h:
            return None
        r = RECT()
        if not ctypes.windll.user32.GetWindowRect(h, ctypes.byref(r)):
            return None
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    except Exception:                            # noqa: BLE001
        return None


def restore_console_size():
    """把控制台窗口恢复成上次退出时的大小。"""
    try:
        import json
        p = _cfg_path()
        if not os.path.exists(p):
            return
        with open(p, encoding='utf-8') as f:
            cfg = json.load(f)
        w, h = int(cfg.get('w', 0)), int(cfg.get('h', 0))
        if w < 240 or h < 140:
            return
        cur = _console_size()
        if not cur:
            return
        import ctypes
        hwnd = _console_hwnd()
        SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
        ctypes.windll.user32.SetWindowPos(hwnd, 0, cur[0], cur[1], w, h,
                                          SWP_NOZORDER | SWP_NOACTIVATE)
    except Exception:                            # noqa: BLE001
        pass


def save_console_size():
    """记住当前控制台窗口大小，下次启动照这个开。"""
    try:
        import json
        r = _console_size()
        if not r or r[2] < 240 or r[3] < 140:
            return
        p = _cfg_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({'w': r[2], 'h': r[3]}, f)
    except Exception:                            # noqa: BLE001
        pass


def pause_if_frozen():
    """双击 exe 时结束后停一下，别让窗口一闪而过。"""
    if not getattr(sys, 'frozen', False):
        return
    try:
        input('\n按回车键退出 . . .')
    except (EOFError, KeyboardInterrupt):
        pass


def ask_next(played, wins):
    """一局结束后问用户接下来做什么。

    返回 'next'（直接开下一局）/ 'rescan'（重新识别当前局面）/ 'quit'。
    """
    print()
    print(LINE)
    print(f'   已经玩了 {played} 局，{wins} 胜。接下来？')
    print(THIN)
    print('     [回车 / n]  直接开始下一局（自动点笑脸重开）')
    print('     [c]         重新识别当前局面，接着玩这一把')
    print('     [q]         退出')
    print(LINE)
    while True:
        try:
            ans = input('  请选择 > ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            return 'quit'
        if ans in ('', 'n', 'next', 'y', 'yes'):
            return 'next'
        if ans in ('c', 'continue', 'r', 'rescan'):
            return 'rescan'
        if ans in ('q', 'quit', 'exit', 'e'):
            return 'quit'
        print('  没看懂，请输入 n（下一局）/ c（重新识别）/ q（退出）')


def wait_board_ready(bd_reader, tries=20):
    """等棋盘进入可玩状态（有已翻开的格子）。"""
    for _ in range(tries):
        time.sleep(0.6)
        try:
            bd = bd_reader()
        except Exception:                        # noqa: BLE001
            continue
        if bd.counts['open'] > 0:
            return bd
    return None


def main():
    ap = argparse.ArgumentParser(description='扫雷自动玩')
    ap.add_argument('--games', type=int, default=0,
                    help='最多玩几局；0（默认）= 一直玩到你自己选退出')
    ap.add_argument('--new', action='store_true', help='先点笑脸重开一局')
    ap.add_argument('--list', action='store_true', help='只列出识别到的扫雷窗口')
    ap.add_argument('--interactive', action='store_true',
                    help='强制开启「每局结束问一次」的交互（输入被重定向时也用）')
    ap.add_argument('--speed', type=int, default=0, help='每次操作后的额外等待（毫秒）')
    ap.add_argument('--verbose-board', action='store_true',
                    help='把每轮棋盘快照也打进日志（默认只记关键动作）')
    args = ap.parse_args()

    banner()

    missing = check_deps()
    if missing:
        print('[!] 缺少 Python 依赖：' + '、'.join(missing))
        print('    请先安装：pip install ' + ' '.join(missing))
        return 2

    wins = find_windows()
    if not wins:
        print('[!] 没有找到正在运行的扫雷窗口。')
        print()
        print('    请先打开扫雷程序，二选一：')
        print('      · 经典版：C:\\Users\\Administrator\\Desktop\\saolei.exe')
        print('      · Java 版：双击 minesweeper\\run.bat（或 Minesweeper.exe）')
        print()
        print('    打开后再运行本脚本即可。')
        return 1

    print('找到以下扫雷窗口：')
    for i, (exe, w) in enumerate(wins):
        print(f'  [{i + 1}] {w["title"]}   （{exe}，位置 {w["rect"][0]},{w["rect"][1]}）')
    print()

    if args.list:
        return 0

    import board as B
    import layout as L
    import bot

    if args.speed > 0:
        os.environ['SAOLEI_EXTRA_DELAY_MS'] = str(args.speed)

    # 先看一眼目标窗口现在长什么样（用多候选 + 自洽性打分，残局才不会认错）
    try:
        img, origin = B.grab(stable=True)
        lay, bd = B.read_best(img)
    except Exception as e:                       # noqa: BLE001
        print('[!] 读取棋盘失败：', e)
        print('    请确认扫雷窗口没有被最小化、也没有被别的窗口挡住。')
        return 3

    # 上一局已经结束（踩雷/通关）时，棋盘上已经没有网格特征，
    # 这时候识别出来的尺寸不可信 —— 直接重开一局再认。
    finished = bd.is_boom() or (bd.counts['hidden'] + bd.counts['question'] == 0)
    if args.new or finished:
        why = '按要求' if args.new else '上一局已经结束了'
        print(f'>> {why}，点笑脸重开一局…')
        click_face(img, origin)
        time.sleep(1.6)
        try:
            img, origin = B.grab(stable=True)
            lay, bd = B.read_best(img)
        except Exception as e:                   # noqa: BLE001
            print('[!] 重开后读取失败：', e)
            return 3

    print('窗口尺寸   :', f'{img.size[0]} x {img.size[1]}')
    print('识别结果   :', describe(bd))
    print('当前局面   :', f'已翻开 {bd.counts["open"]}，已插旗 {bd.counts["flag"]}，'
                         f'未翻开 {bd.counts["hidden"]}')
    if bd.counts['open'] == 0:
        print('            （全新棋盘，稍后由脚本点第一下开局，首点安全）')
    print()

    print(THIN)
    if args.games:
        print(f'开始自动游玩，最多 {args.games} 局。想中止直接关掉本窗口即可。')
    else:
        print('开始自动游玩。每局结束后会问你要不要继续；想中止直接关掉本窗口。')
    print(THIN)
    print()

    interactive = args.interactive or sys.stdin.isatty()
    played = 0
    wins = 0
    while True:
        played += 1
        res, clicks, rd, chords = bot.play_one(played, resume=True,
                                               verbose_board=args.verbose_board)
        if res == 'win':
            wins += 1

        print()
        if res == 'win':
            print(f'>>> 第 {played} 局：通关！')
        elif res == 'lose':
            print(f'>>> 第 {played} 局：踩雷了（差一点）')
        else:
            print(f'>>> 第 {played} 局：{res}')
        print(f'    轮次 {rd}，左键点击 {clicks} 次，chord {chords} 次')

        if args.games and played >= args.games:
            print(f'\n  已经达到设定的 {args.games} 局，收工。')
            break

        if not interactive:
            # 输入被重定向（脚本/自动化）：没人可以问，就自己往下走
            if not args.games:
                break                     # 没设上限又无人可问 → 跑一局收工
            print(f'\n>> 自动开始第 {played + 1} 局…')
            try:
                img, origin = B.grab(stable=True)
                click_face(img, origin)
                time.sleep(1.6)
            except Exception as e:               # noqa: BLE001
                print('[!] 重开失败：', e)
                break
            continue

        choice = ask_next(played, wins)
        if choice == 'quit':
            break

        if choice == 'next':
            print()
            print(f'>> 准备第 {played + 1} 局：点笑脸重开…')
            try:
                img, origin = B.grab(stable=True)
                click_face(img, origin)
                time.sleep(1.6)
            except Exception as e:               # noqa: BLE001
                print('[!] 重开失败：', e)
                break
        else:                                    # rescan：就地重新识别当前局面
            print()
            print('>> 重新识别当前局面…')
            try:
                img, origin = B.grab(stable=True)
                lay, bd = B.read_best(img)
            except Exception as e:               # noqa: BLE001
                print('[!] 识别失败：', e)
                break
            if bd.is_boom() or (bd.counts['hidden'] + bd.counts['question'] == 0):
                print('   这一把已经结束了，帮你点笑脸重开。')
                click_face(img, origin)
                time.sleep(1.6)
            else:
                print(f'   好，接着玩 —— 已翻开 {bd.counts["open"]} 格，'
                      f'已插旗 {bd.counts["flag"]}，未翻开 {bd.counts["hidden"]}')

    print()
    print(LINE)
    if played:
        print(f'   本次一共玩了 {played} 局，{wins} 胜')
    else:
        print('   没有完成任何一局。')
    print(LINE)
    print()
    return 0


if __name__ == '__main__':
    setup_console()
    restore_console_size()          # 上次调过多大，这次就开多大
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:                            # noqa: BLE001
        pass
    try:
        code = main()
    except KeyboardInterrupt:
        code = 130
    finally:
        save_console_size()         # 记住这次调过的大小
    pause_if_frozen()
    sys.exit(code)
