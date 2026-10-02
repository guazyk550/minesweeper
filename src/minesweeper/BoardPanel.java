package minesweeper;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/** 棋盘面板：绘制格子并处理左键翻开 / 右键插旗 / 双键 chord。 */
public class BoardPanel extends JComponent {

    private static final int BORDER = 3;

    private GameModel game;
    private int cell = UiTheme.CELL;

    private boolean leftDown, rightDown, chordArmed;
    private int pressC = -1, pressR = -1;
    private boolean useQuestion;

    /** 任意状态变化后的回调（用于刷新计数与笑脸）。 */
    private Runnable onStateChange;
    /** 每次操作产生的日志（供状态栏显示）。 */
    private java.util.function.Consumer<String> onLog;
    /** 首次点击的钩子：返回 true 表示外部已接管（例如正在异步生成雷区）。 */
    private java.util.function.BiPredicate<Integer, Integer> firstClickHook;

    public void setUseQuestion(boolean b) {
        useQuestion = b;
    }

    public void setFirstClickHook(java.util.function.BiPredicate<Integer, Integer> h) {
        firstClickHook = h;
    }

    public BoardPanel() {
        setOpaque(true);
        setBackground(UiTheme.BG);
        setFocusable(true);
        MouseAdapter ma = new MouseAdapter() {
            @Override
            public void mousePressed(MouseEvent e) {
                handlePressed(e);
            }

            @Override
            public void mouseReleased(MouseEvent e) {
                handleReleased(e);
            }

            @Override
            public void mouseExited(MouseEvent e) {
                pressC = pressR = -1;
                leftDown = rightDown = chordArmed = false;
                repaint();
            }
        };
        addMouseListener(ma);
    }

    public void setOnStateChange(Runnable r) {
        this.onStateChange = r;
    }

    public void setOnLog(java.util.function.Consumer<String> c) {
        this.onLog = c;
    }

    private void log(String s) {
        if (onLog != null) onLog.accept(s);
    }

    private void changed() {
        repaint();
        if (onStateChange != null) onStateChange.run();
    }

    public int cellSize() {
        return cell;
    }

    public void setCellSize(int px) {
        cell = Math.max(10, Math.min(40, px));
        revalidate();
        repaint();
    }

    public void setGame(GameModel g) {
        this.game = g;
        pressC = pressR = -1;
        leftDown = rightDown = chordArmed = false;
        revalidate();
        repaint();
        if (onStateChange != null) onStateChange.run();
    }

    public GameModel game() {
        return game;
    }

    @Override
    public Dimension getPreferredSize() {
        if (game == null) return new Dimension(200, 200);
        return new Dimension(game.cols() * cell + BORDER * 2, game.rows() * cell + BORDER * 2);
    }

    private int colAt(int x) {
        int c = (x - BORDER) / cell;
        if (game == null || c < 0 || c >= game.cols()) return -1;
        return c;
    }

    private int rowAt(int y) {
        int r = (y - BORDER) / cell;
        if (game == null || r < 0 || r >= game.rows()) return -1;
        return r;
    }

    // -------------------------------------------------------------- 鼠标交互

    private void handlePressed(MouseEvent e) {
        if (game == null) return;
        int c = colAt(e.getX()), r = rowAt(e.getY());
        if (c < 0 || r < 0) return;
        if (SwingUtilities.isLeftMouseButton(e)) leftDown = true;
        if (SwingUtilities.isRightMouseButton(e)) rightDown = true;
        pressC = c;
        pressR = r;
        if (leftDown && rightDown) {
            chordArmed = true;
            int n = game.chord(c, r).size();
            if (n > 0) log("chord (" + c + "," + r + ") 展开 " + n + " 格");
            changed();
        } else {
            repaint();
        }
    }

