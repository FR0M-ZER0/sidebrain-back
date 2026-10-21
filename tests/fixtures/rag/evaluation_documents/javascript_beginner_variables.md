# JavaScript values

## Declaring variables

Use `const` when a binding will not be reassigned and `let` when it will. Avoid `var` in new code because its function scope differs from block-scoped `let` and `const`.

```javascript
const name = "Ada";
let count = 3;
```

## Primitive values

JavaScript primitive values include string, number, bigint, boolean, undefined, symbol, and null. `typeof` reports a value's type, with historical special cases such as `typeof null` returning `"object"`.
