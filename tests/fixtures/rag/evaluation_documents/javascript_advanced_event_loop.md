# JavaScript event loop

## Tasks and microtasks

The event loop processes a task, then drains the microtask queue before starting the next task. Promise reactions and `queueMicrotask` callbacks are microtasks; timer callbacks are tasks.

```javascript
console.log("task");
Promise.resolve().then(() => console.log("microtask"));
setTimeout(() => console.log("timer task"), 0);
```

## Ordering asynchronous work

Synchronous code finishes before queued microtasks run. Promise callbacks added by another microtask are also processed before the next task begins.
