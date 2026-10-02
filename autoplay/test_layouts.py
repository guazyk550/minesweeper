"""验证：各种自定义尺寸都能被自动识别（窗口移动/尺寸变化后重建布局）。"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
import board as B, game, windows as W, win

CASES = [(9, 9, 10), (16, 16, 40), (30, 16, 99),
         (12, 20, 35), (30, 24, 150), (9, 24, 20), (25, 9, 45)]


def main():
    W.close_dialogs()
    for (w, h, m) in CASES:
        try:
            game.set_custom(w, h, m)
        except Exception as e:
            print(f'设置失败 宽{w} 高{h} 雷{m}: {e!r}')
            continue
        time.sleep(0.4)
        bd, img, origin = B.read_auto()
        r = win.window_rect(W.find_main())
        exp_rows = min(h, 24)          # 程序高度上限 24
        ok = (bd.cols == w) and (bd.rows == exp_rows) and (bd.total_mines() == m)
        flag = 'OK' if ok else '<<< 不符'
        print(f'自定义 宽{w} 高{h} 雷{m}: 窗口{r[2]-r[0]}x{r[3]-r[1]} '
              f'识别={bd.cols}x{bd.rows} 总雷={bd.total_mines()} '
              f'原点=({bd.layout.gx},{bd.layout.gy}) 截图尺寸={img.size} {flag}')


main()
