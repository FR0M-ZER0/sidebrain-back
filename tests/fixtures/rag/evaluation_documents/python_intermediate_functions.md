# Python functions

## Parameters and return values

Functions are defined with `def`. Positional and keyword arguments are supported; default values should be immutable where possible. `return` sends a value to the caller.

```python
def greet(name: str, punctuation: str = "!") -> str:
    return f"Hello, {name}{punctuation}"
```

## Variable arguments

`*args` collects extra positional arguments as a tuple and `**kwargs` collects extra keyword arguments as a dictionary. Type hints document the expected interface.
