from app.logging_config import logger

if __name__ == "__main__":
    import uvicorn
    logger.info("服务启动")
    uvicorn.run("app.api.routes:app", host="0.0.0.0", port=8000)
