# Universal Collection & Data Structure Complexity Matrix

A language-independent asymptotic reference matrix for core data structures across Python, TypeScript, Java, Go, and C++.

---

## 1. Asymptotic Complexity Matrix

| Data Structure | Access by Index | Search by Value | Insertion (Prepend) | Insertion (Append) | Insertion (Middle) | Deletion (Head) | Deletion (Tail) |
|---|---|---|---|---|---|---|---|
| **Array / Dynamic Array** | $\Theta(1)$ | $\Theta(n)$ | $\Theta(n)$ | Amortized $\Theta(1)$ | $\Theta(n)$ | $\Theta(n)$ | $\Theta(1)$ |
| **Singly Linked List** | $\Theta(n)$ | $\Theta(n)$ | $\Theta(1)$ | $\Theta(1)$ (with tail pointer) | $\Theta(n)$ | $\Theta(1)$ | $\Theta(n)$ |
| **Doubly Linked List** | $\Theta(n)$ | $\Theta(n)$ | $\Theta(1)$ | $\Theta(1)$ | $\Theta(n)$ | $\Theta(1)$ | $\Theta(1)$ |
| **Hash Table (Map/Dict)** | N/A (Keyed) | $\Theta(1)$ avg / $O(n)$ worst | $\Theta(1)$ avg | $\Theta(1)$ avg | N/A | $\Theta(1)$ avg | $\Theta(1)$ avg |
| **Balanced BST (TreeMap)** | N/A (Keyed) | $\Theta(\log n)$ | $\Theta(\log n)$ | $\Theta(\log n)$ | $\Theta(\log n)$ | $\Theta(\log n)$ | $\Theta(\log n)$ |
| **Binary Heap (PriorityQueue)** | $O(1)$ (peek min/max) | $\Theta(n)$ | $O(\log n)$ (push) | $O(\log n)$ (push) | N/A | $O(\log n)$ (pop min/max) | N/A |
| **Double-Ended Queue (Deque)** | $\Theta(n)$ | $\Theta(n)$ | $\Theta(1)$ | $\Theta(1)$ | $\Theta(n)$ | $\Theta(1)$ | $\Theta(1)$ |

---

## 2. Language Equivalency Mapping

| Conceptual Data Structure | Python 3 | TypeScript / JavaScript | Java (JDK) | Go | C++ (STL) |
|---|---|---|---|---|---|
| **Dynamic Array** | `list` | `Array` (`[]`) | `ArrayList<T>` | `[]T` (slice) | `std::vector<T>` |
| **Hash Map** | `dict` | `Map` | `HashMap<K, V>` | `map[K]V` | `std::unordered_map<K, V>` |
| **Hash Set** | `set` | `Set` | `HashSet<T>` | `map[T]struct{}` | `std::unordered_set<T>` |
| **Ordered / Sorted Map** | `collections.OrderedDict` (insertion order) | `Map` (preserves insertion order) | `TreeMap<K, V>` (Red-Black tree) | Third-party / B-Tree | `std::map<K, V>` (Red-Black tree) |
| **Heap / Priority Queue** | `heapq` module | Third-party (`PriorityQueue`) | `PriorityQueue<T>` | `container/heap` | `std::priority_queue<T>` |
| **Double-Ended Queue** | `collections.deque` | Third-party / pointer array | `ArrayDeque<T>` | Third-party / slice | `std::deque<T>` |

---

## 3. Decision Matrix: Choosing the Right Collection

```text
Do you need to access items by numeric index?
  ├── YES ──> Use Dynamic Array (O(1) index access)
  │
  └── NO ───> Do you need constant-time key-value lookup or deduplication?
                ├── YES ──> Do keys need to be sorted in order?
                │             ├── YES ──> Use Balanced BST / TreeMap (O(log n) sorted lookup)
                │             └── NO ───> Use Hash Table / Map / Set (O(1) average lookup)
                │
                └── NO ───> Do you need continuous FIFO Queue operations (push tail, pop head)?
                              ├── YES ──> Use Deque / ArrayDeque (O(1) head/tail push/pop)
                              └── NO ───> Do you need continuous Min/Max extraction?
                                            └── YES ──> Use Binary Heap / PriorityQueue (O(1) peek, O(log n) pop)
```
