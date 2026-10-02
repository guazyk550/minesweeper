package minesweeper;

import java.util.*;

/** 一局扫雷的完整状态与操作。 */
public class GameModel {

    public enum State {HIDDEN, OPEN, FLAG, QUESTION}

    /** 难度定义（初级 / 中级 / 高级 / 自定义）。 */
    public record Difficulty(String name, int cols, int rows, int mines) {
        public static final Difficulty BEGINNER = new Difficulty("初级", 9, 9, 10);
        public static final Difficulty INTERMEDIATE = new Difficulty("中级", 16, 16, 40);
        public static final Difficulty EXPERT = new Difficulty("高级", 30, 16, 99);

        public static Difficulty custom(int cols, int rows, int mines) {
            cols = clamp(cols, 5, 60);
            rows = clamp(rows, 5, 40);
            int max = Math.max(1, cols * rows - 9);
            mines = clamp(mines, 1, max);
            return new Difficulty("自定义", cols, rows, mines);
        }

        private static int clamp(int v, int lo, int hi) {
            return Math.max(lo, Math.min(hi, v));
        }

        @Override
        public String toString() {
            return String.format("%s (%d×%d, %d 雷)", name, cols, rows, mines);
        }
    }

    private final Difficulty diff;
    private final int cols, rows, mines;

    private boolean[][] mineMap;
    private int[][] adjacent;
    private State[][] state;

    private boolean firstClick = true;
    private boolean gameOver, won, exploded;
    private int flagsPlaced;
    private long startTime, endTime;
    private int explodedIdx = -1;

    /** 保证可解模式下，本次生成用了多少次尝试（仅用于展示）。 */
    public int generateAttempts = 1;

    public GameModel(Difficulty d, boolean[][] mineMap) {
        this.diff = d;
        this.cols = d.cols();
        this.rows = d.rows();
        this.mines = d.mines();
        this.mineMap = mineMap;
        this.state = new State[rows][cols];
        for (State[] row : state) Arrays.fill(row, State.HIDDEN);
        computeAdjacent();
    }

    public void setMineMap(boolean[][] m) {
        this.mineMap = m;
        computeAdjacent();
    }

