# C# Performance, Runtime & Concurrency Review Guide

Audit guide for C# memory allocations, cancellation propagation, channels, and client application architecture.

---

## 1. Cancellation Token Propagation

- [ ] **Forwarding `CancellationToken`**:
  - Do all async methods accept `CancellationToken cancellationToken = default` as their final parameter?
  - Is `cancellationToken` forwarded to all downstream async calls (`HttpClient`, `DbContext`, `Task.Delay`, streams)?
  - Omitting cancellation tokens prevents graceful timeouts and causes unneeded background processing when clients disconnect.

---

## 2. Resource Management & `IAsyncDisposable`

- [ ] **`await using` Declarations**:
  - Are resources implementing `IAsyncDisposable` (e.g. `Stream`, `ChannelWriter`, `DbContext`) disposed with `await using` rather than synchronous `using`?
  ```csharp
  // BAD: Synchronous block during async execution
  using var stream = await file.OpenReadAsync();

  // GOOD:
  await using var stream = await file.OpenReadAsync();
  ```

---

## 3. Memory Allocations: Span, Memory & ArrayPool

- [ ] **Zero-Allocation Slicing**:
  - Are hot paths parsing strings or bytes using `ReadOnlySpan<char>` / `ReadOnlySpan<byte>` instead of allocating intermediate substrings via `.Substring()`?
- [ ] **`ArrayPool<T>`**:
  - Are large temporary buffers rented from `ArrayPool<T>.Shared.Rent()` and guaranteed returned in a `finally` block?
- [ ] **String Concatenation in Loops**:
  - Are loops using `StringBuilder` or `ValueStringBuilder` rather than `+=` string concatenations?

---

## 4. Concurrency: Channels & Task Parallel Library

- [ ] **`System.Threading.Channels`**:
  - For producer-consumer queues, is `Channel<T>` used instead of `BlockingCollection<T>` or unbounded lock-based queues?
  - Are channel readers reading asynchronously using `await foreach (var item in channel.Reader.ReadAllAsync(cancellationToken))`?

---

## 5. Desktop & Mobile (WPF / MAUI / MVVM)

- [ ] **Observable Property Notifications**:
  - Are ViewModels utilizing CommunityToolkit.Mvvm (`[ObservableProperty]`, `[RelayCommand]`) to eliminate manual `INotifyPropertyChanged` boilerplate?
- [ ] **Dispatcher Threading**:
  - Are background thread results marshaled to the UI thread via `Dispatcher.InvokeAsync()` before mutating observable collections?
- [ ] **Event Unsubscribing**:
  - Are View event handlers unsubscribed when views are unloaded to prevent memory leaks?

