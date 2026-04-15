# Implementation of Adaptive Genetic Algorithm of Evaluation Function in Chinese Chess Computer Game System

**Authors:** WANG Jiao, WANG Tao, LUO Yan-hong, XU Xin-he

**School of Information Science & Engineering, Northeastern University, Shenyang 110004, China**

**Corresponding Author:** WANG Jiao
**Email:** soldierj@sina.com

**Source:** Journal of Northeastern University (Natural Science), Vol. 26, No. 10 (2005), pp.949-952

---

## Abstract

Adaptive Genetic Algorithm (AGA) is used to solve the problem of chinese chess game on computer. The game system is divided into four parts: searching engine, evaluation function and opening book. Then the AGA is brought into evaluation function to automatically adjust and optimize the parameters' combination of evaluation function by tournament algorithm. Based on the above methods, an off-time self-study system is designed. The experiment results show that the AGA improves the performance of the program developed.

**Key words:** Chinese chess computer game; game tree; evaluation function; tournament algorithm; adaptive genetic algorithm

---

## 1 Introduction

The game is a classical problem to artificial intelligence and machine learning. Chinese chess is one of the most widely played board games with the history more than more than 1500 years. The methods of computer chess and shogi are all used successfully in the computer Chinese chess system. There existes an extensive literature on computer games for different games particularly.

Evaluation function is the fundamental technology of game system. The game system consists of moving generation, searching algorithms and evaluation function. Among them, evaluation function assesses the current state of chess and reflects if the situation is favorable for us or not. In order to improve the play strength of machine, we put evaluation function as our optimize objective.

Most prior researches about evaluation function have relied on manual tuning or ad-hoc feature engineering. However, since the feature set is often large and feature interactions are complex, hand-tuned approaches may not be optimal. In this paper, we present the methods of Adaptive Genetic Algorithm (AGA) to optimize evaluation parameters of Chinese chess. The rest of this paper is organized as follows: In Section 2, we discuss the basic concepts of genetic algorithm and tournament method. In Section 3, we introduce the adaptive genetic algorithm. In Section 4, we perform experiment to verify the effectiveness of the method.

---

## 2 Genetic Algorithm

### 2.1 Basic Concept of Genetic Algorithm

Genetic algorithm (GA) is proposed by Holland. GA is a stochastic search method based on the mechanism of natural selection and natural genetics whose aim is to find the best solution of a given problem. Each individual in a population represents a potential solution to the given problem. After each generation via reproduction, crossover, and mutation, individuals with higher fitness will remain and individuals with lower fitness will be discarded.

The population size and parameters of the algorithm should be carefully chosen, and the learning procedure must obey Holland's "fitness" function to make clear whether a solution is "good" or "bad" in a given problem.

### 2.2 Fitness Function

In our experiment, the fitness function is defined as the win rate of the Chinese chess game:

$$\text{fitness} = \frac{\text{number of wins}}{\text{number of total games}}$$

Each particle in a population represents a set of weights (parameters) in an evaluation function. The evaluation function is used to evaluate chess positions and guide the game tree search. The fitness function evaluates how well a set of weights plays Chinese chess by competition among individuals in the population: the standard procedure is simply to simulate games against other candidates.

---

## 3 Tournament Selection and Genetic Operations

### 3.1 Tournament Selection

Standard tournament selection is time-consuming. We propose an improved tournament selection method to improve the efficiency.

The improved algorithm:

1. Divide the population containing N individuals randomly into M groups
2. Perform tournament training within each group
3. The champion of each group is selected as the best
4. Perform crossover and mutation on M champions to generate 100 new individuals
5. Fill the population with the new individuals to form a new generation

This modified method saves approximately 50% of the computation time compared to standard tournament.

### 3.2 Uniform Crossover

The crossover points are set at parameter intervals.

Based on crossover rate Pc, generate a binary mask of equal length to the number of parameters. The segments in the mask indicate which parent individual provides variables to the offspring. The offspring are determined through the mask and parent individuals.

### 3.3 Mutation

Mutation performs gene flipping with a probability equal to mutation rate Pm:

```
if random() < Pm:
    gene[i] = flip(gene[i])  // binary flip
```

Mutation preserves population diversity and prevents premature convergence.

---

## 4 Adaptive Genetic Algorithm

### 4.1 Need for Adaptive Parameter Control

In traditional GA, Pc (crossover rate) and Pm (mutation rate) are fixed parameters. However:

- If Pc is too large: offspring are generated quickly, but high-fitness individual structures are easily destroyed
- If Pc is too small: search is slow or stagnates
- If Pm is too small: difficult to create new structures
- If Pm is too large: becomes pure random search

Currently there is no universal method to determine optimal Pc and Pm at once. Different problems require different parameter settings obtained through experimental tuning.

### 4.2 Adaptive Strategy

The adaptive parameters are calculated as follows:

