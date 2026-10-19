# Python asynchronous programming

## Coroutines and await

Define a coroutine with `async def`; use `await` to suspend it until another awaitable completes. Calling a coroutine creates an awaitable but does not run it by itself.

```python
async def fetch_value(client, url):
    response = await client.get(url)
    return response.json()
```

## Running concurrent tasks

`asyncio.gather` waits for multiple awaitables and returns their results in input order. `asyncio.run` is an entry point that runs a coroutine in a new event loop.
