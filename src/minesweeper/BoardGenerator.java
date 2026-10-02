package minesweeper;

import java.util.*;

/**
 * 雷区生成器。
 *
 * <p>核心目标：<b>尽量避免经典扫雷那种"必须靠猜"的死局</b>。
 * 做法是"生成 + 用求解器复核"：随机布雷后，完全用逻辑推理去模拟解开这一局，
 * 一旦出现"没有任何确定安全格、必须猜"的时刻，就判定这局不合格，重新生成。
 * 在时限内若找不到 100% 纯逻辑可解的地图，则退而选"需要猜的次数最少"的那张。
 *
 * <p>第一次点击的位置周围 3×3 一定没有雷 —— 既保证首点安全，也让首点必然展开一片。
 */
public final class BoardGenerator {

    private BoardGenerator() {
    }

    /** 生成结果。 */
    public static final class GenResult {
        public final boolean[][] mines;
        /** 模拟解开这一局所需的猜测次数：0 = 纯逻辑可解。 */
        public final int guesses;
        /** 用掉了几次尝试。 */
        public final int attempts;

        GenResult(boolean[][] mines, int guesses, int attempts) {
            this.mines = mines;
            this.guesses = guesses;
            this.attempts = attempts;
        }

        public boolean perfect() {
            return guesses == 0;
        }
    }

    /** 随机布雷，避开首点 3x3。 */
    public static boolean[][] randomMines(GameModel.Difficulty d, int sc, int sr, Random rnd) {
        int cols = d.cols(), rows = d.rows(), mines = d.mines();
        int[] flat = new int[cols * rows];
        int n = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (Math.abs(c - sc) <= 1 && Math.abs(r - sr) <= 1) continue;
                flat[n++] = r * cols + c;
            }
        }
        for (int i = n - 1; i > 0; i--) {           // Fisher-Yates
            int j = rnd.nextInt(i + 1);
            int t = flat[i];
            flat[i] = flat[j];
            flat[j] = t;
        }
        boolean[][] m = new boolean[rows][cols];
        for (int i = 0; i < Math.min(mines, n); i++) m[flat[i] / cols][flat[i] % cols] = true;
        return m;
    }

    /**
     * 模拟"只用逻辑推理"能否解开这一局。
     *
     * @return 需要的猜测次数；-1 表示推理过程出现矛盾或猜错（这局不合格）
     */
    public static int simulate(GameModel.Difficulty d, boolean[][] mineMap, int sc, int sr, int maxGuesses) {
        GameModel g = new GameModel(d, mineMap);
        g.reveal(sc, sr);
        int guesses = 0;
        int guard = 0;
        while (!g.isGameOver() && guard++ < 10000) {
            Solver.Panel p = g.toPanel();
            Solver.Result r = Solver.deduce(p);
            if (r.contradiction) return -1;
            boolean acted = false;
            if (!r.mines.isEmpty()) {
                for (int m : r.mines) g.toggleFlag(g.colOf(m), g.rowOf(m), false);
                acted = true;
            }
            if (!r.safe.isEmpty()) {
                for (int s : r.safe) g.reveal(g.colOf(s), g.rowOf(s));
                acted = true;
            }
            if (g.isGameOver()) break;
            if (acted) continue;

            // 逻辑推不动了，看枚举能不能找出确定格
            Map<Integer, Double> probs = Solver.enumerate(p, Collections.emptySet(), Collections.emptySet());
            if (probs == null || probs.isEmpty()) return -1;
            List<Integer> zeros = new ArrayList<>(), ones = new ArrayList<>();
            for (Map.Entry<Integer, Double> e : probs.entrySet()) {
                if (e.getValue() <= 1e-9) zeros.add(e.getKey());
                else if (e.getValue() >= 1 - 1e-9) ones.add(e.getKey());
            }
            if (zeros.isEmpty() && ones.isEmpty()) {
                guesses++;
                if (guesses > maxGuesses) return guesses;
                int best = -1;
                double bestP = 2;
                for (Map.Entry<Integer, Double> e : probs.entrySet()) {
                    if (e.getValue() < bestP) {
                        bestP = e.getValue();
                        best = e.getKey();
                    }
                }
                if (best < 0) return -1;
                g.reveal(g.colOf(best), g.rowOf(best));
                if (g.isExploded()) return -1;      // 猜爆了，这局不合格
            } else {
                for (int m : ones) g.toggleFlag(g.colOf(m), g.rowOf(m), false);
                for (int s : zeros) g.reveal(g.colOf(s), g.rowOf(s));
            }
        }
        return g.isWon() ? guesses : -1;
    }

    /**
     * 生成雷区。
     *
     * @param maxTries    最多尝试多少次随机地图
     * @param timeBudgetMs 时间上限（毫秒），到点就用手上最好的一张
     */
    public static GenResult generate(GameModel.Difficulty d, int sc, int sr,
                                     int maxTries, long timeBudgetMs) {
        long t0 = System.currentTimeMillis();
        Random rnd = new Random();
        GenResult best = null;
        GenResult last = null;
        for (int t = 1; t <= maxTries; t++) {
            boolean[][] m = randomMines(d, sc, sr, rnd);
            int guesses = simulate(d, m, sc, sr, 3);
            GenResult r = new GenResult(m, guesses, t);
            last = r;
            if (guesses == 0) return r;                       // 纯逻辑可解，直接用
            if (guesses > 0 && (best == null || guesses < best.guesses)) best = r;
            if (System.currentTimeMillis() - t0 > timeBudgetMs) break;
        }
        if (best != null) return best;
        if (last != null) return last;
        return new GenResult(randomMines(d, sc, sr, rnd), -1, maxTries);
    }

    /** 快速版：只做有限尝试，适合不想等太久的场景。 */
    public static GenResult generate(GameModel.Difficulty d, int sc, int sr) {
        return generate(d, sc, sr, 400, 1500);
    }
}
