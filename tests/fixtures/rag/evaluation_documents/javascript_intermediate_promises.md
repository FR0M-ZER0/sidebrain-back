# JavaScript asynchronous results

## Promise states

A Promise represents the eventual completion or failure of an asynchronous operation. It is pending before settlement and becomes fulfilled or rejected afterward.

```javascript
fetch("/api/items")
  .then((response) => response.json())
  .catch((error) => console.error(error));
```

## Promise combinators

`Promise.all` fulfills when all input promises fulfill and rejects when one rejects. `Promise.allSettled` waits for every input and reports each fulfillment or rejection.
