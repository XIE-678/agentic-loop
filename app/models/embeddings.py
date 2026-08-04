import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.logging_config import logger

# ===== 嵌入模型 + 向量库 =====
embeddings = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")

chroma_dir = "./chroma_test"


def _build_vectorstore():
    """构建或加载 Chroma 向量库"""
    if os.path.exists(chroma_dir) and os.listdir(chroma_dir):
        vs = Chroma(persist_directory=chroma_dir, embedding_function=embeddings)
        logger.info("向量库已加载")
    else:
        with open("./知识库文档.txt", 'r', encoding="utf-8") as f:
            text = f.read()
        logger.info("知识库文件 %d 字符", len(text))
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        chunks = text_splitter.create_documents(
            texts=[text], metadatas=[{"source": "知识库文档.txt"}]
        )
        logger.info("切分完成，共 %d 块", len(chunks))
        vs = Chroma.from_documents(
            documents=chunks, embedding=embeddings, persist_directory=chroma_dir
        )
        logger.info("向量库构建完成，共 %d 块", len(chunks))
    return vs


vectorstore = _build_vectorstore()


def get_vectorstore():
    """返回已初始化的向量库实例"""
    return vectorstore
