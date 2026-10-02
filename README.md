# 扫雷 Minesweeper

> 用 Java / Swing 写的经典扫雷：**能生成"逻辑可解"的地图**（避开经典扫雷那种必须靠猜的死局），
> **内置自动玩求解器**，并保留了经典手感（首点安全、chord 展开、七段数码管、笑脸重开）。

[![build](https://github.com/guazyk550/minesweeper/actions/workflows/build.yml/badge.svg)](https://github.com/guazyk550/minesweeper/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Java](https://img.shields.io/badge/Java-8%2B-orange)
![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

---

## 特性

- **经典三难度 + 自定义**：初级 9×9/10、中级 16×16/40、高级 30×16/99；自定义支持列 5–60、行 5–40、任意雷数
- **保证可解**：生成地图后用求解器复核，**必须能纯逻辑推完，不允许出现"没有确定解只能猜"的时刻**
- **自动玩**：内置求解器自动通关，四档速度、可单步、可暂停；会像人一样用 chord 批量展开
- **经典操作**：左键翻开、右键插旗（可选问号标记）、已翻开的数字格上左右键同按（或直接左键点击）chord 展开
- **经典外观**：与经典扫雷逐像素对齐的格子结构、七段数码管、笑脸按钮、错误旗打叉、爆炸格红底
- **整体缩放**：100%（经典 16px）/ 125%（默认）/ 150% / 200%
- **零第三方依赖**：只用 JDK 自带的 Swing，编译产物是一个约 50 KB 的 jar

## 截图

高级 30×16，自动玩通关（剩余雷数 000，笑脸戴墨镜）：

![高级自动通关](scaled_expert.png)

初级 9×9，窗口宽度贴合棋盘：

![初级](scaled_beginner.png)

格子结构与本机经典 `saolei.exe` 的逐像素对比（左：经典 / 右：本项目）：

![网格对比](compare.png)

## 快速开始

### 方式一：下载现成的（推荐，**不需要装 Java**）

到 [Releases](https://github.com/guazyk550/minesweeper/releases/latest) 下载任意一个：

| 下载 | 说明 |
|---|---|
| `Minesweeper-1.1.0.exe` | **Windows 安装程序**（约 32 MB，自带精简 JRE）。双击安装，自动创建开始菜单项和桌面快捷方式，装完直接玩 |
| `Minesweeper-1.1.0-portable.zip` | **免安装绿色版**（约 30 MB）。解压到任意目录，双击里面的 `Minesweeper.exe` 即可 |
| `minesweeper.jar` | 只要 jar（约 48 KB），需要本机有 JDK 8+ |

> 前两个都**自带了精简过的 Java 运行时**，所以目标机器完全不用装 JDK。

### 方式二：自己编译

需要 **JDK 8 或更高**（开发环境为 JDK 24）。

```bash
# 1. 编译打包（Windows 双击 build.bat 亦可）
javac -encoding UTF-8 -d out src/minesweeper/*.java
jar --create --file minesweeper.jar --main-class minesweeper.MainFrame -C out .

# 2. 运行（Windows 双击 run.bat 亦可）
java -jar minesweeper.jar
```

一键演示（自动开始并自动通关）：

```bash
java -jar minesweeper.jar --auto beginner      # 初级
java -jar minesweeper.jar --auto inter         # 中级
java -jar minesweeper.jar --auto expert        # 高级
java -jar minesweeper.jar --auto expert --exit # 通关后打印成绩并退出（便于 CI/脚本）
```

## 玩法

| 操作 | 效果 |
|---|---|
| 左键 | 翻开格子 |
| 右键 | 插旗 / 取消（开启问号标记时为 旗 → ? → 空） |
| 已翻开的数字格上左右键同按，或直接左键点击它 | chord：一次展开相邻的安全格 |
| 点笑脸 / F2 | 重开一局 |
| 菜单「视图」 | 缩放 100% / 125% / 150% / 200% |
| 菜单「自动」 | 开始暂停、单步、速度、重置统计 |

## 配套：外部自动玩机器人（`autoplay/`）

本仓库还带一个**独立于游戏本体**的自动玩机器人：它靠**截图识别棋盘 + 模拟鼠标点击**
来玩桌面上的扫雷，所以不只能玩本项目的 Java 版，也能玩经典的 `saolei.exe`。

```
autoplay/扫雷自动玩.bat    ← 双击启动（需要 Python + numpy + Pillow）
autoplay/autoplay.py       ← 启动器：自动找窗口、报盘面、实时日志
autoplay/build_exe.ps1     ← 打包成独立 exe（内置 Python，目标机器什么都不用装）
```

用法：

```powershell
python autoplay.py --games 3      # 连玩 3 局
python autoplay.py --new          # 先重开一局
python autoplay.py --list         # 只列出识别到的扫雷窗口
```

它能自动认出三种启动方式（`saolei.exe` / `Minesweeper.exe` / `java -jar`），
自适应 16px 和 20px 格子、任意行列数，并自己读数码管拿雷数。
运行期间只在控制台输出，**不会往磁盘写任何文件**。

有趣的是：**它和本项目的求解器是同源的**（`autoplay/solver.py` 是 `Solver.java` 的 Python 版），
只不过一个直接读内存里的游戏模型，另一个得靠眼睛看屏幕。

详细原理与踩过的坑见 [`autoplay/README.md`](autoplay/README.md)。

## 为什么不会出现"必猜死局"

先看随机布雷的实际情况（本项目对 1000 张纯随机地图抽样 12 张的实测）：

| 难度 | 随机地图中「纯逻辑可解」的比例 |
|---|---|
| 初级 9×9/10 | 12/12 |
| 中级 16×16/40 | 9/12 |
| **高级 30×16/99** | **仅 1/12 ≈ 8%** |

也就是说，**经典高级扫雷里九成以上的局面都得起猜**，猜错就输。

本项目的做法是「随机布雷 → 用求解器完整复推一遍 → 只要出现『没有任何确定安全格』的时刻就整张作废重来」，
直到找到一张纯逻辑可解的地图（高级平均试 3–8 次，几百毫秒，在后台线程生成，不卡界面）。
如果超出时间上限仍找不到，就退而选「需要猜的次数最少」的那张，并在状态栏如实告知。

菜单里的 **保证可解** 可以关掉，回到经典那种纯随机模式。

## 自动玩

求解器直接读游戏内部模型（不像外部机器人那样靠截图识别），所以信息完整、零识别误差：

- 有确定结论 → 该插旗的插旗、该翻的翻，并且**优先用 chord 一次展开多个**
- 实在没有确定解 → 挑「踩雷概率最低」的格子去猜，并记录猜测次数

实测（`java -jar minesweeper.jar --auto <难度> --exit`）：

| 难度 | 结果 | 猜测次数 |
|---|---|---|
| 初级 | 通关 | 0 |
| 中级 | 通关 | 0 |
| 高级 | 通关 | 0 |

`HeadlessTest` 的批量测试同样是三种难度各 5 局、**15/15 通关、0 次猜测**。

## 求解器

三级推理，逐步加深：

1. **约束传播** —— 每个已翻开数字格周围「还缺几颗雷」：缺 0 颗则候选格全安全，缺满则全是雷
2. **子集差分** —— 约束 A 的候选集是 B 的子集时，差集的雷数 = `needB − needA`
3. **连通分量枚举 + 全局雷数约束** —— 把前沿按约束连通性分块，枚举所有合法解，
   再用「全场还剩 R 颗雷」做多项式 DP 加权，得到每格是雷的**精确概率**（也覆盖远离前沿的格子）

枚举得到的「概率 0 / 概率 1」同样算确定结论，所以自动玩报出的「猜测 0 次」是真的没猜。

## 项目结构

```
src/minesweeper/
  Solver.java          三级求解器（约束传播 / 子集差分 / 分量枚举 + 全局雷数概率）
  GameModel.java       一局游戏：棋盘、翻开/插旗/chord、连锁展开、计时、胜负
  BoardGenerator.java  雷区生成 + "纯逻辑可解"复核
  AutoPlayer.java      自动玩：后台线程「求解 → 执行」，优先 chord 批量展开
  MainFrame.java       主窗口：菜单、LED 面板、笑脸、棋盘、控制条、缩放
  BoardPanel.java      棋盘绘制与鼠标交互
  LedCounter.java      七段数码管（剩余雷数 / 秒表）
  FaceButton.java      笑脸按钮（普通 / 惊讶 / X 眼 / 墨镜）
  UiTheme.java         经典配色与绘制（3D 边框、网格线、旗子、地雷、笑脸）
  GenTest.java         生成器与求解器自测
  HeadlessTest.java    无界面自动通关测试
tools/shot_any.py      按窗口标题截图（开发调试用）
build.bat / run.bat    Windows 一键编译 / 运行
```

## 开发与测试

```bash
# 编译
javac -encoding UTF-8 -d out src/minesweeper/*.java

# 生成器 + 求解器自测（随机地图可解率、生成耗时）
java -cp out minesweeper.GenTest

# 无界面自动通关测试（三难度各 5 局）
java -cp out minesweeper.HeadlessTest
```

### 打包 Windows 安装程序 / 免安装版

需要 JDK 14+（用到自带的 `jpackage`）和 **WiX Toolset v3**（生成 exe 安装程序用）：

```powershell
winget install WiXToolset.WiXToolset
powershell -ExecutionPolicy Bypass -File packaging\build-installer.ps1 -Version 1.1.0
# 产物：build\packaging\dist\Minesweeper-1.1.0.exe 和 Minesweeper-1.1.0-portable.zip
```

脚本会自动 `jlink` 出一个精简运行时（约 30 MB）打进产物，所以最终用户不需要装 Java。
应用图标由 `packaging/make_icon.py` 生成（PIL 画的未翻开格子 + 地雷）。

## Roadmap

- [ ] 各难度最佳成绩排行榜与配置文件
- [ ] 展开波浪动画、踩雷闪光、音效
- [ ] 提示按钮（标出逻辑上可推的下一步）、撤销/重做
- [ ] 用 `jpackage` 打成免 JDK 的独立安装包
- [ ] 英文界面

## 贡献

欢迎提 Issue 和 PR。改动前建议先跑一遍 `GenTest` 和 `HeadlessTest`，确保求解器与自动玩没有被改坏。

## 许可证

[MIT](LICENSE) © 2026 guazyk550
