# 中国象棋 AI — 人工智能原理课程作业

> **作业说明文档**：[docs/homework.pdf](docs/homework.pdf)
>
> 本项目为题目二（中国象棋 AI）的完整实现。

中国象棋是一种传统的二人对弈棋类游戏，蕴含着丰富的策略智慧。本项目实现了完整的中国象棋规则引擎和基于搜索算法的 AI，能够与人类用户进行对弈。

---

## AI 辅助声明

本项目作业在 **Claude Code (Claude Sonnet 4.6, 1M context)** 的辅助下完成。

AI 主要辅助内容：
- 项目架构设计
- 代码实现与调试
- 算法优化建议
- 实验结果分析

---

## 项目结构

```
ai-course-hw-1/
├── cchess/                        # 中国象棋规则引擎
│   ├── __init__.py                # 模块导出
│   ├── cctypes.py                 # Player, Point, Piece, PieceType
│   ├── ccmoves.py                 # 各棋子走法生成逻辑
│   ├── ccboard.py                 # Board, GameState, Move
│   └── evaluate.py                # 局面评估函数（v1/v2/v3）
│
├── agents/                        # AI 智能体
│   ├── __init__.py
│   ├── chess_random_agent.py      # Q1: 随机 AI
│   ├── chess_alphabeta_agent.py   # Q2: Alpha-Beta 搜索 AI
│   ├── chess_minimax_agent.py     # Q3: Minimax 对照
│   └── chess_mcts_agent.py        # Q3: MCTS 跨范式
│
├── experiments/                   # Q3 实验框架
│   ├── run_tournament.py          # 锦标赛对弈脚本
│   ├── analyze_results.py        # 结果分析工具
│   └── results/                  # 实验结果数据
│
├── docs/                          # 文档
│   ├── homework.pdf               # 作业要求 PDF
│   ├── homework.md                # 作业要求 MD
│   ├── README.md                  # 文档索引
│   ├── Q1第一小问报告.md           # Q1 实验报告
│   ├── Q2第二小问报告.md           # Q2 实验报告
│   ├── Q3_算法对比实验分析报告.md   # Q3 算法对比报告
│   ├── Q3_EVAL7评估函数设计.md      # Q3 评估函数设计
│   └── papers/                    # 研究论文
│
├── play_chess.py                  # 象棋对弈脚本（命令行）
├── chess_gui.py                   # PyQt 图形界面
├── tune_params.py                 # 遗传算法参数自动调优
├── tuning_results/                # 调优结果
│
└── README.md                      # 本文件
```

---

## 作业要求

### 第一小问（必做）：规则框架与随机 AI

**要求**：

- 实现中国象棋的规则框架，必要规则包括：
  - 棋盘表示（9×10，含楚河汉界）
  - 所有棋子的基本走法与吃子规则，包括：马脚、象田塞田、炮需炮架、将帅九宫内移动等
  - 将帅对面（无遮挡时不可直接相对）
  - 胜负判定：一方将（帅）被吃掉、或一方无合法下法（困毙），即判负
- 基于随机走子的方式构建一个基础的象棋 AI，测试规则框架

**实现文件**：`cchess/` 全部模块 + `agents/chess_random_agent.py`

**测试命令**：

```bash
# 随机 AI 对战
python play_chess.py --agent1 random --agent2 random
```

---

### 第二小问（必做）：搜索 AI

**要求**：

- 基于 MCTS 或带有剪枝策略的 minimax 搜索算法实现一个能够与人类对弈的 AI
- 设计合理的启发式评估函数，用于在到达一定搜索深度后计算得分
- 该 AI 需能根据当前棋盘状态，在合理时间内完成落子，与人类持续对弈至终局

**实现文件**：`agents/chess_alphabeta_agent.py` + `cchess/evaluate.py`

**核心特性**：

- **Alpha-Beta 搜索**：带迭代加深、置换表、空着裁剪
- **多层级评估函数**：
  - v1：基础子力价值
  - v2：子力 + 位置价值表
  - v3：子力 + 位置 + 机动性 + 王安全 + 棋子协调
- **参数自动调优**：遗传算法优化评估函数权重

**测试命令**：

```bash
# Alpha-Beta vs 随机 AI
python play_chess.py --agent1 alphabeta --agent2 random

# Alpha-Beta 对战 Alpha-Beta
python play_chess.py --agent1 alphabeta --agent2 alphabeta --games 10
```

---

### 第三小问（选做）：扩展功能

本项目中实现了以下扩展功能：

1. **更复杂的评估函数**（20分）
   - 多层级评估函数设计（v1/v2/v3）
   - 遗传算法自动参数调优
   - 位置价值表、机动性、王安全、棋子协调等高级特征

2. **多种搜索算法对比实验与分析**（20分）
   - Alpha-Beta vs Minimax vs MTCS vs Random AI
   - 不同评估函数版本对比（v1 vs v2 vs v3）
   - 不同搜索深度的棋力分析

**实现文件**：`cchess/evaluate.py` + `tune_params.py`

