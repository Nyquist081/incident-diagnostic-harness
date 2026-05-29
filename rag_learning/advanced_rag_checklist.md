# 高阶 RAG 实战 Checklist

## 设计前

- 明确问题类型：事实查找、解释总结、多跳推理、对比分析、全局洞察、操作建议。
- 明确语料形态：网页、PDF、Markdown、代码、表格、数据库、日志、工单、图谱。
- 明确失败成本：可闲聊、需准确、需审计、需合规。
- 明确权限边界：用户、团队、租户、数据域、时间范围。

## 数据层

- 文档有稳定 id。
- 文档保留 source、版本、更新时间、权限、标题路径。
- 文档去重和近重复合并。
- 表格、代码块、标题层级没有被清洗掉。
- embedding 索引记录模型版本、切分参数和构建时间。

## 检索层

- 有 keyword/sparse fallback。
- 有 dense semantic retrieval。
- 有 hybrid fusion。
- 有 metadata filter。
- 有 reranker。
- 有 query rewrite，但保留原始 query 用于审计。
- 对每次检索保存 top-k、score、rank、source。

## 生成层

- prompt 明确要求基于证据回答。
- 资料不足时允许拒答。
- 输出带引用。
- 关键 claim 能对应到证据。
- 冲突证据要暴露，而不是强行合并。

## 高阶能力选择

| 场景 | 优先技术 |
| --- | --- |
| 用户问题太短或口语化 | query rewriting |
| 召回结果弱或噪声高 | Corrective RAG |
| 需要多步查证 | Multi-hop RAG |
| 需要模型决定是否检索 | Agentic RAG |
| 需要全局主题、关系、社区洞察 | GraphRAG |
| 需要严格减少幻觉 | claim verification + citation grounding |
| 文档很长但问题具体 | parent-child chunk + rerank |
| 精确术语、编号、代码多 | BM25 + dense hybrid |

## 评估层

- 至少有 50-200 条代表性问题。
- 每条问题标注相关文档或证据片段。
- Retrieval 和 generation 分开评估。
- 有难例集：同义改写、否定问题、多跳问题、过期知识、冲突知识、权限边界。
- 有回归评测，索引和 prompt 变更后自动运行。

## 生产层

- 有请求 trace。
- 有缓存策略。
- 有成本和延迟指标。
- 有用户反馈入口。
- 有人工复核流程。
- 有数据更新和索引重建策略。
- 有提示注入和数据泄漏防护。

