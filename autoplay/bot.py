"""扫雷机器人：全自动适配任意盘面（初级/中级/高级/自定义/残局）+ chord 加速。

用法:
    python bot.py <局数> [宽度 高度 雷数]
"""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board as B
import layout as L
import solver as S
import game
import windows as W
import win
import mouse

LOG = os.environ.get('SAOLEI_LOG') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'run.log')


def log(*a):
    msg = ' '.join(str(x) for x in a)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg, flush=True)


class Session:
    """一次连续的游戏会话：缓存布局与窗口句柄，每次操作前重新定位窗口。"""

    def __init__(self, verbose=True):
        self.layout = None
        self.key = None
        self.origin = (0, 0)
        self.verbose = verbose
        self.stat = {'n': 0, 'grab': 0.0, 'read': 0.0, 'solve': 0.0,
                     'click': 0.0, 'sleep': 0.0}

    def refresh(self, force_layout=False):
        t0 = time.time()
        img, origin = B.grab(stable=True)      # 稳定抓取，避免读到重绘中间态
        t1 = time.time()
        self.last_img = img
        self.origin = origin
        if force_layout or self.layout is None or self.key != img.size:
            self.layout = L.detect(img)
            self.key = img.size
        bd = B.read(img, self.layout)
        t2 = time.time()
        st = self.stat
        st['grab'] += t1 - t0
        st['read'] += t2 - t1
        st['n'] += 1
        return bd

    def click(self, c, r, btn='left'):
        x, y = self.layout.center_in_window(c, r)
        x += self.origin[0]
        y += self.origin[1]
        t0 = time.time()
        if btn == 'left':
            mouse.left(x, y)
        elif btn == 'right':
            mouse.right(x, y)
        else:
            mouse.chord(x, y)
        self.stat['click'] += time.time() - t0

    def report(self):
        st = self.stat
        total = st['grab'] + st['read'] + st['solve'] + st['click'] + st['sleep']
        if total <= 0:
            return ''
        return (f'{st["n"]} 轮 | 截图 {st["grab"]:.1f}s | 读盘 {st["read"]:.1f}s | '
                f'求解 {st["solve"]:.1f}s | 点击 {st["click"]:.1f}s | '
                f'等待 {st["sleep"]:.1f}s | 合计 {total:.1f}s')


def describe(bd):
    return (f'{bd.cols}x{bd.rows} 雷={bd.total_mines()} '
            f'open={bd.counts["open"]} hidden={bd.counts["hidden"]} '
            f'flag={bd.counts["flag"]} q={bd.counts["question"]}')


def consistency_errors(bd, st=None):
    """读盘自洽性检查：数字格周围旗数/未知格数必须能容纳该数字。"""
    if st is None:
        st = S.State(bd)
    errs = []
    for (c, r), v in st.open.items():
        if v <= 0:
            continue
        fl = sum(1 for n in st.nb(c, r) if n in st.flags)
        un = sum(1 for n in st.nb(c, r) if n in st.unknown)
        if fl > v:
            errs.append(((c, r), f'旗{fl}>数字{v}'))
        elif fl + un < v:
            errs.append(((c, r), f'旗{fl}+未知{un}<数字{v}'))
    return errs


def nb_count(c, r, cols, rows):
    n = 0
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            if 0 <= c + dc < cols and 0 <= r + dr < rows:
                n += 1
    return n


def boom_cell(bd):
    cells = bd.boom_cells()
    return cells[0] if cells else None


