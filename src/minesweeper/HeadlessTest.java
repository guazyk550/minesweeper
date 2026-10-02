package minesweeper;

import java.util.Map;

/** 无界面测试：直接驱动 GameModel + Solver 自动通关，验证核心逻辑。 */
public class HeadlessTest {

    /** 自动玩一局，返回 [是否胜利, 步数, 猜测次数]。 */
    public static int[] autoPlay(GameModel.Difficulty d, int sc, int sr, boolean solvableOnly) {
        BoardGenerator.GenResult res = BoardGenerator.generate(d, sc, sr, 900, 2500);
        if (solvableOnly && !res.perfect()) {
            System.out.println("  (warning: best map still needs " + res.guesses + " guesses)");
        }
        GameModel g = new GameModel(d, res.mines);
        g.reveal(sc, sr);
        int steps = 0, guesses = 0;
        while (!g.isGameOver() && steps < 5000) {
            Solver.Panel p = g.toPanel();
            Solver.Result sol = Solver.solve(p);
            if (sol.contradiction) {
                System.out.println("  contradiction!");
                break;
            }
            boolean acted = false;
            if (!sol.mines.isEmpty()) {
                for (int m : sol.mines) g.toggleFlag(g.colOf(m), g.rowOf(m), false);
                acted = true;
            }
            if (!sol.safe.isEmpty()) {
                for (int s : sol.safe) g.reveal(g.colOf(s), g.rowOf(s));
                acted = true;
            }
            if (!acted && !sol.probs.isEmpty()) {
                int best = -1;
                double bp = 2;
                for (Map.Entry<Integer, Double> e : sol.probs.entrySet()) {
                    if (e.getValue() < bp) {
                        bp = e.getValue();
                        best = e.getKey();
                    }
                }
                if (best >= 0) {
                    guesses++;
                    g.reveal(g.colOf(best), g.rowOf(best));
                    acted = true;
                }
            }
            if (!acted) break;
            steps++;
        }
        return new int[]{g.isWon() ? 1 : 0, steps, guesses, g.openedCount(), res.attempts, res.guesses};
    }

    public static void main(String[] args) {
        GameModel.Difficulty[] all = {
                GameModel.Difficulty.BEGINNER,
                GameModel.Difficulty.INTERMEDIATE,
                GameModel.Difficulty.EXPERT,
        };
        for (GameModel.Difficulty d : all) {
            int sc = d.cols() / 2, sr = d.rows() / 2;
            int wins = 0, totSteps = 0, totGuess = 0;
            int rounds = 5;
            long t0 = System.currentTimeMillis();
            for (int i = 0; i < rounds; i++) {
                int[] r = autoPlay(d, sc, sr, true);
                wins += r[0];
                totSteps += r[1];
                totGuess += r[2];
                System.out.printf("  %s #%d won=%s steps=%d guesses=%d opened=%d/%d genAttempts=%d genGuesses=%d%n",
                        d.name(), i + 1, r[0] == 1, r[1], r[2], r[3], d.cols() * d.rows() - d.mines(), r[4], r[5]);
            }
            System.out.printf("%s: wins=%d/%d avgSteps=%.1f avgGuesses=%.2f time=%dms%n",
                    d.name(), wins, rounds, totSteps / (double) rounds, totGuess / (double) rounds,
                    System.currentTimeMillis() - t0);
        }
        System.out.println("done");
    }
}
