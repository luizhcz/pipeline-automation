import time
from typing import Callable, Dict, Optional

from aiolimiter import AsyncLimiter
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import get_logger

logger = get_logger(__name__)

def _default_key(req: Request) -> str:
    return req.client.host if req.client else "unknown"

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        max_calls: int = 60,
        period: float = 60.0,
        key_func: Callable[[Request], str] | None = None,
        exempt_paths: Optional[set[str]] = None,
    ):
        super().__init__(app)
        self._max = max_calls
        self._period = period
        self._key_func = key_func or _default_key
        self._exempt = exempt_paths or set()
        self._buckets: Dict[str, AsyncLimiter] = {}

    def _bucket(self, key: str) -> AsyncLimiter:
        return self._buckets.setdefault(key, AsyncLimiter(self._max, self._period))

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt:
            return await call_next(request)

        key = self._key_func(request)
        limit = self._bucket(key)
        try:
            async with limit:
                return await call_next(request)
        except Exception:
            retry = int(self._period)
            logger.warning("Rate limit excedido – %s", key)
            return JSONResponse(
                {"detail": "Too Many Requests", "retry_after": retry},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry)},
            )