def new_game(sess):
    """开新局并确认棋盘确实重置了（菜单命令偶尔会被吞掉）。"""
    for attempt in range(5):
        W.close_dialogs()
        game.send_menu(game.MENU_NEW)
        time.sleep(0.35)
        bd = sess.refresh(force_layout=True)
        total = bd.cols * bd.rows
        fresh = (not bd.is_boom()) and (bd.counts['hidden'] + bd.counts['question'] == total)
        if fresh:
            return bd
        log(f'[新局重试{attempt + 1}] open={bd.counts["open"]} boom={bd.is_boom()}')
        h = W.find_main()
        l, t, r, b = W.window_rect(h)
        mouse.left((l + r) // 2, t + 68, delay=0.45)      # 点笑脸
        time.sleep(0.3)
        bd = sess.refresh(force_layout=True)
        if (not bd.is_boom()) and bd.counts['hidden'] + bd.counts['question'] == bd.cols * bd.rows:
            return bd
    return bd


def play_one(gidx, max_rounds=3000, verbose_board=True, resume=False):
    """resume=True 表示接手当前残局（不重开新局）。"""
    sess = Session()
    if resume:
        bd = sess.refresh(force_layout=True)
        log(f'=== 局{gidx} 接手残局: {describe(bd)} layout={bd.layout}')
    else:
        bd = new_game(sess)
        log(f'=== 局{gidx} 开始: {describe(bd)} layout={bd.layout}')
    if bd.counts['open'] == 0:
        c, r = bd.cols // 2, bd.rows // 2
        sess.click(c, r, 'left')
        # 有些实现（比如本项目的 Java 版）是「首次点击后才生成雷区」，而且会跑
        # 保证可解验证、耗时数秒。这里必须等它展开，否则会对着空棋盘瞎点。
        for _ in range(24):
            time.sleep(0.6)
            bd = sess.refresh()
            if bd.counts['open'] > 0:
                log(f'[开局] 首次点击后展开 {bd.counts["open"]} 格')
                break
        else:
            log('[开局] 等待首次点击展开超时（棋盘可能仍未生成）')
    clicks = 0
    chords = 0
    audit = {}
    known_mines = set()      # 求解器历次确认过的雷（= 我们插的旗，都是真的）
    if bd.cols * bd.rows > 800:
        verbose_board = False
        log(f'[大棋盘 {bd.cols}x{bd.rows}] 关闭逐轮棋盘日志，只记关键动作')

    def done(res, c=0, r=0, ch=0):
        log('[性能] ' + sess.report())
        return res, c, r, ch

    for rd in range(1, max_rounds + 1):
        if W.dialogs():
            log('[对话框] 关闭并重读')
            W.close_dialogs()
            time.sleep(0.3)
            bd = sess.refresh(force_layout=True)
        else:
            bd = sess.refresh()
        st_chk = S.State(bd)
        errs = consistency_errors(bd, st_chk)
        if errs and not bd.is_boom():
            log(f'[读盘不自洽] {errs[:5]} -> 重读')
            time.sleep(0.25)
            bd = sess.refresh(force_layout=True)
            errs = consistency_errors(bd)
            if errs:
                log(f'[读盘不自洽·重读后仍有] {errs[:5]}')
        if verbose_board:
            log(f'--- 局{gidx} 第{rd}轮 ({describe(bd)}) ---')
            log(bd.render())
        if bd.is_boom():
            bc = boom_cell(bd)
            src = []
            if bc in audit.get('clicked', set()):
                src.append('点到它')
            if bc in audit.get('covered', set()):
                src.append('chord覆盖')
            if bc in audit.get('mines', set()):
                src.append('曾被插旗')
            log(f'[踩雷] 格 {bc} 红色占比 {bd.boom_score():.2f} 归因={src or ["未知"]} '
                f'（点击{clicks} 次，chord {chords} 次）')
            # 回溯审计：爆炸后所有雷都会显形（黑点或旗子），用它检验上一轮的推理
            def looks_mine(g):
                st, v = bd.cells[g[1]][g[0]]
                return st in ('flag', 'question') or (st == 'open' and v == 7)
            if audit.get('mines'):
                wrong = sorted(g for g in audit['mines'] if not looks_mine(g))
                log(f'[审计] 上轮插旗 {len(audit["mines"])} 个，其中不是雷的 {len(wrong)} 个: {wrong[:8]}')
            if audit.get('safe'):
                bad = sorted(g for g in audit['safe'] if looks_mine(g))
                log(f'[审计] 上轮判定安全 {len(audit["safe"])} 个，实际是雷的 {len(bad)} 个: {bad[:8]}')
            return done('lose', clicks, rd, chords)
        if bd.counts['hidden'] + bd.counts['question'] == 0:
            fn = os.path.join(os.path.dirname(LOG), f'win_g{gidx}.png')
            try:
                if getattr(sess, 'last_img', None) is not None:
                    sess.last_img.save(fn)
            except Exception as e:
                log('[截图失败]', e)
            log(f'[胜利] 第{rd}轮完成，点击{clicks} 次，chord {chords} 次，截图 {fn}')
            return done('win', clicks, rd, chords)
        st = S.State(bd)
        _t0 = time.time()
        safe, mines, probs = S.solve(st)
        sess.stat['solve'] += time.time() - _t0
        if not safe and not mines and probs:
            p1 = [g for g, p in probs.items() if p >= 1 - 1e-9]
            p0 = [g for g, p in probs.items() if p <= 1e-9]
            mines, safe = p1, p0
            if not p0 and not p1:
                frontier = st.frontier()
                nonfront = [g for g in st.unknown if g not in frontier]
                if bd.counts['open'] < max(30, int(0.06 * bd.cols * bd.rows)) \
                        and len(nonfront) >= 10 and min(probs.values()) > 0.10:
                    # 局面没展开：前沿格几乎不可能开出空白区，必须向远处外扩。
                    # 优先点角落/边缘——邻居越少，开出成片空白区的概率越高
                    # （角落 3 邻居≈50%，边缘≈31%，内部 8 邻居≈16%），而踩雷概率相同。
                    nonfront.sort(key=lambda g: (nb_count(g[0], g[1], bd.cols, bd.rows),
                                                 random.random()))
                    g = nonfront[0]
                    log(f'[外扩] 点 {g}（邻居{nb_count(g[0], g[1], bd.cols, bd.rows)}个，'
                        f'非前沿 {len(nonfront)}，已翻开 {bd.counts["open"]}）')
                else:
                    gmin = min(probs.values())
                    ties = [k for k, v in probs.items() if abs(v - gmin) < 1e-9]
                    g = random.choice(ties)
                    log(f'[猜测] {g} 概率 {gmin:.3f}（并列 {len(ties)}/{len(probs)}）')
                safe = [g]
        if not safe and not mines:
            cand = sorted(st.unknown)
            if not cand:
                log('[卡住] 没有可操作格子')
                return done('stuck', clicks, rd, chords)
            safe = [random.choice(cand)]
            log(f'[随机] {safe[0]}')
        # 1) 插旗
        if mines:
            log(f'[插旗] {sorted(mines)[:20]}{" ..." if len(mines) > 20 else ""}')
            for c, r in mines:
                sess.click(c, r, 'right')
                clicks += 1
            known_mines |= set(mines)
            st.flags |= set(mines)
            st.unknown -= set(mines)
        # 2) chord：在已翻开的数字格上左右键同按，一次翻开相邻格。
        #    安全条件：该数字格周围旗数已等于它的数字，且这些旗都是求解器确认过的真雷
        #    —— 此时其余邻居必然安全（比"逐个证明每个邻居安全"宽松得多，能多 chord 不少）。
        #    （实测：左键单击已翻开数字格也会展开，但它不看旗子，会踩雷，所以只用双键 chord）
        covered = set()
        ch = []
        for (c, r), v in st.open.items():
            if v <= 0:
                continue
            unk = [n for n in st.nb(c, r) if n in st.unknown]
            if not unk:
                continue
            flags_here = [n for n in st.nb(c, r) if n in st.flags]
            if len(flags_here) == v and all(n in known_mines for n in flags_here):
                ch.append((c, r))
        if ch:
            for (c, r) in ch[:40]:
                sess.click(c, r, 'chord')
                chords += 1
                for n in st.nb(c, r):
                    if n in st.unknown:
                        covered.add(n)
            log(f'[chord] {len(ch)} 个格，覆盖 {len(covered)} 格')
        # 3) 剩余确定安全格逐个点开
        rest = [g for g in sorted(safe) if g not in covered]
        if rest:
            log(f'[翻格] {rest[:20]}{" ..." if len(rest) > 20 else ""}')
            for c, r in rest:
                sess.click(c, r, 'left')
                clicks += 1
        audit = {'clicked': set(rest), 'covered': set(covered), 'mines': set(mines)}
        # 给窗口留出重绘时间；下一轮的「稳定抓取」还会再兜一层底，所以这里可以短一些
        sl = 0.02 + min(0.12, 0.003 * (len(mines) + len(rest) + len(ch)))
        time.sleep(sl)
        sess.stat['sleep'] += sl
    log(f'[超时] 局{gidx} 达到最大轮数')
    return done('timeout', clicks, max_rounds, chords)


def setup(mode=None):
    """mode: None=保持当前 | 'beginner'/'inter'/'expert' | (w,h,mines)"""
    import game as G
    W.close_dialogs()
    if mode is None:
        return
    if isinstance(mode, tuple):
        G.set_custom(*mode)
    else:
        G.send_menu({'beginner': G.MENU_BEGINNER, 'inter': G.MENU_INTER,
                     'expert': G.MENU_EXPERT}[mode])
    time.sleep(0.4)


def main(games=1, mode=None, resume=False):
    open(LOG, 'w', encoding='utf-8').close()
    if not resume:
        setup(mode)
    results = []
    for g in range(1, games + 1):
        res, clicks, rd, chords = play_one(g, resume=(resume and g == 1))
        results.append((g, res, clicks, rd, chords))
        log(f'=== 局{g} 结果: {res}, 点击{clicks}, 轮次{rd}, chord{chords} ===')
    won = sum(1 for _, r, _, _, _ in results if r == 'win')
    log(f'汇总: {results}')
    log(f'胜负: {won}/{len(results)}')
    return results


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    args = sys.argv[1:]
    resume = '--resume' in args
    args = [a for a in args if a != '--resume']
    n = int(args[0]) if args else 1
    mode = None
    if len(args) > 3:
        mode = (int(args[1]), int(args[2]), int(args[3]))
    elif len(args) > 1:
        mode = args[1]
    main(n, mode, resume)
