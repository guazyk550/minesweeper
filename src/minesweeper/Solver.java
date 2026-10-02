package minesweeper;

import java.util.*;

/**
 * 扫雷逻辑求解器。
 *
 * <p>三级推理：
 * <ol>
 *   <li>约束传播：数字格周围还缺几颗雷 —— 缺 0 颗则候选全安全，缺满则全是雷；</li>
 *   <li>子集差分：约束 A 的候选集是 B 的子集时，差集的雷数 = needB - needA；</li>
 *   <li>连通分量精确枚举 + 全局雷数约束（多项式 DP 加权），得到每格是雷的精确概率。</li>
 * </ol>
 *
 * <p>格子索引用 {@code idx = row * cols + col} 表示。
 */
public final class Solver {

    private Solver() {
    }

    /** 求解结果。 */
    public static final class Result {
        public final List<Integer> safe = new ArrayList<>();
        public final List<Integer> mines = new ArrayList<>();
        public final Map<Integer, Double> probs = new LinkedHashMap<>();
        public boolean contradiction;

        public boolean hasCertain() {
            return !safe.isEmpty() || !mines.isEmpty();
        }

        public boolean isEmpty() {
            return safe.isEmpty() && mines.isEmpty() && probs.isEmpty();
        }
    }

    /** 单次枚举的格子上限（超过就放弃枚举，退化为只用逻辑推理）。 */
    private static final int MAX_ENUM = 22;

    // ------------------------------------------------------------------ 基础

