# Python fundamentals

## Variables and values

Python names refer to objects. Assignment binds a name to a value; `int`, `float`, `str`, `bool`, `list`, and `dict` are common built-in types. Use `type(value)` to inspect a value's type.

```python
name = "Ada"
count = 3
is_ready = True
```

## Strings and f-strings

An f-string evaluates expressions inside braces and formats them into text. Prefer clear expressions and keep formatting separate from the value when it is reused.

```python
greeting = f"Hello, {name}!"
```
