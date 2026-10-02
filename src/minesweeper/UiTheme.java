package minesweeper;

import java.awt.*;

/** 经典扫雷的视觉主题：颜色、3D 边框、旗子、地雷、笑脸。 */
public final class UiTheme {

    private UiTheme() {
    }

    public static final int CELL = 16;

    public static final Color BG = new Color(192, 192, 192);
    public static final Color DARK = new Color(128, 128, 128);
    public static final Color LIGHT = new Color(255, 255, 255);
    public static final Color LED_PANEL = new Color(0, 0, 0);
    public static final Color LED_ON = new Color(255, 0, 0);
    public static final Color LED_OFF = new Color(72, 0, 0);
    public static final Color FACE_YELLOW = new Color(255, 220, 0);

    /** 1..8 的数字颜色（与经典扫雷一致）。 */
    public static final Color[] NUM_COLORS = {
            null,
            new Color(0, 0, 255),      // 1
            new Color(0, 128, 0),      // 2
            new Color(255, 0, 0),      // 3
            new Color(0, 0, 128),      // 4
            new Color(128, 0, 0),      // 5
            new Color(0, 128, 128),    // 6
            new Color(0, 0, 0),        // 7
            new Color(128, 128, 128),  // 8
    };

    /** 凸起（未翻开的格子）：左上 2px 高光 + 右下 2px 阴影，和经典一致。 */
    public static void raised(Graphics2D g, int x, int y, int w, int h) {
        g.setColor(BG);
        g.fillRect(x, y, w, h);
        g.setColor(LIGHT);
        g.fillRect(x, y, w, 2);
        g.fillRect(x, y, 2, h);
        g.setColor(DARK);
        g.fillRect(x, y + h - 2, w, 2);
        g.fillRect(x + w - 2, y, 2, h);
    }

    /**
     * 已翻开的格子：192 灰 + <b>右边和下边各 1px 深灰网格线</b>。
     *
     * <p>这条细线就是经典扫雷里"格子间隔"的来源 —— 没有它，整片已翻开区域会糊成一整块灰。
     * 经典版的实测结构正是「15px 灰 + 1px 深灰」，与未翻开格的 2px 阴影自然衔接。
     */
    public static void openedCell(Graphics2D g, int x, int y, int s) {
        g.setColor(BG);
        g.fillRect(x, y, s, s);
        g.setColor(DARK);
        g.fillRect(x + s - 1, y, 1, s);
        g.fillRect(x, y + s - 1, s, 1);
    }

    /** 凹陷（已翻开或用旧的面板）。 */
    public static void lowered(Graphics2D g, int x, int y, int w, int h) {
        g.setColor(BG);
        g.fillRect(x, y, w, h);
        g.setColor(DARK);
        g.fillRect(x, y, w, 2);
        g.fillRect(x, y, 2, h);
        g.setColor(LIGHT);
        g.fillRect(x, y + h - 2, w, 2);
        g.fillRect(x + w - 2, y, 2, h);
    }

    /** 细边框的凹陷（棋盘外框）。 */
    public static void sunkenBorder(Graphics2D g, int x, int y, int w, int h) {
        g.setColor(DARK);
        g.drawLine(x, y, x + w - 1, y);
        g.drawLine(x, y, x, y + h - 1);
        g.setColor(LIGHT);
        g.drawLine(x, y + h - 1, x + w - 1, y + h - 1);
        g.drawLine(x + w - 1, y, x + w - 1, y + h - 1);
    }

    /** 画旗子。 */
    public static void flag(Graphics2D g, int x, int y, int size) {
        int w = size;
        // 杆
        g.setColor(Color.BLACK);
        int poleX = x + w / 2;
        g.fillRect(poleX, y + 3, 2, w - 6);
        // 底座
        g.fillRect(poleX - 3, y + w - 5, 8, 2);
        // 旗面
        g.setColor(Color.RED);
        Polygon p = new Polygon();
        p.addPoint(poleX - 6, y + 3);
        p.addPoint(poleX, y + 3);
        p.addPoint(poleX, y + w / 2);
        p.addPoint(poleX - 6, y + w / 2);
        g.fillPolygon(p);
    }

    /** 画地雷。 */
    public static void mine(Graphics2D g, int x, int y, int size) {
        int s = size;
        g.setColor(Color.BLACK);
        int c = x + s / 2, r = y + s / 2;
        int rad = Math.max(3, s / 2 - 3);
        g.fillOval(c - rad, r - rad, rad * 2, rad * 2);
        g.fillRect(c - 1, r - rad - 3, 2, 3);
        g.fillRect(c - 1, r + rad, 2, 3);
        g.fillRect(c - rad - 3, r - 1, 3, 2);
        g.fillRect(c + rad, r - 1, 3, 2);
        g.setColor(Color.WHITE);
        g.fillRect(c - rad + 2, r - rad + 2, 2, 2);
    }

    /** 画错标记（旗插错时打叉）。 */
    public static void wrongFlag(Graphics2D g, int x, int y, int size) {
        mine(g, x, y, size);
        g.setColor(Color.RED);
        g.setStroke(new BasicStroke(2f));
        g.drawLine(x + 3, y + 3, x + size - 4, y + size - 4);
        g.drawLine(x + size - 4, y + 3, x + 3, y + size - 4);
    }

    public enum Face {SMILE, SURPRISED, DEAD, WIN}

    /** 画笑脸按钮（和经典一样：普通 / 张开嘴 / X 眼 / 戴墨镜）。 */
    public static void face(Graphics2D g, int x, int y, int size, Face kind) {
        g.setColor(FACE_YELLOW);
        g.fillOval(x + 1, y + 1, size - 2, size - 2);
        g.setColor(Color.BLACK);
        g.drawOval(x + 1, y + 1, size - 2, size - 2);
        int cx = x + size / 2, cy = y + size / 2;
        switch (kind) {
            case SMILE -> {
                g.fillOval(cx - 4, cy - 4, 2, 3);
                g.fillOval(cx + 3, cy - 4, 2, 3);
                g.drawArc(cx - 6, cy - 2, 12, 8, 200, 140);
            }
            case SURPRISED -> {
                g.fillOval(cx - 4, cy - 4, 2, 3);
                g.fillOval(cx + 3, cy - 4, 2, 3);
                g.drawOval(cx - 3, cy + 1, 6, 6);
            }
            case DEAD -> {
                g.setStroke(new BasicStroke(1.6f));
                g.drawLine(cx - 5, cy - 5, cx - 1, cy - 1);
                g.drawLine(cx - 1, cy - 5, cx - 5, cy - 1);
                g.drawLine(cx + 1, cy - 5, cx + 5, cy - 1);
                g.drawLine(cx + 5, cy - 5, cx + 1, cy - 1);
                g.drawArc(cx - 6, cy + 2, 12, 6, 20, 140);
            }
            case WIN -> {
                g.setStroke(new BasicStroke(2f));
                g.fillRect(cx - 7, cy - 5, 6, 3);
                g.fillRect(cx + 1, cy - 5, 6, 3);
                g.fillRect(cx - 2, cy - 5, 4, 2);
                g.setStroke(new BasicStroke(1.4f));
                g.drawArc(cx - 6, cy - 2, 12, 8, 200, 140);
            }
        }
    }
}
