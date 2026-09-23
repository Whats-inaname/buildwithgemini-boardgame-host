import time
import logging
from functools import wraps

logger = logging.getLogger("board_game_host.telemetry")
logging.basicConfig(level=logging.INFO)

def trace_tool_call(tool_name: str):
    """Decorator to trace tool execution time and log latency telemetry."""
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(f"📊 [TRACE] Tool '{tool_name}' executed successfully in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                logger.error(f"❌ [TRACE] Tool '{tool_name}' failed after {duration:.3f}s: {e}")
                raise e

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(f"📊 [TRACE] Tool '{tool_name}' executed successfully in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                logger.error(f"❌ [TRACE] Tool '{tool_name}' failed after {duration:.3f}s: {e}")
                raise e

        if asyncio_is_coroutine_function(func):
            return async_wrapper
        return sync_wrapper

    return decorator

def asyncio_is_coroutine_function(func):
    import inspect
    return inspect.iscoroutinefunction(func)
