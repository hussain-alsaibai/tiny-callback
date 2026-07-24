# tiny-callback

> Zero-dependency async callbacks, promise pattern, and event emitter for Python. One file. Built for AI agents and event-driven architectures.

```bash
pip install tiny-callback
```

## Why?

JavaScript has Promises, Node has EventEmitter. Python has... asyncio without a story for composing callbacks. `tiny-callback` fills that gap:

```python
from tiny_callback import Callback, emit, on, once

# Promise-style (chainable)
result = (
    Callback(fetch_data)
    .then(transform)
    .then(store)
    .catch(handle_error)
    .finally(cleanup)
)

# Event emitter
emit("user.created", user_id=123, email="alice@example.com")

@on("user.created")
def welcome_user(user_id, email):
    send_welcome_email(email)
```

## Features

- **Promise-like chaining** — `.then()` / `.catch()` / `.finally()`
- **Async support** — Full `async`/`await`, auto-detected
- **Event emitter** — Register/emit/unregister events
- **Once handlers** — `on(...).once()` or `@once` decorator
- **Batching** — Group callbacks and fire all at once
- **No dependencies** — Pure Python stdlib

## Installation

```bash
pip install tiny-callback
```

Or copy `tiny_callback.py` into your project. One file.

## Quick Start

### Callback (Promise Pattern)

```python
from tiny_callback import Callback, sleep

# Sync chain
result = (
    Callback(lambda: fetch_user(123))
    .then(lambda user: enrich(user, include_orders=True))
    .then(lambda user: render_email(user))
    .catch(lambda err: log.error(err))
    .finally(lambda: close_db())
)

# Async chain (auto-detected)
async def workflow():
    result = (
        Callback(fetch_data)
        .then(process)        # runs async if process is async
        .then(store)
        .catch(handle_error)
    )
    return await result  # awaits if async

# Parallel execution
results = (
    Callback.all([
        lambda: fetch_users(),
        lambda: fetch_products(),
        lambda: fetch_orders(),
    ])
    .then(lambda (users, products, orders): combine(users, products, orders))
)
```

### Event Emitter

```python
from tiny_callback import EventEmitter, on, once, emit

ee = EventEmitter()

# Decorator style
@ee.on("order.placed")
def on_order(order_id, total):
    print(f"Order {order_id}: ${total}")

# Once (fires only once)
@ee.once("payment.captured")
def on_payment(order_id):
    notify_fulfillment(order_id)

# Wildcard patterns
@ee.on("order.*")  # matches order.placed, order.cancelled, etc.
def on_any_order(event, **kwargs):
    print(f"Event: {event}")

# Emit
ee.emit("order.placed", order_id=42, total=99.99)

# Remove listener
ee.off("order.placed", on_order)
```

### Deferred (Lazy Execution)

```python
from tiny_callback import deferred

@deferred
def expensive():
    return compute_something()

# Executes only when .resolve() is called
promise = expensive()
# ... later ...
result = promise.resolve()
```

## API Reference

### `Callback(fn=None)`

Create a callback chain. Auto-detects sync vs async.

```python
cb = Callback(sync_fn)       # returns result directly
cb = Callback(async_fn)      # returns awaitable
cb = Callback(coro)          # returns awaitable
```

**Methods:**

| Method | Description |
|--------|-------------|
| `.then(fn)` | Chain success handler, returns new Callback |
| `.catch(fn)` | Chain error handler, returns new Callback |
| `.finally(fn)` | Chain cleanup handler (always runs) |
| `.map(fn)` | Transform result, return new Callback |
| `.flat_map(fn)` | Chain with result unwrapping |
| `.all(cbs)` | Execute list of callbacks in parallel |
| `.race(cbs)` | Return first resolved callback's result |
| `.resolve()` | Execute the chain (sync) |
| `.await()` | Await the chain (async) |

### `EventEmitter()`

Lightweight pub/sub.

```python
ee = EventEmitter()
ee.on(event, handler, *args, **kwargs)   # register handler
ee.once(event, handler)                # one-time handler
ee.off(event, handler)                  # unregister
ee.emit(event, **data)                 # fire event
ee.listeners(event)                    # list handlers
ee.listener_count(event)               # count handlers
ee.on_any(handler)                      # wildcard all events
```

### `deferred(fn)`

Decorator for lazy evaluation.

```python
@deferred
def compute():
    return expensive_operation()

p = compute()  # NOT executed yet
result = p.resolve()  # NOW it runs
```

### `emit(event, **data)`

Module-level convenience for global event bus.

```python
from tiny_callback import emit, on

@on("app.started")
def init():
    print("App starting!")

emit("app.started")  # fires all "app.started" handlers
```

## Real-World Examples

### AI Agent Tool Callbacks

```python
from tiny_callback import Callback

def agent_loop(prompt):
    return (
        Callback(lambda: llm.call(prompt))
        .then(parse_tool_calls)
        .then(execute_tools)
        .then(format_response)
        .catch(lambda err: f"Error: {err}")
    )

# Run
result = agent_loop("What's the weather in Tokyo?")
```

### Webhook Aggregation

```python
from tiny_callback import Callback, once

@once("deploy.complete")
def notify_team():
    send_slack("Deployment complete!")

for service in services:
    @once(f"deploy.{service}.complete")
    def log_deploy(service=service):
        log.info(f"{service} deployed")
```

## License

MIT — do whatever you want.
