package minesweeper;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionListener;

/** 经典黄色笑脸按钮：普通 / 自动玩中(惊讶) / 踩雷(X 眼) / 通关(墨镜)。 */
public class FaceButton extends JButton {

    private UiTheme.Face kind = UiTheme.Face.SMILE;
    private double scale = 1.0;

    public FaceButton(ActionListener l) {
        setBorderPainted(false);
        setContentAreaFilled(false);
        setFocusPainted(false);
        setOpaque(false);
        setToolTipText("重开一局（F2）");
        applySize();
        addActionListener(l);
    }

    /** 跟随整体缩放。 */
    public void setScale(double s) {
        if (s <= 0.1) return;
        scale = s;
        applySize();
    }

    private void applySize() {
        int sz = (int) Math.round(30 * scale);
        Dimension d = new Dimension(sz, sz);
        setPreferredSize(d);
        setMinimumSize(d);
        setMaximumSize(d);
        revalidate();
        repaint();
    }

    public void setKind(UiTheme.Face k) {
        if (k != kind) {
            kind = k;
            repaint();
        }
    }

    public UiTheme.Face kind() {
        return kind;
    }

    @Override
    protected void paintComponent(Graphics g0) {
        Graphics2D g = (Graphics2D) g0.create();
        int w = getWidth(), h = getHeight();
        boolean pressed = getModel().isArmed() || getModel().isPressed();
        if (pressed) UiTheme.lowered(g, 0, 0, w, h);
        else UiTheme.raised(g, 0, 0, w, h);
        int s = Math.min(w, h) - 6;
        UiTheme.face(g, (w - s) / 2, (h - s) / 2, s, kind);
        g.dispose();
    }
}
