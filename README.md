# Agentic Loop

基于 LangGraph 的智能体循环系统，支持多 Agent 协作、知识库检索、联网搜索、对话管理和输出审查。

## 架构

```
用户请求 → Query 扩写 → Supervisor 路由 ─┬→ Knowledge Agent ─┐
                                        └→ Personal Agent  ─┤
                                                              ↓
                                                        Output Guard (审查清洗)
                                                              ↓
                                                      Summarize (条件触发)
                                                              ↓
                                                            返回
```

- **Supervisor**：关键词硬路由（天气/新闻/查询类命中直接走 knowledge）+ LLM 兜底路由
- **Knowledge Agent**：Tavily 联网搜索 + Chroma 知识库检索 + Reranker 重排序
- **Personal Agent**：数学计算、时间查询等本地任务
- **Query Rewrite**：在路由前将模糊问题扩写为 2-3 个精准检索词
- **Output Guard**：审查 Agent 输出，不合规则清洗（去 markdown/emoji/冗余，结构化输出）
- **Summarize**：消息超过 12 条自动触发摘要压缩，保留最近 4 条

## 技术栈

| 组件 | 选型 |
|------|------|
| 框架 | LangGraph + LangChain |
| API | FastAPI + Uvicorn |
| 主 LLM | DeepSeek v4 Pro |
| 路由 + 审查 LLM | DeepSeek Chat（小模型省成本） |
| 联网搜索 | Tavily API |
| 向量存储 | Chroma（底层 SQLite） |
| Embedding 模型 | shibing624/text2vec-base-chinese |
| Reranker | DeepSeek Chat API（替代本地 CrossEncoder） |
| 对话持久化 | SQLite（自定义 SqliteSaver） |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 API Key：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（必填） |
| `TAVILY_API_KEY` | Tavily 搜索 API 密钥（必填） |
| `LANGSMITH_API_KEY` | LangSmith 密钥（可选） |
| `HF_ENDPOINT` | HuggingFace 镜像（国内用户推荐） |

### 3. 启动服务

```bash
python run.py
```

服务运行在 `http://localhost:8000`。

## 项目结构

```
.
├── app/
│   ├── agents/          # Agent 定义 + Prompt（Supervisor / Knowledge / Personal）
│   ├── api/             # FastAPI 路由、中间件、数据模型
│   ├── models/          # LLM / Embedding / Reranker 封装
│   ├── nodes/           # LangGraph 节点实现
│   │   ├── rewrite.py           # Query 扩写
│   │   ├── supervisor_node.py   # 路由决策（硬路由 + LLM）
│   │   ├── knowledge_node.py    # 知识 Agent 节点
│   │   ├── personal_node.py     # 个人助手节点
│   │   ├── output_guard.py      # 输出审查 + 清洗
│   │   └── summarize.py         # 对话摘要
│   ├── tools/           # 工具集
│   │   ├── search_web.py        # Tavily 联网搜索
│   │   ├── search_kb.py         # 知识库检索（向量召回 + Reranker）
│   │   ├── search_limit.py      # 搜索次数限制
│   │   └── calculator.py        # 计算器
│   ├── graph.py         # Agent 图编排
│   ├── state.py         # 状态定义
│   ├── memory.py        # 对话持久化（SQLite）
│   └── config.py        # 全局配置
├── chroma_test/         # Chroma 向量库持久化目录
├── 知识库文档.txt        # 知识库原始文档
├── run.py               # 启动入口
├── langgraph.json       # LangGraph 配置
└── requirements.txt     # 依赖清单
```

## 知识库检索链

```
query → embedding(text2vec-base-chinese) → Chroma 相似度检索(top 5)
      → DeepSeek Reranker 重排序 → 返回 top 2
```

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SEARCH_LIMIT` | 3 | 每轮对话最大搜索次数 |
| `MESSAGE_THRESHOLD` | 12 | 超过此消息数自动触发摘要 |
| `KEEP_RECENT` | 4 | 摘要后保留最近 N 条消息 |
