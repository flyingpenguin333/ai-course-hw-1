# 围棋框架（参考资料）

> **说明**：这是课程提供的围棋 AI 框架代码，仅作为参考。
>
> 本项目选择的是**题目二（中国象棋）**，围棋框架代码保留在此供学习和对比参考。

---

## 文件说明

### 围棋规则引擎 (`dlgo_*.py`)

- `dlgo_init.py` — 模块导出
- `dlgo_gotypes.py` — Player, Point 等基础类型
- `dlgo_goboard.py` — Board, GameState, Move 核心逻辑
- `dlgo_scoring.py` — 计分系统
- `dlgo_zobrist.py` — Zobrist 哈希表

### 围棋 AI 智能体 (`go_*_agent.py`)

- `go_random_agent.py` — 随机 AI
- `go_mcts_agent.py` — MCTS AI
- `go_minimax_agent.py` — Minimax AI

### 围棋对弈脚本

- `play_go.py` — 围棋命令行对弈脚本

---

## 与象棋实现的对比

| 特性 | 围棋框架 | 象棋实现 |
|------|---------|---------|
| 棋盘大小 | 5×5 (可扩展) | 9×10 (固定) |
| 坐标系统 | 1-indexed | 0-indexed |
| 走法 | 单点落子 | 起点→终点 |
| 游戏结束 | 双方连续 pass | 将/帅被吃 或 困毙 |
| 评估函数 | 领地计算 | 子力+位置 |

---

## 学习价值

虽然本项目选择的是象棋，但围棋框架中的一些设计思想值得借鉴：

1. **不可变状态设计**：`GameState.apply_move()` 返回新状态，避免修改原状态
2. **Zobrist 哈希**：用于局面重复检测（劫判定）
3. **MCTS 四步骤**：选择、扩展、模拟、反向传播

---

## 来源

课程提供的围棋 AI 框架，原仓库：
https://github.com/zhenqis123/ai-course-hw1
