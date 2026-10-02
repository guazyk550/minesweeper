"""受控实验：确认这个扫雷程序里“翻开相邻安全格”的正确操作方式。

依次尝试：左键单击已翻开数字格 / 左右键同按(chord) / 左键双击，
看哪一种真的会翻开相邻格，以及是否会踩雷。
"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
import board as B, layout as L, solver as S, game, windows as W, mouse


def read():
    img, origin = B.grab()
    lay = L.detect(img)
    return B.read(img, lay), lay, origin


def click(lay, origin, c, r, btn):
    x, y = lay.center_in_window(c, r)
    x += origin[0]
    y += origin[1]
    if btn == 'left':
        mouse.left(x, y)
    elif btn == 'right':
        mouse.right(x, y)
    elif btn == 'chord':
        mouse.chord(x, y)
    elif btn == 'dbl':
        mouse.left(x, y)
        time.sleep(0.04)
        mouse.left(x, y)


def main():
    W.close_dialogs()
    game.send_menu(game.MENU_BEGINNER)
    time.sleep(0.5)
    bd, lay, origin = read()
    print('开局', bd.layout)
    click(lay, origin, bd.cols // 2, bd.rows // 2, 'left')
    time.sleep(0.35)
    for step in range(40):
        bd, lay, origin = read()
        if bd.is_boom():
            print('!! 已踩雷'); return
        st = S.State(bd)
        safe, mines, probs = S.solve(st)
        if not safe and not mines and probs:
            safe = [min(probs.items(), key=lambda kv: kv[1])[0]]
        for c, r in sorted(mines):
            click(lay, origin, c, r, 'right')
        for c, r in sorted(safe)[:8]:
            click(lay, origin, c, r, 'left')
        st.flags |= set(mines)
        st.unknown -= set(mines)
        ch = S.chordable(st)
        if ch:
            print('棋盘:'); print(bd.render())
            print('可 chord 的格:', ch)
            target = ch[0]
            for act in ('left', 'chord', 'dbl'):
                before = read()[0]
                print(f'--- 测试动作 {act} 于 {target} ---')
                click(lay, origin, target[0], target[1], act)
                time.sleep(0.45)
                after, lay2, or2 = read()
                if after.is_boom():
                    print(f'    动作 {act}: 踩雷！红色占比 {after.boom_score():.2f}')
                    print(after.render())
                    return
                print(f'    动作 {act}: open {before.counts["open"]} -> {after.counts["open"]}')
                if after.counts['open'] > before.counts['open']:
                    print(f'    >>> 动作 {act} 有效（翻开了相邻格）')
                    print(after.render())
                    return
                lay, origin = lay2, or2
            print('三种动作都没能翻开相邻格')
            return
        time.sleep(0.05)
    print('未找到可 chord 的局面')


main()
