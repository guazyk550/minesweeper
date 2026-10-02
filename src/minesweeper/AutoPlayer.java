package minesweeper;

import javax.swing.*;
import java.util.*;
import java.util.function.Consumer;

/**
 * 自动玩：后台线程里"求解 → 执行一步"，不卡界面。
 *
 * <p>因为它直接读游戏模型（不像外部程序那样靠截图识别），所以能拿到完整信息，
 * 也不存在识别误差。求解器给出的确定安全格直接翻、确定雷格直接插旗；
 * 实在没有确定结论时才挑"踩雷概率最低"的格去猜，并记录下来。
 */
public class AutoPlayer {

    public enum Speed {
        TURBO("极速", 0), FAST("快", 40), NORMAL("中", 160), SLOW("慢", 500);

        public final String label;
        public final int delayMs;

        Speed(String label, int delayMs) {
            this.label = label;
            this.delayMs = delayMs;
        }

        @Override
        public String toString() {
            return label;
        }
    }

    private final BoardPanel board;
    private Thread thread;
    private volatile boolean running;
    private volatile boolean paused;
    private volatile boolean stopRequested;
    private Speed speed = Speed.NORMAL;

    private int steps;
    private int guesses;
    private int clicks;
    private int chords;

    private Consumer<String> onLog = s -> {
    };
    private Runnable onFinish = () -> {
    };

    public AutoPlayer(BoardPanel board) {
        this.board = board;
    }

    public void setOnLog(Consumer<String> c) {
        this.onLog = c;
    }

    public void setOnFinish(Runnable r) {
        this.onFinish = r;
    }

    public void setSpeed(Speed s) {
        this.speed = s;
    }

    public Speed speed() {
        return speed;
    }

    public boolean isRunning() {
        return running && !paused;
    }

    public boolean isActive() {
        return running;
    }

    public int steps() {
        return steps;
    }

    public int guesses() {
        return guesses;
    }

    public int clicks() {
        return clicks;
    }

    public int chords() {
        return chords;
    }

    public void resetCounters() {
        steps = guesses = clicks = chords = 0;
    }

    public void start() {
        if (running) {
            paused = false;
            return;
        }
        resetCounters();
        stopRequested = false;
        running = true;
        paused = false;
        thread = new Thread(this::loop, "auto-player");
        thread.setDaemon(true);
        thread.start();
    }

    public void pause() {
        paused = true;
        onLog.accept("自动玩已暂停");
    }

    public void resume() {
        if (running) {
            paused = false;
            onLog.accept("自动玩继续");
        }
    }

    public void stop() {
        stopRequested = true;
        running = false;
        paused = false;
    }

    /** 单步：走一步就停。 */
    public void stepOnce() {
        if (running) {
            pause();
            return;
        }
        resetCounters();
        SwingUtilities.invokeLater(() -> {
            boolean acted = doStep();
            board.repaint();
            onLog.accept(acted ? "单步完成" : "没有可执行的步骤");
            onFinish.run();
        });
    }

    private void loop() {
        try {
            while (running && !stopRequested) {
                if (paused) {
                    Thread.sleep(50);
                    continue;
                }
                boolean acted = doStep();
                SwingUtilities.invokeLater(board::repaint);
                SwingUtilities.invokeLater(onFinish);
                if (!acted) {
                    break;
                }
                int d = speed.delayMs;
                if (d > 0) Thread.sleep(d);
                else Thread.yield();
            }
        } catch (InterruptedException ignored) {
        } finally {
            running = false;
            SwingUtilities.invokeLater(() -> {
                board.repaint();
                onFinish.run();
                onLog.accept(String.format("自动玩结束：%d 步，点击 %d 次，chord %d 次，猜测 %d 次",
                        steps, clicks, chords, guesses));
            });
        }
    }

    /** 找出可以用 chord 一次展开的已翻开数字格：周围所有未翻开格都已被证明安全。 */
    private List<Integer> chordCandidates(GameModel g, Set<Integer> safeSet) {
        List<Integer> out = new ArrayList<>();
        int total = g.cols() * g.rows();
        for (int idx = 0; idx < total; idx++) {
            int c = g.colOf(idx), r = g.rowOf(idx);
            if (g.stateAt(c, r) != GameModel.State.OPEN) continue;
            if (g.adjacentAt(c, r) <= 0) continue;
            boolean anyHidden = false, allSafe = true;
            for (int nb : Solver.neighbors(idx, g.cols(), g.rows())) {
                GameModel.State st = g.stateAt(g.colOf(nb), g.rowOf(nb));
                if (st == GameModel.State.HIDDEN || st == GameModel.State.QUESTION) {
                    anyHidden = true;
                    if (!safeSet.contains(nb)) {
                        allSafe = false;
                        break;
                    }
                }
            }
            if (anyHidden && allSafe) out.add(idx);
        }
        return out;
    }

    /** 走一步，返回是否真的做了操作。 */
    private boolean doStep() {
        GameModel g = board.game();
        if (g == null || g.isGameOver()) return false;

        Solver.Panel p = g.toPanel();
        Solver.Result r;
        try {
            r = Solver.solve(p);
        } catch (RuntimeException ex) {
            onLog.accept("求解异常：" + ex);
            return false;
        }
        if (r.contradiction) {
            onLog.accept("推理出现矛盾（旗可能插错了）");
            return false;
        }

        boolean acted = false;
        if (!r.mines.isEmpty()) {
            for (int m : r.mines) g.toggleFlag(g.colOf(m), g.rowOf(m), false);
            onLog.accept("确定 " + r.mines.size() + " 颗雷，已插旗");
            acted = true;
        }
        if (!r.safe.isEmpty()) {
            // 优先用 chord 一次展开多个：找那些"周围未翻开格都已证明安全"的已翻开数字格
            Set<Integer> safeSet = new HashSet<>(r.safe);
            Set<Integer> covered = new HashSet<>();
            for (int target : chordCandidates(g, safeSet)) {
                List<Integer> ch = g.chord(g.colOf(target), g.rowOf(target));
                if (!ch.isEmpty()) {
                    chords++;
                    covered.addAll(ch);
                }
            }
            int revealed = 0;
            for (int s : r.safe) {
                if (covered.contains(s)) continue;
                g.reveal(g.colOf(s), g.rowOf(s));
                revealed++;
            }
            clicks += revealed;
            onLog.accept(String.format("确定 %d 个安全格（chord 展开 %d 个），已翻开",
                    r.safe.size(), covered.size()));
            acted = true;
        }
        if (!acted && !r.probs.isEmpty()) {
            int best = -1;
            double bp = 2;
            for (Map.Entry<Integer, Double> e : r.probs.entrySet()) {
                if (e.getValue() < bp) {
                    bp = e.getValue();
                    best = e.getKey();
                }
            }
            if (best >= 0) {
                guesses++;
                clicks++;
                onLog.accept(String.format("没有确定解，猜 (%d,%d)：踩雷概率 %.1f%%",
                        g.colOf(best), g.rowOf(best), bp * 100));
                g.reveal(g.colOf(best), g.rowOf(best));
                acted = true;
            }
        }
        if (acted) steps++;
        return acted;
    }
}