    private void computeAdjacent() {
        adjacent = new int[rows][cols];
        if (mineMap == null) return;      // 延迟布雷：首次点击后才生成
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int n = 0;
                for (int dr = -1; dr <= 1; dr++) {
                    for (int dc = -1; dc <= 1; dc++) {
                        if (dc == 0 && dr == 0) continue;
                        int nr = r + dr, nc = c + dc;
                        if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && mineMap[nr][nc]) n++;
                    }
                }
                adjacent[r][c] = n;
            }
        }
    }

    /** 雷区是否已经生成（延迟布雷）。 */
    public boolean hasMines() {
        return mineMap != null;
    }

    // -------------------------------------------------------------- 基本访问

    public Difficulty difficulty() {
        return diff;
    }

    public int cols() {
        return cols;
    }

    public int rows() {
        return rows;
    }

    public int mines() {
        return mines;
    }

    public int idx(int c, int r) {
        return r * cols + c;
    }

    public int colOf(int idx) {
        return idx % cols;
    }

    public int rowOf(int idx) {
        return idx / cols;
    }

    public State stateAt(int c, int r) {
        return state[r][c];
    }

    public int adjacentAt(int c, int r) {
        return adjacent[r][c];
    }

    public boolean isMine(int c, int r) {
        return mineMap[r][c];
    }

    public boolean[][] mineMap() {
        return mineMap;
    }

    public boolean isGameOver() {
        return gameOver;
    }

    public boolean isWon() {
        return won;
    }

    public boolean isExploded() {
        return exploded;
    }

    public int explodedIdx() {
        return explodedIdx;
    }

    public int flagsPlaced() {
        return flagsPlaced;
    }

    public int minesLeft() {
        return mines - flagsPlaced;
    }

    public boolean isFirstClick() {
        return firstClick;
    }

    public long elapsedMillis() {
        if (startTime == 0) return 0;
        long end = gameOver ? endTime : System.currentTimeMillis();
        return Math.max(0, end - startTime);
    }

    public int elapsedSeconds() {
        return (int) Math.min(999, elapsedMillis() / 1000);
    }

    /** 已翻开的格子数。 */
    public int openedCount() {
        int n = 0;
        for (int r = 0; r < rows; r++)
            for (int c = 0; c < cols; c++)
                if (state[r][c] == State.OPEN) n++;
        return n;
    }

    public int hiddenCount() {
        int n = 0;
        for (int r = 0; r < rows; r++)
            for (int c = 0; c < cols; c++)
                if (state[r][c] == State.HIDDEN || state[r][c] == State.QUESTION) n++;
        return n;
    }

    // ------------------------------------------------------------------ 操作

    /** 左键：翻开。返回被翻开的格子索引列表（用于动画/日志）。 */
    public List<Integer> reveal(int c, int r) {
        List<Integer> changed = new ArrayList<>();
        if (gameOver || mineMap == null) return changed;
        if (c < 0 || r < 0 || c >= cols || r >= rows) return changed;
        if (state[r][c] == State.OPEN || state[r][c] == State.FLAG) return changed;

        if (firstClick) {
            firstClick = false;
            startTime = System.currentTimeMillis();
        }
        if (mineMap[r][c]) {
            state[r][c] = State.OPEN;
            exploded = true;
            gameOver = true;
            explodedIdx = idx(c, r);
            endTime = System.currentTimeMillis();
            changed.add(idx(c, r));
            return changed;
        }
        floodReveal(c, r, changed);
        checkWin();
        return changed;
    }

    private void floodReveal(int c, int r, List<Integer> changed) {
        Deque<int[]> stack = new ArrayDeque<>();
        stack.push(new int[]{c, r});
        while (!stack.isEmpty()) {
            int[] cur = stack.pop();
            int cc = cur[0], rr = cur[1];
            if (cc < 0 || rr < 0 || cc >= cols || rr >= rows) continue;
            if (state[rr][cc] == State.OPEN || state[rr][cc] == State.FLAG) continue;
            if (mineMap[rr][cc]) continue;
            state[rr][cc] = State.OPEN;
            changed.add(idx(cc, rr));
            if (adjacent[rr][cc] == 0) {
                for (int dr = -1; dr <= 1; dr++)
                    for (int dc = -1; dc <= 1; dc++) {
                        if (dc == 0 && dr == 0) continue;
                        stack.push(new int[]{cc + dc, rr + dr});
                    }
            }
        }
    }

    /** 右键：未翻开 -> 旗 -> (问号) -> 未翻开。 */
    public boolean toggleFlag(int c, int r, boolean useQuestion) {
        if (gameOver || c < 0 || r < 0 || c >= cols || r >= rows) return false;
        if (state[r][c] == State.OPEN) return false;
        if (firstClick) {   // 允许先插旗，但计时从第一次点击开始
            firstClick = false;
            startTime = System.currentTimeMillis();
        }
        switch (state[r][c]) {
            case HIDDEN -> {
                state[r][c] = State.FLAG;
                flagsPlaced++;
            }
            case FLAG -> {
                flagsPlaced--;
                state[r][c] = useQuestion ? State.QUESTION : State.HIDDEN;
            }
            default -> state[r][c] = State.HIDDEN;
        }
        return true;
    }

    /** 双键 / 左键点已翻开数字格：旗数满足时翻开其余邻居。 */
    public List<Integer> chord(int c, int r) {
        List<Integer> changed = new ArrayList<>();
        if (gameOver || c < 0 || r < 0 || c >= cols || r >= rows) return changed;
        if (state[r][c] != State.OPEN || adjacent[r][c] == 0) return changed;
        int need = adjacent[r][c];
        int flags = 0;
        List<int[]> targets = new ArrayList<>();
        for (int dr = -1; dr <= 1; dr++)
            for (int dc = -1; dc <= 1; dc++) {
                if (dc == 0 && dr == 0) continue;
                int nr = r + dr, nc = c + dc;
                if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
                if (state[nr][nc] == State.FLAG) flags++;
                else if (state[nr][nc] != State.OPEN) targets.add(new int[]{nc, nr});
            }
        if (flags != need || targets.isEmpty()) return changed;
        for (int[] t : targets) {
            if (gameOver) break;
            if (mineMap[t[1]][t[0]]) {
                state[t[1]][t[0]] = State.OPEN;
                exploded = true;
                gameOver = true;
                explodedIdx = idx(t[0], t[1]);
                endTime = System.currentTimeMillis();
                changed.add(idx(t[0], t[1]));
                break;
            }
            floodReveal(t[0], t[1], changed);
        }
        if (!gameOver) checkWin();
        return changed;
    }

    private void checkWin() {
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (!mineMap[r][c] && state[r][c] != State.OPEN) return;
            }
        }
        won = true;
        gameOver = true;
        endTime = System.currentTimeMillis();
        // 胜利时自动为所有雷插旗（和经典扫雷一致）
        flagsPlaced = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (mineMap[r][c]) {
                    state[r][c] = State.FLAG;
                    flagsPlaced++;
                }
            }
        }
    }

    // ------------------------------------------------------------ 供求解器用

    public Solver.Panel toPanel() {
        Map<Integer, Integer> open = new HashMap<>();
        Set<Integer> flags = new HashSet<>(), unknown = new HashSet<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int i = idx(c, r);
                switch (state[r][c]) {
                    case OPEN -> open.put(i, adjacent[r][c]);
                    case FLAG -> flags.add(i);
                    default -> unknown.add(i);
                }
            }
        }
        return new Solver.Panel(cols, rows, mines, open, flags, unknown);
    }

    /** 导出当前局面的文本快照（便于测试与调试）。 */
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                switch (state[r][c]) {
                    case OPEN -> sb.append(adjacent[r][c] == 0 ? '.' : (char) ('0' + adjacent[r][c]));
                    case FLAG -> sb.append('F');
                    case QUESTION -> sb.append('?');
                    default -> sb.append('#');
                }
            }
            sb.append('\n');
        }
        return sb.toString();
    }
}
