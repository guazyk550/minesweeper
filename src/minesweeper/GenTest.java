package minesweeper;

import java.util.Random;

/** 核心算法自测：随机地图中有多少是纯逻辑可解的，以及生成器要试几次。 */
public class GenTest {

    public static void main(String[] args) {
        GameModel.Difficulty[] all = {
                GameModel.Difficulty.BEGINNER,
                GameModel.Difficulty.INTERMEDIATE,
                GameModel.Difficulty.EXPERT,
        };
        Random rnd = new Random(20240501L);
        int trials = 12;
        for (GameModel.Difficulty d : all) {
            int sc = d.cols() / 2, sr = d.rows() / 2;
            int solvable = 0, needGuess = 0, broken = 0;
            long t0 = System.currentTimeMillis();
            for (int i = 0; i < trials; i++) {
                boolean[][] m = BoardGenerator.randomMines(d, sc, sr, rnd);
                int g = BoardGenerator.simulate(d, m, sc, sr, 1);
                if (g == 0) solvable++;
                else if (g > 0) needGuess++;
                else broken++;
            }
            long dt = System.currentTimeMillis() - t0;
            System.out.printf("%-12s random boards: logically-solvable=%d, needs-guess=%d, bad=%d  (%d trials, %dms)%n",
                    d.name(), solvable, needGuess, broken, trials, dt);

            for (int i = 0; i < 2; i++) {
                long g0 = System.currentTimeMillis();
                BoardGenerator.GenResult r = BoardGenerator.generate(d, sc, sr, 800, 3000);
                long gdt = System.currentTimeMillis() - g0;
                System.out.printf("             generated: attempts=%d guesses=%d time=%dms%n",
                        r.attempts, r.guesses, gdt);
            }
        }
        System.out.println("done");
    }
}
