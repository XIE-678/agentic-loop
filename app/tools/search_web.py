import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from app.tools.schemas import SearchWebInput
from app.tools.search_limit import _bump_search_count, search_count, SEARCH_LIMIT
from app.logging_config import logger


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
    logger.info("联网搜索(%d/%d): %s", search_count, SEARCH_LIMIT, query[:40])
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get("https://www.bing.com/search", params={"q": query}, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for li in soup.select("li.b_algo"):
            a_tag = li.select_one("h2 a")
            p_tag = li.select_one(".b_caption p")
            if a_tag:
                results.append({
                    "title": a_tag.get_text(strip=True),
                    "href": a_tag.get("href", ""),
                    "body": p_tag.get_text(strip=True) if p_tag else "",
                })
            if len(results) >= 5:
                break
        logger.info("搜索返回 %d 条结果", len(results))
        if not results:
            return "没有搜索到相关内容。"
        parts = []
        for r in results:
            parts.append(f"【{r['title']}】\n{r['href']}\n{r['body']}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        logger.warning("搜索失败: %s", e)
        return f"搜索出错: {str(e)}"
