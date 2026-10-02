"""把游戏推进到中局（残局），供 resume 测试用。

用法: python make_midgame.py [难度] [推进轮数]
"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
import board as B, layout as L, solver as S, game, windows as W, bot


def main(mode='expert', rounds=6):
    W.close_dialogs()
    if isinstance(mode, str) and mode in ('beginner', 'inter', 'expert'):
        game.send_menu({'beginner': game.MENU_BEGINNER, 'inter': game.MENU_INTER,
                        'expert': game.MENU_EXPERT}[mode])
    time.sleep(0.4)
    sess = bot.Session()
    bd = bot.new_game(sess)
    print('新局:', bot.describe(bd))
    for i in range(rounds):
        bd = sess.refresh()
        if bd.is_boom() or bd.counts['hidden'] + bd.counts['question'] == 0:
            print('局面已结束，停止推进')
            break
        st = S.State(bd)
        safe, mines, probs = S.solve(st)
        acted = 0
        for c, r in sorted(mines):
            sess.click(c, r, 'right')
            acted += 1
        if not safe and not mines and probs:
            g = min(probs.items(), key=lambda kv: kv[1])[0]
            safe = [g]
        for c, r in sorted(safe)[:6]:
            sess.click(c, r, 'left')
            acted += 1
        if acted == 0:
            break
        time.sleep(0.15)
    bd = sess.refresh()
    print('残局状态:', bot.describe(bd))
    print(bd.render())
    print('现在可以运行: python bot.py 1 --resume')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'expert'
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    main(mode, n)
