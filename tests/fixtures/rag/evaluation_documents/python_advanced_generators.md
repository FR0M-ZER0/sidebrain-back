# Advanced Python iteration

## Generator functions

A function containing `yield` produces a generator that yields values lazily. Each iteration resumes after the previous `yield`, so a large sequence need not be materialized in memory.

```python
def countdown(start):
    while start:
        yield start
        start -= 1
```

## Generator expressions

Generator expressions use parentheses and evaluate items lazily, unlike list comprehensions which construct a list immediately.
