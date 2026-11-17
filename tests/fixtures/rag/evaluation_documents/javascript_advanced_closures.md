# JavaScript lexical environment

## Closures

A closure is a function bundled with references to its surrounding lexical environment. An inner function can keep access to variables from an outer function after that outer call has returned.

```javascript
function makeCounter() {
  let count = 0;
  return () => ++count;
}
```

## Private state

Closures can encapsulate state because callers can invoke the returned function without accessing the outer variable directly. Each call to the factory creates a distinct lexical environment.
