# Java Collections: Selection, Concurrency & Performance

A practical guide for choosing the right collection, ensuring thread safety, and optimizing for performance and CPU cache locality.

---

## 1. Collection Decision Matrix

### Lists & Deques
| Collection | Best For | Avoid When | Complexity |
| :--- | :--- | :--- | :--- |
| **`ArrayList`** | **Default choice for lists.** Fast random access (`get(i)`), contiguous memory, cache-friendly iteration. | Frequent insertions/deletions in the middle of large lists. | Access: $O(1)$, Add: amortized $O(1)$ |
| **`ArrayDeque`** | **Default for Stacks and Queues (LIFO/FIFO).** Faster than `Stack` and `LinkedList`. | Need random index-based access (`get(i)`). | Push/Pop: $O(1)$ |
| **`LinkedList`** | Almost never in modern Java. | High memory overhead per node and severe CPU cache misses. | Access: $O(n)$, Search: $O(n)$ |

### Sets
| Collection | Best For | Characteristics | Complexity |
| :--- | :--- | :--- | :--- |
| **`HashSet`** | **Default choice for unique elements.** | Unordered. Relies on `equals()` and `hashCode()`. | Add/Contains: $O(1)$ |
| **`LinkedHashSet`** | When insertion order must be maintained. | Small overhead over `HashSet` to maintain doubly-linked list. | Add/Contains: $O(1)$ |
| **`TreeSet`** | When elements must remain sorted (natural or `Comparator`). | Navigable, range operations (`subSet`, `headSet`). | Add/Contains: $O(\log n)$ |
| **`EnumSet`** | **Mandatory when elements are `enum` values.** | Implemented internally as a bit vector. Blazing fast, minimal memory. | Bitwise speed: $O(1)$ |

### Maps
| Collection | Best For | Characteristics | Complexity |
| :--- | :--- | :--- | :--- |
| **`HashMap`** | **Default choice for key-value pairs.** | Unordered. Handles collisions via buckets / red-black trees. | Get/Put: $O(1)$ |
| **`LinkedHashMap`** | Maintaining insertion order or building **LRU caches** (`removeEldestEntry`). | Maintains doubly-linked list across entries. | Get/Put: $O(1)$ |
| **`TreeMap`** | Sorted keys or range lookups (`subMap`, `floorKey`). | Red-black tree backing. Keys must implement `Comparable`. | Get/Put: $O(\log n)$ |
| **`EnumMap`** | **Mandatory when keys are `enum` values.** | Backed by a compact array. Zero hashing overhead, no collisions. | Array access: $O(1)$ |

---

## 2. Thread-Safe Collections

### Modern Concurrent Collections (`java.util.concurrent`)
- **`ConcurrentHashMap`**:
  - High concurrency without locking entire map. Uses CAS for reads and bucket-level locks for writes.
  - Never use `Collections.synchronizedMap()` in performance-critical paths.
  - Use atomic compute methods: `map.computeIfAbsent(key, k -> load(k))`.
- **`CopyOnWriteArrayList` / `CopyOnWriteArraySet`**:
  - **When to use**: Highly read-heavy scenarios with very rare writes (e.g., event listener registries).
  - **Avoid when**: Frequent writes (every mutation clones the entire backing array, causing heavy GC pressure).
- **`ConcurrentLinkedQueue` / `LinkedBlockingQueue`**:
  - Non-blocking (CAS-based) vs. blocking producer-consumer queues. Use blocking queues when threads must wait for elements.

### Immutability as the Ultimate Thread-Safety
Immutable collections are inherently thread-safe and require zero locking:
```java
List<String> readOnlyList = List.of("A", "B", "C"); // Unmodifiable & thread-safe
Map<String, String> config = Map.copyOf(mutableConfig);
List<String> names = users.stream().map(User::name).toList(); // Java 16+, unmodifiable
```
- `List.of` / `Map.of` / `copyOf` reject `null` elements and throw on mutation.
- `Collections.unmodifiableList(x)` is only a *view* — changes to `x` still show through. Use `List.copyOf` for a true snapshot.

### `ConcurrentHashMap` Caveat
Keep `compute*` / `merge` functions short and side-effect free; never modify the same map inside them (can deadlock or throw).

### Sequenced Collections (Java 21+)
Use `getFirst()`, `getLast()`, `reversed()` on `List`, `Deque`, `LinkedHashSet`/`LinkedHashMap` instead of `list.get(list.size() - 1)`.

---

## 3. Performance & Efficiency Guidelines

### 1. Pre-size Collections
Dynamic resizing causes array allocations and array copy operations. Pre-size whenever the expected size is known:
```java
// Avoid repeated dynamic resizing
var items = new ArrayList<Item>(expectedCount);
// HashMap rehashes at 75% load factor; Java 19+ computes capacity for you
var map = HashMap.<String, Item>newHashMap(expectedCount);
// Pre-19: new HashMap<>((int) Math.ceil(expectedCount / 0.75))
```

### 2. Prefer Array-Backed Structures (CPU Cache Locality)
- Modern CPUs fetch memory into L1/L2/L3 caches in 64-byte **cache lines**.
- `ArrayList` and `ArrayDeque` store data contiguously in memory, yielding massive hardware cache hit rates.
- `LinkedList` scatters node objects across heap memory, forcing CPU pointer chasing and frequent cache misses.

### 3. Minimize Boxing Overhead
- Storing primitive numbers in generic collections (e.g., `List<Integer>`) boxes each number into a 16-24 byte heap object.
- For high-throughput numeric workloads, use primitive arrays (`int[]`, `long[]`) or specialized primitive collections (FastUtil / Eclipse Collections).

### 4. Correct `equals()` and `hashCode()` Contracts
- Inconsistent `hashCode()` degrades `HashMap` and `HashSet` from $O(1)$ performance down to $O(n)$ (or $O(\log n)$ tree bins).
- Use `record` or let IDE/Lombok generate consistent, immutable key contracts.
- Never mutate an object's fields used in `hashCode()` while it is a key in a map/set — it becomes unreachable.