    /** 某格周围的 8 个邻居。 */
    public static int[] neighbors(int idx, int cols, int rows) {
        int c = idx % cols, r = idx / cols;
        int[] tmp = new int[8];
        int n = 0;
        for (int dr = -1; dr <= 1; dr++) {
            for (int dc = -1; dc <= 1; dc++) {
                if (dc == 0 && dr == 0) continue;
                int nr = r + dr, nc = c + dc;
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) tmp[n++] = nr * cols + nc;
            }
        }
        return Arrays.copyOf(tmp, n);
    }

    /** 邻居数量（角落 3、边上 5、内部 8）。 */
    public static int neighborCount(int idx, int cols, int rows) {
        return neighbors(idx, cols, rows).length;
    }

    private static final class Cons {
        final BitSet cand;
        final int need;

        Cons(BitSet cand, int need) {
            this.cand = cand;
            this.need = need;
        }
    }

    /** 面板的只读视图，求解所需的全部信息。 */
    public static final class Panel {
        public final int cols, rows, totalMines;
        public final Map<Integer, Integer> open;   // 已翻开的数字格 -> 数字
        public final Set<Integer> flags;           // 已插旗
        public final Set<Integer> unknown;         // 未翻开（不含旗）

        public Panel(int cols, int rows, int totalMines,
                     Map<Integer, Integer> open, Set<Integer> flags, Set<Integer> unknown) {
            this.cols = cols;
            this.rows = rows;
            this.totalMines = totalMines;
            this.open = open;
            this.flags = flags;
            this.unknown = unknown;
        }
    }

    /**
     * 构建约束表。{@code extraMines}/{@code extraSafe} 是推理过程中已确定的格，
     * 必须从候选集中剔除，否则 need 会被重复扣减。
     *
     * @return null 表示出现矛盾（旗插错了）
     */
    private static List<Cons> buildCons(Panel p, Set<Integer> extraMines, Set<Integer> extraSafe) {
        List<Cons> out = new ArrayList<>();
        int cols = p.cols, rows = p.rows;
        for (Map.Entry<Integer, Integer> e : p.open.entrySet()) {
            int idx = e.getKey(), v = e.getValue();
            if (v <= 0) continue;
            BitSet cand = new BitSet(cols * rows);
            int flagged = 0;
            for (int n : neighbors(idx, cols, rows)) {
                if (p.flags.contains(n) || extraMines.contains(n)) flagged++;
                else if (p.unknown.contains(n) && !extraSafe.contains(n)) cand.set(n);
            }
            int need = v - flagged;
            if (cand.isEmpty()) {
                if (need != 0) return null;
                continue;
            }
            out.add(new Cons(cand, need));
        }
        return out;
    }

    // -------------------------------------------------------------- 逻辑推理

    /** 只用确定性推理（不含枚举），返回 safe/mines。 */
    public static Result deduce(Panel p) {
        Result res = new Result();
        BitSet safe = new BitSet(p.cols * p.rows);
        BitSet mines = new BitSet(p.cols * p.rows);
        Set<Integer> extraSafe = new HashSet<>();
        Set<Integer> extraMines = new HashSet<>();

        for (int iter = 0; iter < 200; iter++) {
            List<Cons> cs = buildCons(p, extraMines, extraSafe);
            if (cs == null) {
                res.contradiction = true;
                return res;
            }
            BitSet newSafe = new BitSet(), newMine = new BitSet();
            for (Cons con : cs) {
                int size = con.cand.cardinality();
                if (con.need < 0 || con.need > size) {
                    res.contradiction = true;
                    return res;
                }
                if (con.need == 0) newSafe.or(con.cand);
                else if (con.need == size) newMine.or(con.cand);
            }
            subsetRule(cs, newSafe, newMine);

            newSafe.andNot(safe);
            newSafe.andNot(mines);
            newMine.andNot(safe);
            newMine.andNot(mines);
            newMine.andNot(newSafe);
            if (newSafe.isEmpty() && newMine.isEmpty()) break;

            safe.or(newSafe);
            mines.or(newMine);
            for (int i = newSafe.nextSetBit(0); i >= 0; i = newSafe.nextSetBit(i + 1)) extraSafe.add(i);
            for (int i = newMine.nextSetBit(0); i >= 0; i = newMine.nextSetBit(i + 1)) extraMines.add(i);
        }
        for (int i = safe.nextSetBit(0); i >= 0; i = safe.nextSetBit(i + 1)) res.safe.add(i);
        for (int i = mines.nextSetBit(0); i >= 0; i = mines.nextSetBit(i + 1)) res.mines.add(i);
        return res;
    }

    /** 子集差分规则：只比较共享候选格的约束对。 */
    private static void subsetRule(List<Cons> cs, BitSet newSafe, BitSet newMine) {
        Map<Integer, List<Integer>> byCell = new HashMap<>();
        for (int i = 0; i < cs.size(); i++) {
            for (int g = cs.get(i).cand.nextSetBit(0); g >= 0; g = cs.get(i).cand.nextSetBit(g + 1)) {
                byCell.computeIfAbsent(g, k -> new ArrayList<>()).add(i);
            }
        }
        Set<Long> seen = new HashSet<>();
        for (List<Integer> list : byCell.values()) {
            int sz = list.size();
            for (int a = 0; a < sz; a++) {
                for (int b = a + 1; b < sz; b++) {
                    int i = list.get(a), j = list.get(b);
                    long key = (long) Math.min(i, j) * 100000L + Math.max(i, j);
                    if (!seen.add(key)) continue;
                    BitSet ci = cs.get(i).cand, cj = cs.get(j).cand;
                    BitSet diff = (BitSet) ci.clone();
                    diff.andNot(cj);
                    int nd;
                    if (diff.isEmpty()) {                 // ci ⊆ cj
                        diff = (BitSet) cj.clone();
                        diff.andNot(ci);
                        nd = cs.get(j).need - cs.get(i).need;
                    } else {
                        BitSet diff2 = (BitSet) cj.clone();
                        diff2.andNot(ci);
                        if (!diff2.isEmpty()) continue;   // 互不包含
                        diff = (BitSet) ci.clone();
                        diff.andNot(cj);
                        nd = cs.get(i).need - cs.get(j).need;
                    }
                    if (nd == 0) newSafe.or(diff);
                    else if (nd == diff.cardinality()) newMine.or(diff);
                }
            }
        }
    }

    // ------------------------------------------------------- 枚举 + 全局概率

    /** 枚举前沿所有合法解，结合全局雷数约束算出每格是雷的概率。 */
    public static Map<Integer, Double> enumerate(Panel p, Set<Integer> extraMines, Set<Integer> extraSafe) {
        int cols = p.cols, rows = p.rows, total = cols * rows;
        Set<Integer> knownMines = new HashSet<>(p.flags);
        knownMines.addAll(extraMines);
        Set<Integer> unknown = new HashSet<>(p.unknown);
        unknown.removeAll(extraMines);
        if (unknown.isEmpty()) return new LinkedHashMap<>();

        int totalMines = p.totalMines;
        int remain = totalMines - knownMines.size();
        if (remain < 0 || remain > unknown.size()) return null;

        List<Cons> cs = buildCons(p, extraMines, extraSafe);
        if (cs == null) return null;

        BitSet frontier = new BitSet(total);
        for (Cons con : cs) frontier.or(con.cand);
        BitSet nonFront = new BitSet(total);
        for (int g : unknown) if (!frontier.get(g)) nonFront.set(g);

        // 并查集：同一约束内的格属于同一分量
        int[] parent = new int[total];
        for (int i = 0; i < total; i++) parent[i] = i;
        for (Cons con : cs) {
            int first = con.cand.nextSetBit(0);
            for (int g = con.cand.nextSetBit(0); g >= 0; g = con.cand.nextSetBit(g + 1)) {
                union(parent, first, g);
            }
        }
        Map<Integer, List<Integer>> groups = new LinkedHashMap<>();
        for (int g = frontier.nextSetBit(0); g >= 0; g = frontier.nextSetBit(g + 1)) {
            groups.computeIfAbsent(find(parent, g), k -> new ArrayList<>()).add(g);
        }

        // 逐分量枚举
        List<int[]> compCells = new ArrayList<>();
        List<int[]> compMasks = new ArrayList<>();
        List<long[]> compCounts = new ArrayList<>();   // [雷数] = 解数
        for (List<Integer> cells : groups.values()) {
            int k = cells.size();
            if (k > MAX_ENUM) return null;
            int[] arr = new int[k];
            Map<Integer, Integer> pos = new HashMap<>();
            for (int i = 0; i < k; i++) {
                arr[i] = cells.get(i);
                pos.put(cells.get(i), i);
            }
            // 该分量内的约束
            List<Cons> my = new ArrayList<>();
            BitSet cellSet = new BitSet(total);
            for (int g : arr) cellSet.set(g);
            for (Cons con : cs) {
                BitSet t = (BitSet) con.cand.clone();
                t.andNot(cellSet);
                if (t.isEmpty()) my.add(con);
            }
            List<Integer> masks = new ArrayList<>();
            int limit = 1 << k;
            long[] cnt = new long[k + 1];
            for (int mask = 0; mask < limit; mask++) {
                boolean ok = true;
                for (Cons con : my) {
                    int hit = 0;
                    for (int g = con.cand.nextSetBit(0); g >= 0; g = con.cand.nextSetBit(g + 1)) {
                        if ((mask & (1 << pos.get(g))) != 0) hit++;
                    }
                    if (hit != con.need) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    masks.add(mask);
                    cnt[Integer.bitCount(mask)]++;
                }
            }
            if (masks.isEmpty()) return null;
            compCells.add(arr);
            compMasks.add(toIntArray(masks));
            compCounts.add(cnt);
        }

        int nf = nonFront.cardinality();
        int lo = Math.max(0, remain - nf);
        int hi = Math.min(remain, frontier.cardinality());
        if (lo > hi) return null;

        // 前缀/后缀 DP（按雷数分组）
        int m = compCells.size();
        List<long[]> left = new ArrayList<>();
        left.add(new long[]{1L});
        for (int i = 0; i < m; i++) left.add(convolve(left.get(i), compCounts.get(i)));
        List<long[]> right = new ArrayList<>();
        for (int i = 0; i <= m; i++) right.add(null);
        right.set(m, new long[]{1L});
        for (int i = m - 1; i >= 0; i--) right.set(i, convolve(right.get(i + 1), compCounts.get(i)));

        long totalValid = 0;
        for (int k = lo; k <= hi && k < left.get(m).length; k++) totalValid += left.get(m)[k];
        if (totalValid == 0) return null;

        Map<Integer, Double> probs = new LinkedHashMap<>();
        for (int i = 0; i < m; i++) {
            long[] pair = convolve(left.get(i), right.get(i + 1));
            int[] cells = compCells.get(i);
            int[] masks = compMasks.get(i);
            long[] hits = new long[cells.length];
            for (int mask : masks) {
                int x = Integer.bitCount(mask);
                long w = 0;
                for (int t = Math.max(0, lo - x); t <= hi - x && t < pair.length; t++) w += pair[t];
                if (w == 0) continue;
                for (int b = 0; b < cells.length; b++) {
                    if ((mask & (1 << b)) != 0) hits[b] += w;
                }
            }
            for (int b = 0; b < cells.length; b++) {
                probs.put(cells[b], hits[b] / (double) totalValid);
            }
        }
        if (nf > 0) {
            long acc = 0;
            long[] all = left.get(m);
            for (int k = lo; k <= hi && k < all.length; k++) acc += all[k] * (remain - k);
            double prob = acc / (double) totalValid / nf;
            for (int g = nonFront.nextSetBit(0); g >= 0; g = nonFront.nextSetBit(g + 1)) probs.put(g, prob);
        }
        return probs;
    }

    /**
     * 完整求解：先逻辑推理，没有结论时再枚举概率。
     *
     * <p>枚举出来的"概率 0 / 概率 1"同样属于确定结论，会一并放进 {@link Result#safe}
     * 和 {@link Result#mines}；因此调用方只要看到 safe/mines 为空、probs 非空，
     * 就说明这一步<b>真的必须猜</b>。
     */
    public static Result solve(Panel p) {
        Result r = deduce(p);
        if (r.contradiction) return r;
        if (r.hasCertain()) return r;
        Map<Integer, Double> probs = enumerate(p, Collections.emptySet(), Collections.emptySet());
        if (probs != null) {
            r.probs.putAll(probs);
            for (Map.Entry<Integer, Double> e : probs.entrySet()) {
                if (e.getValue() <= 1e-9) r.safe.add(e.getKey());
                else if (e.getValue() >= 1 - 1e-9) r.mines.add(e.getKey());
            }
        }
        return r;
    }

    // ------------------------------------------------------------------ 工具

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    }

    private static void union(int[] parent, int a, int b) {
        int ra = find(parent, a), rb = find(parent, b);
        if (ra != rb) parent[ra] = rb;
    }

    private static int[] toIntArray(List<Integer> list) {
        int[] a = new int[list.size()];
        for (int i = 0; i < a.length; i++) a[i] = list.get(i);
        return a;
    }

    /** 两个「按雷数分组的解数」数组的卷积。 */
    private static long[] convolve(long[] a, long[] b) {
        long[] out = new long[a.length + b.length - 1];
        for (int i = 0; i < a.length; i++) {
            if (a[i] == 0) continue;
            for (int j = 0; j < b.length; j++) {
                if (b[j] == 0) continue;
                out[i + j] += a[i] * b[j];
            }
        }
        return out;
    }
}
