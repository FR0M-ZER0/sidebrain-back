# JavaScript functions

## Function declarations

A function declaration defines a reusable block of code. Parameters receive arguments and `return` sends a result to the caller.

```javascript
function greet(name) {
  return `Hello, ${name}!`;
}
```

## Arrow functions

Arrow functions use `=>` and can have an expression body or a block body. They do not have their own `this`, which makes them behave differently from ordinary function expressions.
