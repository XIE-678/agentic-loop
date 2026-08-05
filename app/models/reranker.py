import os
import re
import requests
from app.logging_config import logger


class DeepSeekReranker:
    """用 DeepSeek API 做 rerank，替代本地 CrossEncoder，不用下载国外模型"""

    def __init__(self, model="deepseek-chat"):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        self.model = model

    def predict(self, pairs):
        """
        pairs: [[query, doc_content], ...]
        返回: list[float] 相关性分数 (0~1)
        """
        if not pairs:
            return []

        query = pairs[0][0]
        scores = []

        for _, doc_content in pairs:
            try:
                resp = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "你是一个文档相关性评分器。"
                                    "根据查询和文档内容的相关程度，只输出一个0到1之间的浮点数，不要任何解释。"
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"查询：{query}\n\n"
                                    f"文档内容：{doc_content[:800]}\n\n"
                                    "相关性分数（0-1）："
                                ),
                            },
                        ],
                        "temperature": 0,
                        "max_tokens": 10,
                    },
                    timeout=30,
                )
                score_text = resp.json()["choices"][0]["message"]["content"].strip()
                score = float(re.search(r"[\d.]+", score_text).group())
                scores.append(min(max(score, 0.0), 1.0))
            except Exception as e:
                logger.warning("Rerank 评分失败: %s", e)
                scores.append(0.0)

        return scores


# ===== Reranker 实例 =====
reranker = DeepSeekReranker(model="deepseek-chat")
logger.info("DeepSeek Reranker 初始化完成")
