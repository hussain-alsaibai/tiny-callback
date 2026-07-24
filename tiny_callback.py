"""
tiny-callback — Zero-dependency async callbacks, promise pattern, and event emitter for Python.
MIT License. https://github.com/hussain-alsaibai/tiny-callback
"""
from __future__ import annotations
import asyncio
import time
from typing import Callable, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

__version__ = "1.0.0"
__all__ = ["Callback", "EventEmitter", "deferred", "emit", "on", "once"]


# ── Global event bus ──────────────────────────────────────────────────────────
_global_bus: "EventEmitter | None" = None


def _global() -> "EventEmitter":
    global _global_bus
    if _global_bus is None:
        _global_bus = EventEmitter()
    return _global_bus


def emit(event: str, **data):
    """Emit a global event."""
    _global().emit(event, **data)


def on(event: str, handler: Optional[Callable] = None, **kwargs):
    """Register a global event handler."""
    def decorator(fn: Callable) -> Callable:
        _global().on(event, fn, **kwargs)
        return fn

    if handler is not None:
        _global().on(event, handler, **kwargs)
        return handler
    return decorator


def once(event: str, handler: Optional[Callable] = None, **kwargs):
    """Register a one-time global event handler."""
    def decorator(fn: Callable) -> Callable:
        _global().once(event, fn, **kwargs)
        return fn

    if handler is not None:
        _global().once(event, handler, **kwargs)
        return handler
    return decorator


# ── Callback chain ─────────────────────────────────────────────────────────────

class Callback:
    """
    Promise-like callback chain. Supports sync/async functions transparently.

    Usage:
        Callback(sync_fn).then(fn).catch(fn).always(fn)
    """

    def __init__(
        self,
        fn: Optional[Callable] = None,
        value: Any = None,
        error: Any = None,
    ):
        self._fn = fn
        self._value = value
        self._error = error
        # Auto-resolve if fn is provided and value/error not yet set
        self._resolved = fn is None and value is not None
        self._is_async = asyncio.iscoroutinefunction(fn) if fn else False
        # If fn is sync and provided without pre-set value, capture immediately
        if fn is not None and not self._is_async and value is None and error is None:
            try:
                self._value = fn()
                self._resolved = True
                self._fn = None
            except Exception as e:
                self._error = e
                self._resolved = True
                self._fn = None

    def then(self, fn: Callable[[Any], Any]) -> "Callback":
        """Chain a success handler. Returns a new Callback."""
        if self._error is not None:
            return Callback(value=self._value, error=self._error)
        try:
            result = fn(self._value) if self._resolved else None
            is_async = asyncio.iscoroutinefunction(fn)
            return Callback(
                fn=fn if is_async else None,
                value=result,
                error=None,
            )
        except Exception as e:
            return Callback(value=None, error=e)

    def catch(self, fn: Callable[[Exception], Any]) -> "Callback":
        """Chain an error handler."""
        if self._error is None:
            return Callback(fn=self._fn, value=self._value, error=None)
        try:
            result = fn(self._error)
            is_async = asyncio.iscoroutinefunction(fn)
            return Callback(
                fn=fn if is_async else None,
                value=result,
                error=None,
            )
        except Exception:
            return Callback(value=None, error=None)

    def always(self, fn: Callable) -> "Callback":
        """Chain a cleanup handler that always runs."""
        try:
            fn()
        except Exception:
            pass
        return Callback(fn=self._fn, value=self._value, error=self._error)

    # Alias for JS folks who miss finally
    def finally_fn(self, fn: Callable) -> "Callback":
        """Alias for always(). 'finally' is a reserved keyword in Python."""
        return self.always(fn)

    def map(self, fn: Callable[[Any], Any]) -> "Callback":
        """Transform the value."""
        return self.then(fn)

    def resolve(self) -> Any:
        """Execute the chain synchronously."""
        if self._fn is not None and not self._is_async:
            try:
                self._value = self._fn()
            except Exception as e:
                self._error = e
                raise

        if self._error is not None:
            raise self._error
        return self._value

    async def await_result(self) -> Any:
        """Await the chain asynchronously."""
        if self._fn is not None:
            if self._is_async:
                try:
                    self._value = await self._fn()
                except Exception as e:
                    self._error = e
            else:
                self._value = self._fn()

        if self._error is not None:
            raise self._error
        return self._value

    @classmethod
    def all(cls, fns: list[Callable]) -> "Callback":
        """Execute all callbacks in parallel (sync)."""
        results = []
        errors = []
        for fn in fns:
            try:
                results.append(fn())
            except Exception as e:
                errors.append(e)
                results.append(None)
        return Callback(
            value=results,
            error=errors if errors else None,
        )

    @classmethod
    async def all_async(cls, fns: list[Callable]) -> "Callback":
        """Execute all callbacks in parallel (async)."""
        tasks = [
            asyncio.ensure_future(f())
            if asyncio.iscoroutinefunction(f)
            else asyncio.to_thread(f)
            for f in fns
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        return Callback(
            value=results,
            error=errors if errors else None,
        )

    @property
    def value(self) -> Any:
        return self._value

    @property
    def error(self) -> Any:
        return self._error

    def __bool__(self) -> bool:
        return self._error is None


# ── Deferred ──────────────────────────────────────────────────────────────────

def deferred(fn: Callable) -> "_Deferred":
    """Decorator for lazy evaluation."""
    return _Deferred(fn)


class _Deferred:
    """Lazy evaluation wrapper."""

    def __init__(self, fn: Callable):
        self._fn = fn
        self._resolved = False
        self._value = None
        self._error = None

    def resolve(self) -> Any:
        if not self._resolved:
            self._resolved = True
            try:
                self._value = self._fn()
            except Exception as e:
                self._error = e
                raise
        if self._error is not None:
            raise self._error
        return self._value


# ── Event Emitter ─────────────────────────────────────────────────────────────

@dataclass
class _Handler:
    fn: Callable
    once: bool = False
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)


