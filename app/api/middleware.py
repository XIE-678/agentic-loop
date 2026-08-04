import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_config import logger


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        resp = await call_next(request)
        elapsed = time.time() - start
        logger.info("HTTP %s %s → %s (%.2fs)", request.method, request.url.path, resp.status_code, elapsed)
        return resp
