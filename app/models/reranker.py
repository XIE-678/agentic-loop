from sentence_transformers import CrossEncoder
from app.logging_config import logger

# ===== Reranker 重排序模型 =====
reranker = CrossEncoder(
    "BAAI/bge-reranker-v2-m3",
    device="cpu",
)
logger.info("Reranker 模型加载完成")
