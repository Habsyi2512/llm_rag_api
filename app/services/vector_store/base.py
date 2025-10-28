# app/services/vector_store/base.py

import asyncio
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Singleton container for service state
class _VectorState:
    def __init__(self):
        self._vector_store = None
        self._retriever = None
        self._embeddings = None
        self._initialized = False
        self._lock = asyncio.Lock()  # protect rebuilds

    @property
    def vector_store(self):
        return self._vector_store

    @vector_store.setter
    def vector_store(self, v):
        self._vector_store = v

    @property
    def retriever(self):
        return self._retriever

    @retriever.setter
    def retriever(self, r):
        self._retriever = r

    @property
    def embeddings(self):
        return self._embeddings

    @embeddings.setter
    def embeddings(self, e):
        self._embeddings = e

    @property
    def initialized(self):
        return self._initialized

    @initialized.setter
    def initialized(self, val: bool):
        self._initialized = val

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock


_state = _VectorState()

def get_state() -> _VectorState:
    return _state


# simple retry helper (no external dependency)
async def retry_async(func, *args, tries: int = 3, backoff_base: float = 0.5, **kwargs):
    last_exc = None
    for attempt in range(1, tries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            wait = backoff_base * (2 ** (attempt - 1))
            logger.warning("Attempt %s failed, retrying after %.1fs: %s", attempt, wait, e)
            await asyncio.sleep(wait)
    # final raise
    raise last_exc