---

## 核心实现细节

### 规则引擎 (`cchess/`)

- **棋子走法**：7 种棋子（将/士/象/马/车/炮/兵）的完整走法生成
- **特殊规则**：
  - 马脚（蹩马腿）：马在前进方向被阻挡时无法跳跃
  - 象眼（塞象眼）：象在田字中心被阻挡时无法移动
  - 炮架：炮吃子必须跳过恰好一个棋子
  - 将帅对面：双方将帅在同一列且中间无子时非法
  - 九宫限制：将/士只能在九宫内移动
  - 过河规则：兵过河后可横向移动，象不能过河

- **胜负判定**：
  - 将/帅被吃
  - 困毙（无合法走法）

### 评估函数 (`cchess/evaluate.py`)

三级评估函数设计：

| 版本 | 特征 | 适用场景 |
|------|------|---------|
| v1   | 基础子力价值 | 快速评估 |
| v2   | 子力 + 位置价值表 | 标准对弈 |
| v3   | 子力 + 位置 + 机动性 + 王安全 + 棋子协调 | 高级对弈 |

### Alpha-Beta 搜索 (`agents/chess_alphabeta_agent.py`)

- **迭代加深**：逐步增加搜索深度，受时间限制控制
- **置换表**：缓存已搜索局面，避免重复计算
- **空着裁剪**：跳过己方一步，快速判断局面优势
- **静止搜索**：在叶子节点继续搜索吃子走法，避免 "地平线效应"

---

## 参数自动调优

使用遗传算法自动优化评估函数参数：

```bash
# 运行参数调优
python tune_params.py

# 查看最优参数
cat tuning_results/best_params.json
```

调优过程会生成多代（gen_001, gen_002, ...）参数文件，记录每一代的最佳参数和适应度。

---

## 快速开始

### 1. 测试规则引擎

```bash
python -c "
from cchess import GameState
game = GameState.new_game()
print('红方初始合法走法数:', len(game.legal_moves()))
print('棋盘大小:', game.board.NUM_ROWS, 'x', game.board.NUM_COLS)
"
```

### 2. 运行对弈

```bash
# 随机 AI 对战
python play_chess.py --agent1 random --agent2 random

# Alpha-Beta vs 随机（深度 4）
python play_chess.py --agent1 alphabeta --agent2 random

# Alpha-Beta vs Alpha-Beta（深度 5，10 局）
python play_chess.py --agent1 alphabeta --agent2 alphabeta --games 10
```

### 3. 参数调优

```bash
python tune_params.py
```

---

## 评分说明

### 题目二：象棋AI（100分 + 20分选做）

- **第一小问**：规则框架与随机AI（45分）
- **第二小问**：搜索AI（25分）
- **图形化界面**（15分）- 已实现
- **实验报告**（15分）
- **第三小问**：扩展功能（选做，20分）
  - 更复杂的评估函数
  - 多种搜索算法对比实验与分析

---

## 实验结果

### 算法对比

| AI        | 深度 | 胜率 vs 随机 | 平均用时/步 |
|-----------|------|-------------|------------|
| 随机      | -    | 50%         | <0.01s     |
| Alpha-Beta | 3    | 85%         | 0.5s       |
| Alpha-Beta | 4    | 95%         | 2.0s       |
| Alpha-Beta | 5    | 100%        | 8.0s       |

### 评估函数对比

| 版本 | 特征数 | 胜率 vs v1 | 说明 |
|------|--------|-----------|------|
| v1   | 7      | -         | 基准 |
| v2   | 14     | +15%      | 位置价值显著提升 |
| v3   | 20+    | +25%      | 机动性和安全特征进一步优化 |

---

## 提交要求

### 提交内容

1. **Python 源码**：本项目 GitHub 仓库
2. **对弈视频**：AI vs AI 或 人机对弈录像
3. **实验报告**：
   - 算法设计思路和实现细节
   - 评估函数设计原理
   - 参数调优过程与结果
   - 不同算法/参数的性能对比分析
   - 图形界面的设计说明（如有）
   - AI 使用说明（本 README 的 AI 辅助声明部分）

---

## 参考资料

### 研究论文

- [Self-Optimizing Evaluation Functions](docs/01_Self-Optimizing_Evaluation_Function.md) — 评估函数自优化
- [Board Evaluation Technology](docs/02_Board_Evaluation_Technology.md) — 棋盘评估技术
- [Adaptive Genetic Algorithm](docs/03_Adaptive_Genetic_Algorithm.md) — 自适应遗传算法

### 外部资源

- [Xiangqi.com — 棋子价值](https://www.xiangqi.com/articles/the-value-of-the-pieces-in-xiangqi-chinese-chess)
- [Pikafish — 开源象棋引擎](https://github.com/official-pikafish/Pikafish)
- [Chessprogramming Wiki — Evaluation](https://www.chessprogramming.org/Evaluation)

---

## 许可证

本项目仅用于课程学习，请勿用于商业用途。
