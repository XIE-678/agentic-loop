from langchain_core.tools import tool
from app.models.embeddings import get_vectorstore
from app.models.reranker import reranker
from app.tools.schemas import SearchInput
from app.logging_config import logger


@tool(args_schema=SearchInput)
def search_knowledge_base(query: str):
    """搜索知识库中的文档内容。当用户询问AI、Python、机器学习等知识性问题时，
    用这个方法检索相关文档，再基于检索结果回答。
    流程：向量召回 top5 → Reranker 重排序 → 返回 top2 最相关。"""
    vectorstore = get_vectorstore()

    # 第一轮：向量召回 top5
    candidates = vectorstore.similarity_search(query, k=5)
    if not candidates:
        return "知识库中没有找到相关内容。"

    logger.info("向量召回 %d 条，正在 rerank...", len(candidates))

    # 第二轮：交叉编码器重排序
    pairs = [[query, doc.page_content] for doc in candidates]
    scores = reranker.predict(pairs)  # 返回 list[float]，分数越高越相关

    # 按分数降序排列
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

    # 取 top2 最相关
    top2 = ranked[:2]
    logger.info(
        "Rerank 完成: top2 分数 [%s]",
        ", ".join(f"{s:.3f}" for s, _ in top2),
    )

    parts = []
    for i, (score, doc) in enumerate(top2, 1):
        parts.append(
            f"【第{i}名 · 相关度 {score:.3f} · 来源：{doc.metadata['source']}】\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(parts)
