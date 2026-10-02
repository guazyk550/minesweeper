"""扫雷自动玩 —— 双击 `扫雷自动玩.bat` 即可运行。

自动识别桌面上正在运行的扫雷窗口（经典 saolei.exe 或本项目的 Java 版
Minesweeper.exe），用「截图识别棋盘 + 虚拟鼠标点击」实时游玩，
日志同时打印到控制台和 run.log。

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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LINE = '=' * 64
THIN = '-' * 64


def app_dir():
    """打包成 exe 后返回 exe 所在目录，直接跑脚本时返回脚本目录。

    日志、截图这类产物都写到这个目录，免得打出来的 exe 把文件丢到临时解包目录里。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return HERE


# bot/solver 等模块按这个环境变量决定日志写哪儿
os.environ.setdefault('SAOLEI_LOG', os.path.join(app_dir(), 'run.log'))


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


def pause_if_frozen():
    """双击 exe 时结束后停一下，别让窗口一闪而过。"""
    if not getattr(sys, 'frozen', False):
        return
    try:
        input('\n按回车键退出 . . .')
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    ap = argparse.ArgumentParser(description='扫雷自动玩')
    ap.add_argument('--games', type=int, default=1, help='玩几局（默认 1）')
    ap.add_argument('--new', action='store_true', help='先点笑脸重开一局')
    ap.add_argument('--list', action='store_true', help='只列出识别到的扫雷窗口')
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

    # 先看一眼目标窗口现在长什么样
    try:
        img, origin = B.grab(stable=True)
        lay = L.detect(img)
        bd = B.read(img, lay)
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
            lay = L.detect(img)
            bd = B.read(img, lay)
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
    print(f'开始自动游玩，共 {args.games} 局。想中止直接关掉本窗口即可。')
    print(THIN)
    print()

    results = []
    for g in range(1, args.games + 1):
        if g > 1:
            print()
            print(f'>> 准备第 {g} 局：点笑脸重开…')
            try:
                img, origin = B.grab(stable=True)
                click_face(img, origin)
                time.sleep(1.6)
            except Exception as e:               # noqa: BLE001
                print('[!] 重开失败：', e)
                break
        res, clicks, rd, chords = bot.play_one(g, resume=True,
                                               verbose_board=args.verbose_board)
        results.append((g, res, clicks, rd, chords))

        print()
        if res == 'win':
            print(f'>>> 第 {g} 局：通关！')
        elif res == 'lose':
            print(f'>>> 第 {g} 局：踩雷了（差一点）')
        else:
            print(f'>>> 第 {g} 局：{res}')
        print(f'    轮次 {rd}，左键点击 {clicks} 次，chord {chords} 次')

    print()
    print(LINE)
    if results:
        wins_n = sum(1 for _, r, _, _, _ in results if r == 'win')
        print(f'   全部结束：{wins_n} 胜 / {len(results)} 局')
        print(f'   日志文件：{os.environ.get("SAOLEI_LOG")}')
    else:
        print('   没有完成任何一局。')
    print(LINE)
    print()
    return 0


if __name__ == '__main__':
    setup_console()
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:                            # noqa: BLE001
        pass
    try:
        code = main()
    except KeyboardInterrupt:
        code = 130
    pause_if_frozen()
    sys.exit(code)
