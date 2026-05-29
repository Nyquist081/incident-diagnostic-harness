# RAG 代码实践

本目录从一个无依赖脚本开始，帮助你先理解 RAG 链路，而不是被框架细节淹没。

## 运行最小示例

```bash
python rag_learning/practice/toy_rag.py
```

你会看到：

- BM25 召回结果。
- 简单 rerank 后的排序。
- 带引用的模板化答案。
- `Recall@3` 和 `MRR` 评估结果。

## 下一步改造

1. 把 `DOCUMENTS` 替换成真实 Markdown 或 FAQ。
2. 增加 chunker，保留标题路径和 source。
3. 增加 dense embedding 检索。
4. 用 RRF 融合 BM25 和 dense 结果。
5. 接入 reranker。
6. 把答案生成替换成真实 LLM 调用。
7. 保存 trace 到 JSONL。
8. 为每次改动运行评估集。

