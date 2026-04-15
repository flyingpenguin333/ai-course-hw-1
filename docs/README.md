# PDF 文献提取完整索引

## 文件列表

本目录包含从4篇学术论文PDF中完整提取的Markdown格式文档，适合AI阅读和处理。

### 1. PDF01_Self-Optimizing_Evaluation_Function.md
**标题:** Self-Optimizing Evaluation Function for Chinese-Chess

**作者:** Xiangran Du, Min Zhang, Xizhao Wang

**来源:** International Journal of Hybrid Information Technology, Vol. 7, No. 4 (2014), pp.163-172

**核心研究:**
- 粒子群优化(PSO)算法应用于中国象棋评估函数优化
- 自对弈训练方法
- 地位控制在评估函数中的重要性研究

**关键成果:**
- PSO有效优化参数，программе棋力显著提升
- 简化评估函数（无地位控制）反而性能更优
- 自动优化克服人工调参的主观性

---

### 2. PDF02_Board_Evaluation_Technology.md
**标题:** Research on Technology of Board Evaluation in Chinese Chess Computer Game
**中文标题:** 中国象棋计算机博弈局面评估技术研究

**作者:** 黄鸿, 林健, 任雪梅 (Beijing Institute of Technology)

**核心研究:**
- 局面评估方法的四分类体系：
  - 静态单子型
  - 未来局势型
  - 象棋知识型
  - 局面附加信息
- 评估方法与其他模块(博弈树搜索、着法生成、知识库)的关系
- 参数优化方法(爬山法、模拟退火、遗传算法、神经网络)

**关键技术:**
- 子力强度计算
- 位置价值评估
- 棋子灵活度/机动性
- 棋盘控制力
- 棋子配合打法识别
- 定"形"与定"势"判断

---

### 3. PDF03_Adaptive_Genetic_Algorithm.md
**标题:** Implementation of Adaptive Genetic Algorithm of Evaluation Function in Chinese Chess Computer Game System

**作者:** 王骄, 王涛, 罗燕红, 许心和 (Northeastern University)

**来源:** Journal of Northeastern University (Natural Science), Vol. 26, No. 10 (2005), pp.949-952

**核心研究:**
- 自适应遗传算法(AGA)用于评估函数参数优化
- 改进的锦标赛选择机制
- 均匀交叉和自适应变异
- 动态交叉率(Pc)和变异率(Pm)调整

**创新点:**
- AGA自动调整Pc和Pm，避免手工设定问题
- 改进的锦标赛选择节省50%计算时间
- 参数自学习能力强

**实验结果:**
- 600代训练达到约75%胜率
- 自动优化参数优于手工调参
- 参数值符合象棋知识规律

---

### 4. PDF04_Comparison_Training.md
**标题:** Comparison Training for Computer Chinese Chess

**作者:** Wen-Jie Tseng, Jr-Chang Chen, I-Chen Wu, Tinghan Wei

**机构:** National Chiao Tung University, National Taipei University

**核心研究:**
- 比对训练(Comparison Training)用于自动调整评估函数权重
- N元组网络(n-tuple network)特征提取
- 分级评估(Tapered Eval)与比对训练结合
- 批量训练和并行化处理

**主要特征类型:**
1. 单个棋子特征(MATL, LOC, MOB)
2. 王的安全特征(AKA, SPC)
3. 棋子关系特征(COP, MATL2, LOC2)

**实验成果:**
- 自动调优权重相比手工调参胜率提升86.58%
- 加入N元组特征(尤其是LOC2)性能显著提升
- EVAL13版本达81.65%胜率改进
- 批量训练实现2.87-3.7倍的并行加速

---

## 文档特点

✓ **完整原文提取** - 保留论文的原始结构和内容  
✓ **Markdown格式** - 便于AI处理和阅读  
✓ **保留所有核心内容** - 包含摘要、引言、方法、实验、结论、参考文献  
✓ **数学公式** - 使用LaTeX格式呈现  
✓ **表格和组织结构** - 清晰的层级结构  

## 使用建议

1. **快速了解** - 阅读各文档的摘要和结论部分
2. **深入研究** - 查看完整内容、公式推导和实验细节
3. **交叉参考** - 这些文献相互关联，形成完整的研究脉络
4. **AI处理** - 可直接利用Markdown格式进行自然语言处理

---

**提取完成时间:** 2026年4月15日  
**总共提取:** 4篇学术论文  
**格式:** Markdown (AI友好)  
**字数估算:** 约80,000字以上
