# Agentic Loop

基于 LangGraph 的智能体循环系统，支持多 Agent 协作、知识库检索、工具调用和对话管理。

## 架构

```
用户请求 → Query 扩写 → Supervisor 路由 → Knowledge Agent / Personal Agent → 摘要 → 返回
```

- **Supervisor**：中央调度器，分析意图并分发给合适的子 Agent
- **Knowledge Agent**：负责知识库检索、联网搜索、计算等知识密集型任务
- **Personal Agent**：负责个人信息管理、日程等个人化任务
- **Query Rewrite**：在路由前对用户问题进行扩写优化
- **Summarize**：对话历史过长时自动触发摘要压缩

## 技术栈

- **框架**：LangGraph + LangChain
- **API**：FastAPI + Uvicorn
- **模型**：DeepSeek（兼容 OpenAI 接口）
- **向量存储**：Chroma
- **嵌入模型**：sentence-transformers（HuggingFace）
- **监控**：LangSmith（可选）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（必填） |
| `LANGSMITH_API_KEY` | LangSmith 密钥（可选，用于监控） |
| `LANGSMITH_TRACING` | 是否开启追踪，默认 `false` |

### 3. 启动服务

```bash
python run.py
```

服务运行在 `http://localhost:8000`。

## 项目结构

```
.
├── app/
│   ├── agents/        # Agent 定义（Supervisor / Knowledge / Personal）
│   ├── api/           # FastAPI 路由、中间件、数据模型
│   ├── models/        # LLM / Embedding / Reranker 模型封装
│   ├── nodes/         # LangGraph 节点实现
│   ├── tools/         # 工具集（搜索、计算器等）
│   ├── graph.py       # Agent 图编排
│   ├── state.py       # 状态定义
│   ├── memory.py      # 对话记忆管理
│   └── config.py      # 全局配置
├── run.py             # 启动入口
├── langgraph.json     # LangGraph 配置
└── requirements.txt   # 依赖清单
```

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SEARCH_LIMIT` | 3 | 每轮对话最大搜索次数 |
| `MESSAGE_THRESHOLD` | 12 | 超过此消息数自动触发摘要 |
| `KEEP_RECENT` | 4 | 摘要后保留最近 N 条消息 |