    private void handleReleased(MouseEvent e) {
        if (game == null) return;
        boolean wasChord = chordArmed;
        int c = pressC, r = pressR;
        if (SwingUtilities.isLeftMouseButton(e)) leftDown = false;
        if (SwingUtilities.isRightMouseButton(e)) rightDown = false;
        if (!leftDown && !rightDown) chordArmed = false;

        if (wasChord) {
            if (pressC >= 0) changed();
            return;
        }
        if (c < 0 || r < 0) {
            repaint();
            return;
        }
        if (SwingUtilities.isLeftMouseButton(e)) {
            GameModel.State st = game.stateAt(c, r);
            if (st == GameModel.State.OPEN && game.adjacentAt(c, r) > 0) {
                int n = game.chord(c, r).size();       // 经典行为：点已翻开的数字格也能展开
                if (n > 0) log("展开 (" + c + "," + r + ") " + n + " 格");
            } else if (st == GameModel.State.HIDDEN || st == GameModel.State.QUESTION) {
                if (!game.hasMines() && firstClickHook != null) {
                    if (firstClickHook.test(c, r)) {   // 外部接管：正在生成雷区
                        pressC = pressR = -1;
                        changed();
                        return;
                    }
                }
                game.reveal(c, r);
            }
            changed();
        } else if (SwingUtilities.isRightMouseButton(e)) {
            if (game.toggleFlag(c, r, useQuestion)) changed();
        }
        pressC = pressR = -1;
    }

    // ------------------------------------------------------------------ 绘制

    @Override
    protected void paintComponent(Graphics g0) {
        Graphics2D g = (Graphics2D) g0.create();
        int w = getWidth(), h = getHeight();
        g.setColor(UiTheme.BG);
        g.fillRect(0, 0, w, h);
        if (game == null) {
            g.dispose();
            return;
        }
        UiTheme.sunkenBorder(g, 0, 0, w, h);
        g.translate(BORDER, BORDER);
        for (int r = 0; r < game.rows(); r++) {
            for (int c = 0; c < game.cols(); c++) {
                drawCell(g, c * cell, r * cell, c, r);
            }
        }
        g.dispose();
    }

    private void drawCell(Graphics2D g, int x, int y, int c, int r) {
        GameModel.State st = game.stateAt(c, r);
        boolean over = game.isGameOver();
        int s = cell;
        if (st == GameModel.State.OPEN) {
            if (game.isMine(c, r) && game.idx(c, r) == game.explodedIdx()) {
                g.setColor(new Color(255, 0, 0));      // 踩中的那颗：红底
                g.fillRect(x, y, s, s);
            } else {
                UiTheme.openedCell(g, x, y, s);
            }
            if (game.isMine(c, r)) {
                UiTheme.mine(g, x, y, s);
            } else {
                int n = game.adjacentAt(c, r);
                if (n > 0) drawNumber(g, x, y, s, n);
            }
            return;
        }
        boolean pressed = (pressC == c && pressR == r && (leftDown || rightDown));
        if (pressed) UiTheme.lowered(g, x, y, s, s);
        else UiTheme.raised(g, x, y, s, s);

        if (st == GameModel.State.FLAG) {
            if (over && !game.isMine(c, r)) UiTheme.wrongFlag(g, x, y, s);
            else UiTheme.flag(g, x, y, s);
        } else if (st == GameModel.State.QUESTION) {
            drawQuestion(g, x, y, s);
        } else if (over && game.isMine(c, r)) {
            UiTheme.mine(g, x, y, s);
        }
    }

    private void drawNumber(Graphics2D g, int x, int y, int s, int n) {
        g.setColor(UiTheme.NUM_COLORS[Math.max(1, Math.min(8, n))]);
        g.setFont(new Font(Font.SANS_SERIF, Font.BOLD, s - 3));
        String t = String.valueOf(n);
        FontMetrics fm = g.getFontMetrics();
        int tx = x + (s - fm.stringWidth(t)) / 2;
        int ty = y + (s - fm.getHeight()) / 2 + fm.getAscent();
        g.drawString(t, tx, ty);
    }

    private void drawQuestion(Graphics2D g, int x, int y, int s) {
        g.setColor(Color.BLACK);
        g.setFont(new Font(Font.SANS_SERIF, Font.BOLD, s - 3));
        FontMetrics fm = g.getFontMetrics();
        String t = "?";
        g.drawString(t, x + (s - fm.stringWidth(t)) / 2, y + (s - fm.getHeight()) / 2 + fm.getAscent());
    }
}