$$P_c(t) = \begin{cases}
p_{c1} - \frac{(p_{c1}-p_{c2})(f'-f_{avg})}{f_{max}-f_{avg}}, & \text{if } f' \geq f_{avg} \\
p_{c1}, & \text{if } f' < f_{avg}
\end{cases}$$

$$P_m(t) = \begin{cases}
p_{m1} - \frac{(p_{m1}-p_{m2})(f_{max}-f')}{f_{max}-f_{avg}}, & \text{if } f' \geq f_{max} \\
p_{m1}, & \text{if } f' < f_{max}
\end{cases}$$

where:
- $p_{c1} = 0.9, p_{c2} = 0.6$
- $p_{m1} = 0.1, p_{m2} = 0.001$
- $f_{max}$: maximum fitness in population
- $f_{avg}$: average fitness in population
- $f'$: fitness of the individual to be crossover (or mutation)

**Advantages:**
- Pc and Pm automatically adjust based on fitness changes
- Maintains population diversity while ensuring convergence
- Provides optimal Pc and Pm relative to a specific solution

---

## 5 Experimental Results

### 5.1 Test Experimental Design

Composition:
- Champions from generations 100, 200, 300, 400, 500, 600
- Two random players

Method: Round-robin tournament
- Each pair plays two games with exchanged move order
- Winner gains +1 point, loser gains -1 point

### 5.2 Training Results (at generation 600)

| Piece Parameters | Car | Horse | Cannon | Guard | Elephant | Pawn |
|------------------|-----|-------|--------|-------|----------|------|
| Trained Values   | 989 | 439   | 442    | 226   | 210      | 55   |

**Characteristics:**
- Piece values rank according to human experience
- Car value ≈ Horse + Cannon values
- Horse value ≈ Cannon value ≈ Elephant + Guard values

### 5.3 Performance Analysis

The performance curve shows:

**Phase 1 (Generations 0-100):**
- Low learning efficiency
- Win rate between 0% and 15%

**Phase 2 (Generations 100-300):**
- Performance climbing phase
- Win rate: 15% to 55%

**Phase 3 (Generations 300-600):**
- Exponential growth phase
- Win rate: stabilizes around 55%-75%

### 5.4 Comparative Results

**Hand-tuned vs Automatically Optimized:**
- The automatically optimized parameters show superior performance
- AGA successfully avoids manual bias in parameter selection
- Training quality improves with generation number

---

## 6 Convergence Characteristics

### 6.1 Learning Curve Analysis

The learning curve exhibits:
- Initial zigzag pattern (non-monotonic)
- Clear improvement after generation 220
- Convergence around generation 300 with win rate stabilizing at ~65%

### 6.2 Parameter Evolution

| Generation | Pc Range | Pm Range | Characteristics |
|------------|----------|----------|-----------------|
| Early     | High (0.8-0.9) | Low (0.01) | Fast exploration |
| Middle    | Medium (0.6-0.8) | Medium (0.05) | Balanced phase |
| Late      | Low (0.4-0.6) | High (0.1) | Convergence tuning |

---

## 7 Comparison with Other Optimization Methods

| Method | Advantages | Disadvantages | Suitability for Chinese Chess |
|--------|------------|---------------|-----------------------------| 
| Genetic Algorithm (GA) | Global search, fast convergence | Difficult to choose Pc/Pm | High |
| Adaptive GA (AGA) | Automatic parameter adjustment | Slightly higher complexity | Very High |
| Simulated Annealing | Escapes local optima | Slow speed | Medium |
| Neural Networks | Strong self-learning | Requires many resources | Medium |
| Particle Swarm Optimization | Relatively simple | Parameters need manual setting | Medium |

---

## 8 Implementation Recommendations

1. **Initialization:** Initialize parameters based on domain knowledge, such as piece values
2. **Population Size:** 20-30 individuals provide good balance
3. **Number of Iterations:** Typically 300-600 generations to see significant improvement
4. **Self-play Depth:** Depth 4-5 search for effective evaluation
5. **Convergence Criterion:** Stop if no improvement for 50+ consecutive generations

---

## 9 Summary

Adaptive Genetic Algorithm provides an effective method for automatic optimization of evaluation function parameters in Chinese chess computer game systems. The method:

- Eliminates manual parameter tuning bias
- Automatically adjusts Pc and Pm based on fitness landscape
- Achieves significant performance improvements over hand-tuned systems
- Incorporates domain knowledge through proper initialization
- Maintains population diversity while ensuring convergence

The experimental results demonstrate that AGA can improve the playing strength of Chinese chess programs effectively and significantly reduce the manual tuning effort required.

---

## References

[1] Yen, S.J., Chen, J.C., Yang, T.N. Computer Chinese chess. ICGA Journal 2004; 3:3-18.

[2] PC游戏编程. 重庆: 重庆大学出版社, 2002.

[3] Marsland, T.A. Computer chess and search. Encyclopedia of AI. Edmonton: University of Alberta 1991.

[4] Hsu, S.C., Tsao, K.M. Design and implementation of an opening game knowledge-base system for computer Chinese chess. R. Bulletin of the College of Engineering, N.T.U 1991; 53: 75-86.

[5] Lorenz, D., Markovitch, S. Derivative evaluation function learning using genetic operators. A. Proceedings of the AAAI Fall Symposium on Games: Planning and Learning. C. New Carolina 1993: 106-114.

[6] Holland, J.H. Adaptation in nature and artificial system. M. Ann Arbor: The University of Michigan Press 1975.

[7] 中国象棋计算机博弈. Z. 2000: 20-23. Michalewicz, Z. Genetic algorithm + data structure = evolution programs. M. Beijing: Science Press. 2000: 20-23.

[8] 遗传算法基础理论与应用. M. 北京: 科学出版社, 2002: 1-15. Li, M.Q. Genetic algorithm's base theory and application. M. Beijing: Science Press. 2002: 1-15.

[9] 遗传算法-理论、应用与程序实现. M. 西安 西安交通大学出版社, 2002: 195-210. Wang, X.P., Cao, L.M. Genetic algorithm—theory, application and programming implement. M. Xi'an: Xi'an Jiaotong University Press. 2002: 195-210.

[10] Angeline, J., Pollack, J.B. Competitive environments evolve better solution for complex tasks. A. Proceedings of the Fifth International Conference on Genetic Algorithms. C. Urbana-Champaign 1993: 264-270.

