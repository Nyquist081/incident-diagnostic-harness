# RAG 系统学习指南

这份指南面向已经会基本 Python、了解 LLM 调用方式、希望系统掌握 RAG 和高阶 RAG 工程的人。学习目标不是背概念，而是能独立设计、实现、评估并优化一个可上线的检索增强生成系统。

## 目录

- [学习路径](#学习路径)
- [核心技术原理](#核心技术原理)
- [高阶 RAG 技术图谱](#高阶-rag-技术图谱)
- [工程实践路线](#工程实践路线)
- [优化理论与评估](#优化理论与评估)
- [常见故障与诊断](#常见故障与诊断)
- [推荐论文与资料](#推荐论文与资料)

## 学习路径

### 第一阶段：朴素 RAG

目标：理解 RAG 为什么有效，以及一个最小系统由哪些模块组成。

1. 学会区分模型参数记忆和外部知识库。
2. 掌握文档加载、清洗、切分、向量化、索引、召回、生成的完整链路。
3. 用一个小语料实现问答，并输出引用来源。
4. 观察失败案例：没召回、召回错、上下文太长、模型忽略证据、答案无引用。

交付物：

- 一个本地可运行的 RAG demo。
- 至少 20 条测试问题。
- 每条问题记录 `retrieved_docs`、`answer`、`citations`、`failure_reason`。

### 第二阶段：检索质量优化

目标：把问题从“能跑”推进到“召回稳定、可解释、可诊断”。

1. 学习 sparse retrieval：BM25、关键词召回、字段过滤。
2. 学习 dense retrieval：embedding、向量相似度、ANN 索引。
3. 学习 hybrid retrieval：BM25 + dense fusion。
4. 学习 query rewriting：查询改写、HyDE、多查询扩展。
5. 学习 reranking：cross-encoder、LLM rerank、规则重排。

交付物：

- 检索评估集。
- `Recall@k`、`MRR`、`nDCG` 指标。
- 至少三种检索策略对比。

### 第三阶段：生成质量与可信度

目标：让生成答案严格依赖证据，减少幻觉。

1. 设计证据优先的 prompt：先读证据，再回答，无法支持就拒答。
2. 增加引用约束：每个关键结论绑定 chunk/source id。
3. 做答案校验：claim extraction、claim-to-evidence matching。
4. 引入 answerability 判断：资料不足时明确说明缺口。

交付物：

- 引用完整率评估。
- 幻觉样本集。
- 拒答策略和边界说明。

### 第四阶段：高阶 RAG

目标：处理复杂、多跳、长文档、结构化、实时和跨系统场景。

1. Agentic RAG：让模型决定是否检索、检索什么、何时停止。
2. Self-RAG：检索、生成、批判过程自反思。
3. Corrective RAG：对召回结果做可靠性判定，必要时补检索或改写查询。
4. GraphRAG：抽取实体关系，结合社区摘要和图检索回答全局问题。
5. Multi-hop RAG：拆解问题，多轮检索，合并证据链。
6. Long-context RAG：长上下文不是替代检索，而是改变检索粒度和排序策略。

交付物：

- 一个多跳问题求解流程。
- 一个 GraphRAG 或结构化知识检索原型。
- 一份离线评估报告。

### 第五阶段：生产化

目标：让系统具备监控、回归测试、成本控制和持续迭代能力。

1. 构建数据管道：增量同步、去重、版本化、权限继承。
2. 构建观测：查询日志、召回证据、生成 prompt、模型输出、用户反馈。
3. 构建评测：golden set、LLM-as-judge、人工复核、线上 A/B。
4. 构建安全：权限过滤、提示注入防护、敏感信息脱敏。
5. 构建成本控制：缓存、分层模型、候选裁剪、批量 embedding。

交付物：

- RAG 质量 dashboard。
- 回归评测脚本。
- 生产变更 checklist。

## 核心技术原理

### RAG 的基本公式

RAG 可以抽象为：

```text
documents -> index
question -> retriever -> evidence
question + evidence -> generator -> answer
```

关键变量：

- `D`：知识库文档集合。
- `q`：用户问题。
- `z`：检索到的证据片段。
- `y`：生成答案。

朴素 RAG 通常近似为：

```text
p(y | q) ~= p_llm(y | q, top_k(retrieve(q, D)))
```

工程上最重要的是不要把 RAG 理解成“向量数据库 + prompt”。真正的 RAG 是一个证据选择和证据约束生成系统。

### 文档切分

切分决定了检索系统的最小知识单元。

常见策略：

- 固定 token 窗口：实现简单，容易切断语义。
- 段落/标题切分：语义更自然，长度分布不均。
- 递归切分：按标题、段落、句子逐级拆分。
- 语义切分：基于 embedding 或话题边界切分。
- parent-child chunk：小 chunk 用于召回，大 parent chunk 用于注入上下文。

经验原则：

- 问答型知识库常从 300-800 tokens/chunk 起步。
- 技术文档保留标题层级、路径、版本、代码块语言。
- 法务、医疗、合规类材料要保留条款编号和章节路径。
- chunk overlap 能缓解断句，但过大会增加重复召回和成本。

### Embedding 与相似度

Dense retrieval 通常把文本映射为向量：

```text
v_q = embed(q)
v_d = embed(chunk)
score = cosine(v_q, v_d)
```

注意点：

- embedding 模型决定语义空间，不同模型的向量不可混用。
- 索引重建要记录 embedding model、维度、预处理版本。
- 余弦相似度适合归一化向量；内积和 L2 适合不同索引配置。
- embedding 擅长语义相似，不一定擅长精确编号、错误码、函数名、专有名词。

### Sparse、Dense 与 Hybrid

Sparse retrieval：

- 优点：精确匹配强，解释性好，对 ID、代码、错误码友好。
- 缺点：同义改写、跨语言、概念类问题较弱。

Dense retrieval：

- 优点：语义泛化好。
- 缺点：容易召回“看起来相关但不支持答案”的内容。

Hybrid retrieval：

- 同时取 BM25 和 embedding 候选。
- 用 RRF、线性加权或学习排序融合。
- 再用 reranker 精排。

RRF 公式：

```text
score(d) = sum(1 / (k + rank_i(d)))
```

其中 `rank_i(d)` 是文档 `d` 在第 `i` 个检索器里的排名，`k` 常取 60 左右。

### Reranking

召回阶段追求不要漏，重排阶段追求把真正有用的证据放到前面。

常见 reranker：

- Cross-encoder reranker：输入 `(query, chunk)`，输出相关性分数。
- LLM reranker：让 LLM 判断证据是否支持回答。
- 规则 reranker：基于权限、时间、类型、标题路径、业务优先级调整。

重排时要区分三种相关性：

- topical relevance：主题相关。
- answer relevance：能回答问题。
- evidence support：能支持最终结论。

上线 RAG 更看重后两者。

## 高阶 RAG 技术图谱

### Query Rewriting

适用场景：

- 用户问题过短。
- 问题包含指代。
- 问题需要拆成多个子问题。
- 用户用业务口语问技术材料。

常见方法：

- Rewrite：把问题改写成适合检索的形式。
- Multi-query：生成多个不同角度的查询。
- HyDE：先生成一个假想答案，再用假想答案向量检索。
- Step-back prompting：先抽象出上位问题，再检索背景知识。

风险：

- 改写可能改变用户原意。
- HyDE 可能把模型幻觉注入检索。
- 多查询会提高成本和重复候选。

### Multi-hop RAG

适用场景：

- 问题需要多个事实组合。
- 一跳检索拿不到完整证据。
- 查询依赖上一步结果。

基本流程：

```text
question
-> decompose into sub-questions
-> retrieve evidence for each sub-question
-> resolve entities and conflicts
-> synthesize answer with evidence chain
```

工程要点：

- 保存每一步检索轨迹。
- 对子问题设置停止条件。
- 合并证据时做去重和冲突检测。

### Self-RAG

Self-RAG 的核心思想是让模型学习在生成过程中自我判断：是否需要检索、检索结果是否相关、生成内容是否被证据支持、答案是否有用。

可工程化落地为四个判断器：

- `need_retrieval(q)`：是否需要检索。
- `is_relevant(q, chunk)`：证据是否相关。
- `is_supported(answer_claim, chunk)`：结论是否被支持。
- `is_useful(answer, q)`：答案是否解决问题。

不一定要训练专门模型，也可以先用小模型、规则或 LLM judge 实现。

### Corrective RAG

Corrective RAG 的重点是“检索结果不可靠时如何纠错”。

典型流程：

```text
retrieve -> grade evidence -> if weak: rewrite/search again -> refine knowledge -> answer
```

适用场景：

- 语料质量参差不齐。
- 用户问题容易召回相邻但错误的内容。
- 业务要求不能基于弱证据回答。

关键设计：

- 证据分级：strong、partial、irrelevant、conflicting。
- 弱证据触发补检索。
- 冲突证据触发澄清或输出不确定性。

### GraphRAG

GraphRAG 把文本知识转成实体、关系、社区、摘要等图结构，适合回答“全局性”和“关系性”问题。

典型构件：

- Entity extraction：抽取实体。
- Relation extraction：抽取实体关系。
- Community detection：发现实体社区。
- Community summary：生成社区摘要。
- Local search：围绕实体邻域回答具体问题。
- Global search：基于社区摘要回答全局问题。

适用问题：

- “这个组织的主要风险是什么？”
- “多个事件之间有什么共同根因？”
- “哪些系统模块形成了关键依赖链？”

不适合一开始就上 GraphRAG 的情况：

- 文档规模很小。
- 问题主要是精确事实查找。
- 没有稳定的实体体系。

### Agentic RAG

Agentic RAG 让模型作为控制器，在多个工具之间选择动作：

```text
think -> search docs -> inspect source -> search web/db -> verify -> answer
```

优点：

- 能处理开放问题和多源问题。
- 能动态决定检索深度。
- 能在证据不足时继续查找。

风险：

- 延迟和成本不可控。
- 工具调用错误会累积。
- 需要严格的停止条件、权限控制和审计日志。

## 工程实践路线

### 项目 1：最小 RAG

实现：

- 文档加载。
- 简单分词。
- BM25 检索。
- top-k 上下文拼接。
- 模板化答案生成。

练习代码：[practice/toy_rag.py](practice/toy_rag.py)

运行：

```bash
python rag_learning/practice/toy_rag.py
```

### 项目 2：Hybrid RAG

新增：

- embedding 检索。
- BM25 + dense 融合。
- reranker。
- 元数据过滤。

建议数据集：

- 公司内部 FAQ。
- 产品文档。
- GitHub issue。
- 事故复盘文档。

### 项目 3：可评估 RAG

新增：

- `questions.jsonl`：问题、标准答案、相关文档 id。
- `eval_retrieval.py`：计算 Recall@k、MRR、nDCG。
- `eval_answer.py`：评估答案正确性、引用支持率、拒答合理性。

指标：

- Retrieval：Recall@k、Precision@k、MRR、nDCG。
- Generation：faithfulness、answer correctness、citation precision、citation recall。
- System：latency、cost、cache hit rate、fallback rate。

### 项目 4：高阶 RAG

新增：

- query rewrite。
- corrective retrieval。
- multi-hop planner。
- claim verification。
- trace viewer。

输出每次请求的 trace：

```json
{
  "question": "...",
  "rewritten_queries": ["..."],
  "retrieved": [{"id": "doc-1", "score": 0.83}],
  "reranked": [{"id": "doc-1", "score": 0.91}],
  "claims": [{"text": "...", "supported_by": ["doc-1"]}],
  "answer": "..."
}
```

## 优化理论与评估

### 错误分层

RAG 失败不要只看最终答案，要按链路拆：

1. 数据层：文档缺失、过期、重复、权限错误。
2. 切分层：chunk 太碎、太长、丢标题、丢表格结构。
3. 召回层：top-k 没有相关证据。
4. 排序层：相关证据有但排在后面。
5. 上下文层：证据过多、冲突、顺序不合理。
6. 生成层：模型无视证据、过度推断、引用错误。
7. 产品层：用户问题不清、权限边界不清、反馈闭环缺失。

### 检索指标

Recall@k：

```text
Recall@k = relevant_docs_in_top_k / all_relevant_docs
```

MRR：

```text
MRR = average(1 / rank_of_first_relevant_doc)
```

nDCG：

```text
DCG@k = sum(rel_i / log2(i + 1))
nDCG@k = DCG@k / IDCG@k
```

经验：

- 问答系统优先优化 Recall@k 和 MRR。
- 有多级相关性标注时使用 nDCG。
- top-k 不是越大越好，过大会污染上下文。

### 生成指标

Faithfulness：

- 答案里的关键 claim 是否被证据支持。

Answer correctness：

- 答案是否解决了用户问题。

Citation precision：

- 引用的证据是否真的支持对应句子。

Citation recall：

- 关键结论是否都有引用。

Abstention quality：

- 资料不足时是否正确拒答。

### 优化优先级

通常按这个顺序排查：

1. 语料是否有答案。
2. 相关 chunk 是否能被召回。
3. 相关 chunk 是否排在上下文预算内。
4. prompt 是否强制基于证据回答。
5. 模型是否具备必要推理能力。
6. 是否需要多跳、图结构或工具调用。

不要一开始就调 prompt 或换大模型。大多数 RAG 质量问题首先是数据和检索问题。

## 常见故障与诊断

| 现象 | 可能原因 | 诊断方法 | 修复 |
| --- | --- | --- | --- |
| 答案胡编 | 没召回到证据或 prompt 未约束 | 查看 top-k 和引用 | 增加拒答、claim 校验 |
| 召回看似相关但答不上 | topical relevance 高，evidence support 低 | 标注 chunk 是否直接回答 | rerank 目标改为 answer relevance |
| 错过专有名词/错误码 | dense 对精确匹配弱 | 用关键词搜索对比 | 加 BM25/hybrid |
| 同一问题答案不稳定 | 候选排序抖动或上下文过多 | 固定 seed，记录 trace | 稳定排序、去重、压缩上下文 |
| 引用错误 | 生成阶段引用未绑定证据 | claim-to-citation 检查 | 句级引用和后验校验 |
| 权限泄漏 | 检索前未做 ACL 过滤 | 审计 retrieved docs | query-time permission filter |
| 成本高 | 多查询、rerank、长上下文过度使用 | 分析 token 和调用日志 | 缓存、分层模型、早停 |

## 推荐论文与资料

基础：

- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, Lewis et al., 2020: https://arxiv.org/abs/2005.11401
- Retrieval-Augmented Generation for Large Language Models: A Survey, Gao et al., 2023: https://arxiv.org/abs/2312.10997
- Retrieval-Augmented Generation for Natural Language Processing: A Survey, 2024: https://arxiv.org/abs/2407.13193

高阶：

- Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection, Asai et al., 2023: https://openreview.net/forum?id=jbNjgmE0OP
- Corrective Retrieval Augmented Generation, Yan et al., 2024: https://arxiv.org/abs/2401.15884
- Microsoft GraphRAG project: https://www.microsoft.com/en-us/research/project/graphrag/

关键词：

- BM25
- dense retrieval
- hybrid search
- reciprocal rank fusion
- cross-encoder reranking
- query rewriting
- HyDE
- multi-hop retrieval
- citation grounding
- claim verification
- GraphRAG
- agentic RAG

## 建议学习节奏

四周版本：

- 第 1 周：完成朴素 RAG 和 20 条问题评测。
- 第 2 周：完成 BM25、dense、hybrid 对比。
- 第 3 周：加入 rerank、引用和拒答。
- 第 4 周：实现 corrective RAG 或 multi-hop RAG，并写评估报告。

八周版本：

- 第 1-2 周：基础 RAG、文档处理、检索指标。
- 第 3-4 周：hybrid、rerank、query rewrite。
- 第 5 周：生成约束、引用、claim verification。
- 第 6 周：Self-RAG、CRAG、multi-hop。
- 第 7 周：GraphRAG 或 Agentic RAG。
- 第 8 周：生产化、监控、A/B、成本优化。

