import os
from datetime import datetime
from tavily import TavilyClient
from langchain_core.tools import tool
from app.tools.schemas import SearchWebInput
from app.tools.search_limit import _bump_search_count, search_count, SEARCH_LIMIT
from app.logging_config import logger

# Tavily 客户端（全局复用）
_tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))


@tool(args_schema=SearchWebInput)
def search_web(query: str):
    """联网搜索最新信息。当用户询问新闻、实时信息等需要联网的问题时使用。
    重要：每轮对话最多只能调用有限次数，超过后必须基于已有搜索结果回答！"""
    if not _bump_search_count():
        logger.warning("已达搜索上限 %d 次，拒绝搜索: %s", SEARCH_LIMIT, query[:40])
        return (
            f"⚠️ 本轮已搜索 {SEARCH_LIMIT} 次，已达上限！"
            "请基于之前搜索到的结果回答用户，不要再调用搜索工具。"
            "如果搜索结果不够好，诚实告诉用户并给出已有信息即可。"
        )

    # 拼入当前日期，确保搜索时效性（防止 Tavily 返回昨日缓存）
    today = datetime.now().strftime("%Y年%m月%d日")
    dated_query = f"{today} {query}"

    logger.info("联网搜索(%d/%d): %s", search_count, SEARCH_LIMIT, query[:40])
    try:
        resp = _tavily.search(
            query=dated_query,
            max_results=5,
            include_raw_content=False,
        )
        results = resp.get("results", [])
        logger.info("搜索返回 %d 条结果", len(results))
        if not results:
            return "没有搜索到相关内容。"

        parts = []
        for r in results:
            parts.append(f"【{r['title']}】\n{r['url']}\n{r['content']}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        logger.warning("搜索失败: %s", e)
        return f"搜索出错: {str(e)}"
