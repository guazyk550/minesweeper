package minesweeper;

import javax.swing.*;
import javax.swing.border.BevelBorder;
import javax.swing.border.CompoundBorder;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.KeyEvent;
import java.util.List;
import java.util.Random;

/** 主窗口：菜单 + LED 计数面板 + 笑脸重开 + 棋盘 + 自动玩控制条。 */
public class MainFrame extends JFrame {

    private GameModel.Difficulty diff = lastDifficulty();
    private GameModel game;

    private final BoardPanel board = new BoardPanel();
    private final LedCounter mineLed = new LedCounter();
    private final LedCounter timeLed = new LedCounter();
    private final FaceButton faceBtn = new FaceButton(e -> newGame(diff));
    private final AutoPlayer auto = new AutoPlayer(board);

    private final JLabel status = new JLabel(" 就绪");
    private final JCheckBox solvableChk = new JCheckBox("保证可解", true);
    private final JCheckBox markChk = new JCheckBox("问号标记", false);
    private final JComboBox<AutoPlayer.Speed> speedBox = new JComboBox<>(AutoPlayer.Speed.values());
    private final JButton autoBtn = new JButton("▶ 自动玩");
    private final JButton stepBtn = new JButton("单步");
    private final JPanel boardHolder = new JPanel(new GridBagLayout());

    private JCheckBoxMenuItem solvableItem;
    private JCheckBoxMenuItem markItem;
    private boolean demoExit;
    private boolean endHandled;
    /** 整体缩放：格子、数码管、笑脸、数字字体一起变。 */
    private double scale = PREFS.getDouble("scale", 1.25);

    /** 记住上次用的难度与缩放。Java 内置的 Preferences，Windows 下落注册表
     *  （HKCU\Software\JavaSoft\Prefs），不会在程序目录留下配置文件。 */
    private static final java.util.prefs.Preferences PREFS =
            java.util.prefs.Preferences.userNodeForPackage(MainFrame.class);

    /** 读上次的难度；没存过或存的值不合法就回到初级。 */
    private static GameModel.Difficulty lastDifficulty() {
        int cols = PREFS.getInt("cols", 0);
        int rows = PREFS.getInt("rows", 0);
        int mines = PREFS.getInt("mines", 0);
        for (GameModel.Difficulty d : new GameModel.Difficulty[]{
                GameModel.Difficulty.BEGINNER,
                GameModel.Difficulty.INTERMEDIATE,
                GameModel.Difficulty.EXPERT}) {
            if (d.cols() == cols && d.rows() == rows && d.mines() == mines) {
                return d;
            }
        }
        if (cols < 5 || rows < 5 || mines < 1) {
            return GameModel.Difficulty.BEGINNER;
        }
        return GameModel.Difficulty.custom(cols, rows, mines);
    }

    private static void rememberDifficulty(GameModel.Difficulty d) {
        PREFS.putInt("cols", d.cols());
        PREFS.putInt("rows", d.rows());
        PREFS.putInt("mines", d.mines());
    }

    public MainFrame() {
        super("扫雷 Minesweeper");
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setResizable(false);
        buildMenu();
        buildUI();
        newGame(diff);
        new Timer(200, e -> tick()).start();
        applyScale(scale);
        setLocationRelativeTo(null);
    }

    /** 应用整体缩放并重新适配窗口。 */
    private void applyScale(double s) {
        scale = s;
        PREFS.putDouble("scale", s);           // 记住缩放，下次打开还是这个大小
        board.setCellSize((int) Math.round(UiTheme.CELL * s));
        mineLed.setScale(s);
        timeLed.setScale(s);
        faceBtn.setScale(s);
        packToFit(true);
        status.setText(String.format(" 缩放 %d%%（格子 %dpx）", (int) Math.round(s * 100), board.cellSize()));
    }

    // ------------------------------------------------------------------ 构建

