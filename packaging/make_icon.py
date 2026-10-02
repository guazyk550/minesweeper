"""生成扫雷应用图标（未翻开格子 + 黑地雷），输出多尺寸 .ico。

用法: python make_icon.py
"""
from PIL import Image, ImageDraw

SIZE = 256
BG = (192, 192, 192)
LIGHT = (255, 255, 255)
DARK = (128, 128, 128)
MINE = (0, 0, 0)


def draw_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    edge = max(1, round(s * 0.09))          # 立体边框厚度
    # 格子底色 + 3D 边框（和游戏里的未翻开格一致）
    d.rectangle([0, 0, s - 1, s - 1], fill=BG)
    d.rectangle([0, 0, s - 1, edge - 1], fill=LIGHT)
    d.rectangle([0, 0, edge - 1, s - 1], fill=LIGHT)
    d.rectangle([0, s - edge, s - 1, s - 1], fill=DARK)
    d.rectangle([s - edge, 0, s - 1, s - 1], fill=DARK)

    # 地雷
    cx = cy = s / 2
    r = s * 0.27
    spike_w = max(1, round(s * 0.045))
    # 八根尖刺
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                   (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)):
        L = r * 1.45
        d.line([cx, cy, cx + dx * L, cy + dy * L], fill=MINE, width=spike_w)
    # 本体
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MINE)
    # 高光
    hr = max(1, round(r * 0.28))
    d.ellipse([cx - r * 0.55, cy - r * 0.62,
               cx - r * 0.55 + hr * 2, cy - r * 0.62 + hr * 2], fill=(255, 255, 255))
    return img


def main():
    base = draw_icon(SIZE)
    out = r'D:\gua550\minesweeper\packaging\minesweeper.ico'
    base.save(out, format='ICO',
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print('图标已生成:', out)
    # 顺便导出一张 png 便于预览
    base.save(r'D:\gua550\minesweeper\packaging\minesweeper.png')
    print('预览图: packaging/minesweeper.png')


main()
