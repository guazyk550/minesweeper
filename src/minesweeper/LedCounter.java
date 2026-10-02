package minesweeper;

import javax.swing.*;
import java.awt.*;

/** 七段数码管计数器（剩余雷数 / 秒表），仿经典扫雷的红色 LED；支持整体缩放。 */
public class LedCounter extends JComponent {

    /** 0-9 各数字点亮的段。 */
    private static final String[] SEGS = {
            "abcdef", "bc", "abdeg", "abcdg", "bcfg", "acdfg", "acdefg", "abc", "abcdefg", "abcdfg"
    };

    private static final int DW = 13;      // 基准：每位宽
    private static final int DH = 23;      // 基准：每位高
    private static final int PAD = 3;
    private static final int THICK = 3;

    private double scale = 1.0;
    private int value;

    public LedCounter() {
        applySize();
    }

    public void setScale(double s) {
        if (s <= 0.1) return;
        scale = s;
        applySize();
    }

    private int dw() {
        return (int) Math.round(DW * scale);
    }

    private int dh() {
        return (int) Math.round(DH * scale);
    }

    private int pad() {
        return Math.max(1, (int) Math.round(PAD * scale));
    }

    private int thick() {
        return Math.max(2, (int) Math.round(THICK * scale));
    }

    private void applySize() {
        Dimension d = new Dimension(dw() * 3 + pad() * 2, dh() + pad() * 2);
        setPreferredSize(d);
        setMinimumSize(d);
        setMaximumSize(d);
        revalidate();
        repaint();
    }

    public void setValue(int v) {
        v = Math.max(-99, Math.min(999, v));
        if (v != value) {
            value = v;
            repaint();
        }
    }

    public int getValue() {
        return value;
    }

    @Override
    protected void paintComponent(Graphics g0) {
        Graphics2D g = (Graphics2D) g0.create();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_OFF);
        int w = getWidth(), h = getHeight();
        g.setColor(UiTheme.LED_PANEL);
        g.fillRect(0, 0, w, h);
        UiTheme.sunkenBorder(g, 0, 0, w, h);

        int W = dw(), H = dh();
        int oy = (h - H) / 2;
        int ox = (w - W * 3) / 2;
        if (value < 0) {
            drawSegments(g, ox, oy, "g");       // 负号
            int v = Math.min(99, -value);
            drawDigit(g, ox + W, oy, v / 10);
            drawDigit(g, ox + W * 2, oy, v % 10);
        } else {
            int v = Math.min(999, value);
            drawDigit(g, ox, oy, v / 100);
            drawDigit(g, ox + W, oy, (v / 10) % 10);
            drawDigit(g, ox + W * 2, oy, v % 10);
        }
        g.dispose();
    }

    private void drawDigit(Graphics2D g, int x, int y, int digit) {
        drawSegments(g, x, y, SEGS[Math.max(0, Math.min(9, digit))]);
    }

    private void drawSegments(Graphics2D g, int x, int y, String segs) {
        g.setColor(UiTheme.LED_ON);
        int W = dw(), H = dh(), T = thick();
        for (char c : segs.toCharArray()) {
            switch (c) {
                case 'a' -> g.fillRect(x + T - 1, y, W - (T - 1) * 2, T);
                case 'd' -> g.fillRect(x + T - 1, y + H - T, W - (T - 1) * 2, T);
                case 'g' -> g.fillRect(x + T - 1, y + H / 2 - T / 2, W - (T - 1) * 2, T);
                case 'f' -> g.fillRect(x, y + T - 1, T, H / 2 - T + 1);
                case 'b' -> g.fillRect(x + W - T, y + T - 1, T, H / 2 - T + 1);
                case 'e' -> g.fillRect(x, y + H / 2, T, H / 2 - T + 1);
                case 'c' -> g.fillRect(x + W - T, y + H / 2, T, H / 2 - T + 1);
                default -> {
                }
            }
        }
    }
}
