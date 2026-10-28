# JavaScript async and await

## Async functions

An `async` function always returns a Promise. `await` pauses that function until a Promise settles, then returns its fulfillment value or throws its rejection.

```javascript
async function loadItems() {
  const response = await fetch("/api/items");
  return response.json();
}
```

## Concurrent requests

Use `Promise.all` with multiple promises to start independent work concurrently. Awaiting the array of promises does not make sequential operations concurrent if each request is awaited before the next starts.
