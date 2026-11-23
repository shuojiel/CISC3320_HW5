# CISC 3320 — HW5: Memory Allocator Simulator

A Python simulator for a fixed-size heap, based on Lecture 10 (Fall 2026). It tracks block metadata and does not allocate real bytes. No external packages are required.

## Run

Requires Python 3.10 or newer.

```bash
python allocator.py
python allocator.py --size 1000 --policy best
python allocator.py --policy worst --script lecture_trace.txt
python -m unittest -v
```

Windows PowerShell works with the same commands (or use `py` instead of `python`).

## Commands

- `alloc A 200` — allocate 200 bytes for unique name A.
- `free A` — release A and merge adjacent free blocks.
- `policy first` / `policy best` / `policy worst` — switch placement policy.
- `stats` — report pool size, used/free bytes, hole count, largest hole, fragmentation, free list.
- `map` — print all blocks in address order.
- `help` — show commands.
- `quit` — exit.

The default pool is 1000 bytes, with addresses 0–999. Printed ranges use **half-open** notation: `[0-200)` means bytes 0 through 199.

## Design decisions

**Representation:** One address-sorted list of `Block(start, size, name)`. A block with `name=None` is free; otherwise it is allocated. The class `MemoryAllocator` provides `allocate`, `free`, `stats`, `memory_map`, and `set_policy` without printing. The CLI is separate so the class can later be imported into PyShell OS.

**Placement:** First-fit uses the first suitable free block in address order. Best-fit uses the smallest suitable hole; worst-fit uses the largest suitable hole. Ties go to the **lowest address**. A policy change affects future allocations, not existing blocks.

**Splitting:** Allocation starts at the selected hole's first address. If the hole is larger than the request, the remainder becomes a free block. An exact fit replaces the entire hole, leaving no zero-length block.

**Coalescing:** On `free`, the allocated block is marked free, and a pass merges every pair of adjacent free blocks. This merges left, right, or both neighbors.

**Error handling:** Zero/negative sizes, invalid sizes, duplicate active names, unknown names, double frees, invalid policies, and out-of-memory requests return clear errors without changing the pool. A freed name may be reused for a new allocation.

**Invariants:** Every block has a positive size; blocks are sorted, adjacent, and nonoverlapping; the first block starts at 0; the last ends at the pool size; all block sizes sum to the pool size; no adjacent free blocks remain; active names are unique. `check_invariants()` runs after successful allocations/frees.

**Fragmentation formula:** External fragmentation = `100 * (1 - largest_hole / total_free)` percent. When no free space exists, fragmentation is defined as 0%. There is no alignment or block header overhead in this basic simulator, so internal fragmentation is not modeled.

## Testing

Run `python -m unittest -v`. Tests cover:

1. All nine lecture-trace operations under first-fit, best-fit, and worst-fit.
2. Exact-fit allocation without a zero-sized hole.
3. Coalescing on both sides and fully freeing the pool.
4. Oversized requests, zero sizes, duplicate names, unknown names, and double frees.
5. Reusing names after free and policy tie-breaking.
6. Fragmentation statistics and command handling.
7. Pool-size validation and invariant checks.

### Expected lecture trace results

After allocating A=200, B=300, C=150, D=100, freeing B and D, then allocating E=280 and F=100:

| Policy | E start | F start | Final holes | G=260 |
|---|---:|---:|---|---|
| First-fit | 200 | 650 | [480-500) 20; [750-1000) 250 | FAIL |
| Best-fit | 200 | 650 | [480-500) 20; [750-1000) 250 | FAIL |
| Worst-fit | 650 | 200 | [300-500) 200; [930-1000) 70 | FAIL |

All three policies have 270 bytes free, but no single hole can fit G=260. This is **external fragmentation**. The simulator prints an error and preserves the state.

### Example stats

After `alloc A 200`, `alloc B 300`, `alloc C 150`, `free B`:

```text
pool 1000    used 350    free 650    holes 2
largest hole 350    fragmentation 46.2%
free list: [200-500) [650-1000)
```

## Future PyShell OS integration

Import `MemoryAllocator` into PyShell OS and use `allocate(name, size)` to reserve a simulated output buffer, `free(name)` after a job's output is written, and `stats()` for `memstat`. For a shared pool used by concurrent jobs, guard operations with a lock. On pool exhaustion, this version reports an error instead of blocking or evicting jobs.
