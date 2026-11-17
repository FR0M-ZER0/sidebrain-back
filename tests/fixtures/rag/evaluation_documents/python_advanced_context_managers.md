# Python resource management

## Context managers

The `with` statement enters a context manager and guarantees its exit method is called when the block ends, including when an exception occurs. File objects implement this protocol.

```python
with open("data.txt", encoding="utf-8") as stream:
    contents = stream.read()
```

## Implementing the protocol

An object-based context manager implements `__enter__` and `__exit__`. `contextlib.contextmanager` can express the same setup and cleanup around a `yield`.
