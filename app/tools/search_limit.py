from app.config import SEARCH_LIMIT
from app.logging_config import logger

# ===== 搜索次数限制 =====
search_count = 0  # 当前轮已搜索次数（knowledge_node 入口重置）


def _bump_search_count() -> bool:
    """返回 True 表示还可以搜，False 表示已达上限"""
    global search_count
    search_count += 1
    return search_count <= SEARCH_LIMIT


def reset_search_count():
    """每轮对话开始时重置搜索计数"""
    global search_count
    search_count = 0
    logger.info("搜索计数已重置 (上限 %d)", SEARCH_LIMIT)