class EventEmitter:
    """
    Lightweight pub/sub event emitter.

    Usage:
        ee = EventEmitter()
        ee.on("event", handler)
        ee.once("event", handler)
        ee.emit("event", data=123)
        ee.off("event", handler)
    """

    def __init__(self):
        self._handlers: dict[str, list[_Handler]] = defaultdict(list)
        self._any_handlers: list[_Handler] = []
        self._event_count: dict[str, int] = defaultdict(int)
        self._total_events = 0

    def on(self, event: str, handler: Optional[Callable] = None, *args, **kwargs) -> Callable:
        """Register an event handler. Use as @ee.on("event") or ee.on("event", fn)."""
        def decorator(fn: Callable) -> Callable:
            self._handlers[event].append(
                _Handler(fn=fn, args=args, kwargs=kwargs)
            )
            return fn

        if handler is not None:
            self._handlers[event].append(
                _Handler(fn=handler, args=args, kwargs=kwargs)
            )
            return handler
        return decorator

    def once(self, event: str, handler: Optional[Callable] = None, *args, **kwargs) -> Callable:
        """Register a one-time event handler."""
        def decorator(fn: Callable) -> Callable:
            self._handlers[event].append(
                _Handler(fn=fn, once=True, args=args, kwargs=kwargs)
            )
            return fn

        if handler is not None:
            self._handlers[event].append(
                _Handler(fn=handler, once=True, args=args, kwargs=kwargs)
            )
            return handler
        return decorator

    def off(self, event: str, handler: Optional[Callable] = None):
        """Unregister a handler."""
        if handler is None:
            self._handlers[event].clear()
        else:
            self._handlers[event] = [
                h for h in self._handlers[event] if h.fn != handler
            ]

    def emit(self, event: str, **data) -> list[Any]:
        """Fire all handlers for an event."""
        self._event_count[event] += 1
        self._total_events += 1
        results = []

        handlers_to_fire = list(self._handlers[event])
        self._handlers[event] = [
            h for h in handlers_to_fire if not h.once
        ]

        for h in handlers_to_fire:
            try:
                result = h.fn(**{**h.kwargs, **data})
                if asyncio.iscoroutinefunction(h.fn):
                    try:
                        asyncio.get_running_loop()
                        asyncio.create_task(result)
                    except RuntimeError:
                        pass
                results.append(result)
            except Exception as e:
                results.append(e)

        for h in self._any_handlers:
            try:
                result = h.fn(event=event, **h.kwargs, **data)
                results.append(result)
            except Exception as e:
                results.append(e)

        return results

    def listeners(self, event: str) -> int:
        return len(self._handlers[event])

    def on_any(self, handler: Callable):
        """Register a handler that receives ALL events."""
        self._any_handlers.append(_Handler(fn=handler))
        return handler

    def off_any(self, handler: Optional[Callable] = None):
        if handler is None:
            self._any_handlers.clear()
        else:
            self._any_handlers = [
                h for h in self._any_handlers if h.fn != handler
            ]

    def events_count(self, event: str) -> int:
        return self._event_count.get(event, 0)

    def total_events(self) -> int:
        return self._total_events