    private void buildMenu() {
        JMenuBar bar = new JMenuBar();

        JMenu game = new JMenu("游戏(G)");
        game.setMnemonic('G');

        JMenuItem ng = new JMenuItem("新游戏(N)");
        ng.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_F2, 0));
        ng.addActionListener(e -> newGame(diff));
        game.add(ng);
        game.addSeparator();

        ButtonGroup bg = new ButtonGroup();
        List<GameModel.Difficulty> presets = List.of(
                GameModel.Difficulty.BEGINNER, GameModel.Difficulty.INTERMEDIATE, GameModel.Difficulty.EXPERT);
        for (GameModel.Difficulty d : presets) {
            JRadioButtonMenuItem item = new JRadioButtonMenuItem(d.toString());
            if (d == GameModel.Difficulty.BEGINNER) item.setSelected(true);
            item.addActionListener(e -> newGame(d));
            bg.add(item);
            game.add(item);
        }
        JMenuItem custom = new JMenuItem("自定义(C)…");
        custom.addActionListener(e -> customDialog());
        game.add(custom);
        game.addSeparator();

        solvableItem = new JCheckBoxMenuItem("保证可解（避开必猜死局）", true);
        solvableItem.addActionListener(e -> solvableChk.setSelected(solvableItem.isSelected()));
        game.add(solvableItem);
        markItem = new JCheckBoxMenuItem("允许问号标记(?)", false);
        markItem.addActionListener(e -> markChk.setSelected(markItem.isSelected()));
        game.add(markItem);
        game.addSeparator();

        JMenuItem exit = new JMenuItem("退出(X)");
        exit.addActionListener(e -> dispose());
        game.add(exit);

        JMenu view = new JMenu("视图(V)");
        view.setMnemonic('V');
        ButtonGroup vg = new ButtonGroup();
        double[] opts = {1.0, 1.25, 1.5, 2.0};
        String[] labels = {"100%（经典 16px）", "125%（默认）", "150%", "200%"};
        for (int i = 0; i < opts.length; i++) {
            double s = opts[i];
            JRadioButtonMenuItem it = new JRadioButtonMenuItem(labels[i]);
            if (Math.abs(s - scale) < 1e-9) it.setSelected(true);
            it.addActionListener(e -> applyScale(s));
            vg.add(it);
            view.add(it);
        }

        JMenu autoMenu = new JMenu("自动(A)");
        autoMenu.setMnemonic('A');
        JMenuItem startItem = new JMenuItem("开始 / 暂停自动玩");
        startItem.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_SPACE, 0));
        startItem.addActionListener(e -> toggleAuto());
        autoMenu.add(startItem);
        JMenuItem stepItem = new JMenuItem("单步");
        stepItem.addActionListener(e -> auto.stepOnce());
        autoMenu.add(stepItem);
        autoMenu.addSeparator();
        ButtonGroup sg = new ButtonGroup();
        for (AutoPlayer.Speed s : AutoPlayer.Speed.values()) {
            JRadioButtonMenuItem item = new JRadioButtonMenuItem(s.label + "（" + s.delayMs + "ms/步）");
            if (s == AutoPlayer.Speed.NORMAL) item.setSelected(true);
            item.addActionListener(e -> {
                speedBox.setSelectedItem(s);
                auto.setSpeed(s);
            });
            sg.add(item);
            autoMenu.add(item);
        }
        autoMenu.addSeparator();
        JMenuItem resetItem = new JMenuItem("重置统计");
        resetItem.addActionListener(e -> {
            auto.resetCounters();
            status.setText(" 统计已重置");
        });
        autoMenu.add(resetItem);

        JMenu help = new JMenu("帮助(H)");
        help.setMnemonic('H');
        JMenuItem about = new JMenuItem("关于…");
        about.addActionListener(e -> JOptionPane.showMessageDialog(this,
                """
                        扫雷 Minesweeper（Java / Swing）
                        
                        · 保留经典初级 / 中级 / 高级，另可自定义任意行列与雷数
                        · 「保证可解」开启时，生成的地图经过求解器复核，
                          不会出现必须靠猜才能继续的死局
                        · 笑脸 = 重开一局；右键插旗；已翻开的数字格上左右键同按
                          或直接左键点击可展开相邻安全格（chord）
                        · 「自动玩」内置求解器自动通关，无需外部程序
                        """, "关于", JOptionPane.INFORMATION_MESSAGE));
        help.add(about);

        bar.add(game);
        bar.add(view);
        bar.add(autoMenu);
        bar.add(help);
        setJMenuBar(bar);
    }

    private void buildUI() {
        JPanel content = new JPanel(new BorderLayout());
        content.setBackground(UiTheme.BG);

        // 顶部：雷数 LED + 笑脸 + 秒表 LED
        JPanel top = new JPanel(new BorderLayout());
        top.setBackground(UiTheme.BG);
        top.setBorder(new CompoundBorder(new EmptyBorder(5, 5, 5, 5),
                new BevelBorder(BevelBorder.LOWERED, UiTheme.LIGHT, UiTheme.DARK)));
        JPanel topWest = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        topWest.setBackground(UiTheme.BG);
        topWest.add(mineLed);
        JPanel topEast = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
        topEast.setBackground(UiTheme.BG);
        topEast.add(timeLed);
        top.add(topWest, BorderLayout.WEST);
        top.add(faceBtn, BorderLayout.CENTER);
        top.add(topEast, BorderLayout.EAST);

        // 棋盘
        boardHolder.setBackground(UiTheme.BG);
        boardHolder.add(board);

        // 底部控制条：分两行排，窄棋盘（初级/中级）时窗口就不会被撑得太宽
        JPanel row1 = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 2));
        row1.setBackground(UiTheme.BG);
        row1.add(autoBtn);
        row1.add(stepBtn);
        row1.add(new JLabel("速度"));
        row1.add(speedBox);

        JPanel row2 = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 2));
        row2.setBackground(UiTheme.BG);
        row2.add(solvableChk);
        row2.add(markChk);

        JPanel controls = new JPanel(new GridLayout(2, 1, 0, 0));
        controls.setBackground(UiTheme.BG);
        controls.add(row1);
        controls.add(row2);

        status.setForeground(new Color(60, 60, 60));
        status.setBorder(new EmptyBorder(2, 6, 4, 6));

        JPanel south = new JPanel(new BorderLayout());
        south.setBackground(UiTheme.BG);
        south.add(controls, BorderLayout.NORTH);
        south.add(status, BorderLayout.SOUTH);

        content.add(top, BorderLayout.NORTH);
        content.add(boardHolder, BorderLayout.CENTER);
        content.add(south, BorderLayout.SOUTH);
        setContentPane(content);

        // 事件接线
        autoBtn.addActionListener(e -> toggleAuto());
        stepBtn.addActionListener(e -> auto.stepOnce());
        speedBox.addActionListener(e -> {
            AutoPlayer.Speed s = (AutoPlayer.Speed) speedBox.getSelectedItem();
            if (s != null) auto.setSpeed(s);
        });
        solvableChk.addActionListener(e -> {
            if (solvableItem != null) solvableItem.setSelected(solvableChk.isSelected());
        });
        markChk.addActionListener(e -> {
            board.setUseQuestion(markChk.isSelected());
            if (markItem != null) markItem.setSelected(markChk.isSelected());
        });
        board.setOnStateChange(this::onBoardChanged);
        board.setOnLog(s -> status.setText(" " + s));
        board.setFirstClickHook((c, r) -> {
            if (game.hasMines()) return false;
            generateThenClick(c, r);
            return true;
        });
        auto.setOnLog(s -> status.setText(" " + s));
        auto.setOnFinish(this::onAutoFinish);
    }

    // -------------------------------------------------------------- 游戏流程

    private void newGame(GameModel.Difficulty d) {
        auto.stop();
        auto.resetCounters();          // 否则状态栏会显示上一局的点击数/猜测数
        autoBtn.setText("▶ 自动玩");
        endHandled = false;
        this.diff = d;
        rememberDifficulty(d);         // 记住这个难度，下次打开直接用它
        game = new GameModel(d, null);          // 延迟布雷：首次点击后生成
        board.setGame(game);
        faceBtn.setKind(UiTheme.Face.SMILE);
        mineLed.setValue(d.mines());
        timeLed.setValue(0);
        status.setText(" 点击任意格子开始（首点安全，雷区首次点击后生成）");
        packToFit(false);
    }

    /** 首次点击：生成雷区（可选择"保证可解"），再执行翻开。 */
    private void generateThenClick(int c, int r) {
        if (!solvableChk.isSelected()) {
            game.setMineMap(BoardGenerator.randomMines(diff, c, r, new Random()));
            game.reveal(c, r);
            board.repaint();
            onBoardChanged();
            status.setText(" 雷区已生成（随机模式，不保证可解）");
            return;
        }
        status.setText(" 正在生成保证可解的雷区…");
        autoBtn.setEnabled(false);
        new Thread(() -> {
            BoardGenerator.GenResult res = BoardGenerator.generate(diff, c, r, 900, 2500);
            SwingUtilities.invokeLater(() -> {
                game.setMineMap(res.mines);
                game.reveal(c, r);
                board.repaint();
                onBoardChanged();
                autoBtn.setEnabled(true);
                status.setText(res.perfect()
                        ? String.format(" 雷区已生成：纯逻辑可解（试了 %d 张图）", res.attempts)
                        : String.format(" 雷区已生成：需猜 %d 次（试了 %d 张图）", res.guesses, res.attempts));
            });
        }, "generator").start();
    }

    private void toggleAuto() {
        if (game == null || game.isGameOver() || !game.hasMines()) {
            if (game == null || game.isGameOver()) newGame(diff);
            if (!game.hasMines()) {
                status.setText(" 请先点击一个格子，让雷区生成后再启动自动玩");
                return;
            }
        }
        if (auto.isRunning()) {
            auto.pause();
            autoBtn.setText("▶ 继续");
        } else if (auto.isActive()) {
            auto.resume();
            autoBtn.setText("⏸ 暂停");
        } else {
            auto.start();
            autoBtn.setText("⏸ 暂停");
        }
        updateFace();
    }

    private void onAutoFinish() {
        if (auto.isRunning()) autoBtn.setText("⏸ 暂停");
        else if (auto.isActive()) autoBtn.setText("▶ 继续");
        else autoBtn.setText("▶ 自动玩");
        if (game != null) {
            mineLed.setValue(game.minesLeft());
            timeLed.setValue(game.elapsedSeconds());
        }
        updateFace();
        checkGameEnd();          // 自动玩在后台线程操作棋盘，必须在这里补一次结束检查
    }

    private void onBoardChanged() {
        if (game == null) return;
        mineLed.setValue(game.minesLeft());
        updateFace();
        checkGameEnd();
    }

    /** 游戏结束只处理一次。 */
    private void checkGameEnd() {
        if (game == null || !game.isGameOver() || endHandled) return;
        endHandled = true;
        auto.stop();
        autoBtn.setText("▶ 自动玩");
        updateFace();
        if (game.isWon()) {
            status.setText(String.format(" 通关！用时 %d 秒（%d 次点击，%d 次猜测）",
                    game.elapsedSeconds(), auto.clicks(), auto.guesses()));
        } else {
            status.setText(" 踩雷了…点笑脸重开一局");
        }
        if (demoExit) {
            System.out.printf("DEMO_RESULT won=%s seconds=%d guesses=%d clicks=%d steps=%d%n",
                    game.isWon(), game.elapsedSeconds(), auto.guesses(), auto.clicks(), auto.steps());
            System.out.flush();
            dispose();
            System.exit(0);
        }
    }

    private void tick() {
        if (game == null) return;
        timeLed.setValue(game.elapsedSeconds());
        mineLed.setValue(game.minesLeft());
    }

    private void updateFace() {
        if (game == null) return;
        if (game.isWon()) faceBtn.setKind(UiTheme.Face.WIN);
        else if (game.isExploded()) faceBtn.setKind(UiTheme.Face.DEAD);
        else if (auto.isRunning()) faceBtn.setKind(UiTheme.Face.SURPRISED);
        else faceBtn.setKind(UiTheme.Face.SMILE);
    }

    private void customDialog() {
        JSpinner w = new JSpinner(new SpinnerNumberModel(Math.max(5, diff.cols()), 5, 60, 1));
        JSpinner h = new JSpinner(new SpinnerNumberModel(Math.max(5, diff.rows()), 5, 40, 1));
        JSpinner m = new JSpinner(new SpinnerNumberModel(Math.max(1, diff.mines()), 1, 9999, 1));
        JPanel p = new JPanel(new GridLayout(3, 2, 8, 8));
        p.add(new JLabel("宽度（列）："));
        p.add(w);
        p.add(new JLabel("高度（行）："));
        p.add(h);
        p.add(new JLabel("雷数："));
        p.add(m);
        int ok = JOptionPane.showConfirmDialog(this, p, "自定义雷区",
                JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE);
        if (ok != JOptionPane.OK_OPTION) return;
        GameModel.Difficulty d = GameModel.Difficulty.custom(
                (Integer) w.getValue(), (Integer) h.getValue(), (Integer) m.getValue());
        newGame(d);
    }

    /** 按棋盘大小调整窗口；必要时缩小格子以适配屏幕。 */
    private void packToFit(boolean center) {
        pack();
        Dimension screen = Toolkit.getDefaultToolkit().getScreenSize();
        int cell = board.cellSize();
        while (cell > 10 && (getWidth() > screen.width - 40 || getHeight() > screen.height - 90)) {
            cell--;
            board.setCellSize(cell);
            pack();
        }
        if (center) setLocationRelativeTo(null);
    }

    /**
     * 演示模式：{@code --auto [beginner|inter|expert]} 启动后先点开中心格生成雷区，
     * 然后立刻开始自动玩（方便一键演示/测试）。
     */
    public void startAutoDemo(String mode, boolean exitWhenDone) {
        this.demoExit = exitWhenDone;
        GameModel.Difficulty d = switch (mode == null ? "beginner" : mode) {
            case "inter", "intermediate" -> GameModel.Difficulty.INTERMEDIATE;
            case "expert" -> GameModel.Difficulty.EXPERT;
            default -> GameModel.Difficulty.BEGINNER;
        };
        newGame(d);
        Timer t = new Timer(400, null);
        t.addActionListener(e -> {
            t.stop();
            int c = d.cols() / 2, r = d.rows() / 2;
            BoardGenerator.GenResult res = BoardGenerator.generate(d, c, r, 900, 2500);
            game.setMineMap(res.mines);
            game.reveal(c, r);
            board.repaint();
            onBoardChanged();
            status.setText(res.perfect() ? " 演示：纯逻辑可解地图" : " 演示：需猜 " + res.guesses + " 次");
            auto.start();
            autoBtn.setText("⏸ 暂停");
        });
        t.setRepeats(false);
        t.start();
    }

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception ignored) {
        }
        final boolean autoDemo = args.length > 0 && args[0].equals("--auto");
        final boolean exitWhenDone = java.util.Arrays.asList(args).contains("--exit");
        final String mode = args.length > 1 ? args[1] : "beginner";
        SwingUtilities.invokeLater(() -> {
            MainFrame f = new MainFrame();
            f.setVisible(true);
            if (autoDemo) f.startAutoDemo(mode, exitWhenDone);
        });
    }
}
