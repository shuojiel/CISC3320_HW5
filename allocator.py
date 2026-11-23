"""Fixed-size memory allocator simulator for CISC 3320 HW5."""
from dataclasses import dataclass


@dataclass
class Block:
    start: int
    size: int
    name: str | None = None

    @property
    def end(self):
        return self.start + self.size

    @property
    def free(self):
        return self.name is None


class MemoryAllocator:
    """Maintain an address-sorted partition of the simulated pool.

    Ties for best/worst fit go to the lowest start address.
    """

    POLICIES = {"first": "first-fit", "best": "best-fit", "worst": "worst-fit"}

    def __init__(self, pool_size=1000, policy="first"):
        if not isinstance(pool_size, int) or pool_size <= 0:
            raise ValueError("pool size must be a positive integer")
        self.pool_size = pool_size
        self.blocks = [Block(0, pool_size)]
        self.policy = "first"
        self.set_policy(policy)
        self.freed_names = set()

    def set_policy(self, policy):
        policy = policy.lower().removesuffix("-fit")
        if policy not in self.POLICIES:
            raise ValueError("policy must be first, best, or worst")
        self.policy = policy
        return self.POLICIES[policy]

    def allocate(self, name, size):
        if not name or name.isspace():
            raise ValueError("allocation name cannot be empty")
        if any(b.name == name for b in self.blocks):
            raise ValueError(f"duplicate allocation name: {name}")
        if not isinstance(size, int) or size <= 0:
            raise ValueError("allocation size must be a positive integer")
        candidates = [i for i, b in enumerate(self.blocks) if b.free and b.size >= size]
        if not candidates:
            raise ValueError(f"out of memory: no hole fits {size} bytes")
        if self.policy == "first":
            index = candidates[0]
        elif self.policy == "best":
            index = min(candidates, key=lambda i: (self.blocks[i].size, self.blocks[i].start))
        else:
            index = min(candidates, key=lambda i: (-self.blocks[i].size, self.blocks[i].start))
        hole = self.blocks[index]
        allocated = Block(hole.start, size, name)
        if hole.size == size:
            self.blocks[index] = allocated
        else:
            self.blocks[index:index + 1] = [allocated, Block(hole.start + size, hole.size - size)]
        self.freed_names.discard(name)
        self.check_invariants()
        return allocated.start

    def free(self, name):
        index = next((i for i, b in enumerate(self.blocks) if b.name == name), None)
        if index is None:
            if name in self.freed_names:
                raise ValueError(f"double free: {name} was already freed")
            raise ValueError(f"unknown allocation name: {name}")
        block = self.blocks[index]
        start, size = block.start, block.size
        block.name = None
        self.freed_names.add(name)
        # Merge all consecutive holes, including both neighbors.
        merged = []
        for current in self.blocks:
            if merged and merged[-1].free and current.free:
                merged[-1].size += current.size
            else:
                merged.append(current)
        self.blocks = merged
        self.check_invariants()
        return start, size

    def stats(self):
        holes = [b for b in self.blocks if b.free]
        free_bytes = sum(b.size for b in holes)
        largest = max((b.size for b in holes), default=0)
        return {
            "pool": self.pool_size,
            "used": self.pool_size - free_bytes,
            "free": free_bytes,
            "holes": len(holes),
            "largest_hole": largest,
            "fragmentation": (1 - largest / free_bytes) * 100 if free_bytes else 0.0,
        }

    def free_list(self):
        return " ".join(f"[{b.start}-{b.end})" for b in self.blocks if b.free) or "(none)"

    def memory_map(self):
        return "\n".join(
            f"[{b.start:>5}-{b.end:<5}) {b.size:>5} bytes  {'FREE' if b.free else 'USED ' + b.name}"
            for b in self.blocks
        )

    def check_invariants(self):
        assert self.blocks and self.blocks[0].start == 0
        assert all(b.size > 0 for b in self.blocks)
        assert all(a.end == b.start for a, b in zip(self.blocks, self.blocks[1:]))
        assert self.blocks[-1].end == self.pool_size
        assert sum(b.size for b in self.blocks) == self.pool_size
        assert not any(a.free and b.free for a, b in zip(self.blocks, self.blocks[1:]))
        names = [b.name for b in self.blocks if not b.free]
        assert len(names) == len(set(names))


def run_command(allocator, line):
    parts = line.strip().split()
    if not parts or parts[0].startswith("#"):
        return None
    cmd = parts[0].lower()
    try:
        if cmd == "alloc" and len(parts) == 3:
            name = parts[1]
            try:
                size = int(parts[2])
            except ValueError:
                raise ValueError("size must be an integer") from None
            start = allocator.allocate(name, size)
            return f"{name}: {size} bytes at [{start}-{start + size})"
        if cmd == "free" and len(parts) == 2:
            start, size = allocator.free(parts[1])
            return f"{parts[1]} freed (was [{start}-{start + size}) {size} bytes)\nfree list: {allocator.free_list()}"
        if cmd == "policy" and len(parts) == 2:
            return f"policy: {allocator.set_policy(parts[1])}"
        if cmd == "stats" and len(parts) == 1:
            s = allocator.stats()
            return (f"pool {s['pool']}    used {s['used']}    free {s['free']}    holes {s['holes']}\n"
                    f"largest hole {s['largest_hole']}    fragmentation {s['fragmentation']:.1f}%\n"
                    f"free list: {allocator.free_list()}")
        if cmd == "map" and len(parts) == 1:
            return allocator.memory_map()
        if cmd in ("help", "?") and len(parts) == 1:
            return "Commands: alloc NAME SIZE | free NAME | policy first|best|worst | stats | map | help | quit"
        if cmd in ("quit", "exit") and len(parts) == 1:
            return "QUIT"
        return "ERROR: invalid command. Type 'help' for usage."
    except ValueError as exc:
        return f"ERROR: {exc}"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CISC 3320 HW5 memory allocator simulator")
    parser.add_argument("--size", type=int, default=1000, help="pool size in bytes (default: 1000)")
    parser.add_argument("--policy", choices=["first", "best", "worst"], default="first")
    parser.add_argument("--script", help="read commands from a file instead of interactive input")
    args = parser.parse_args()
    try:
        allocator = MemoryAllocator(args.size, args.policy)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Memory allocator: {args.size} bytes, {allocator.POLICIES[allocator.policy]}")
    print("Type 'help' for commands.")
    if args.script:
        try:
            with open(args.script, encoding="utf-8") as source:
                for line in source:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    print(f"alloc> {line}")
                    output = run_command(allocator, line)
                    if output == "QUIT":
                        break
                    if output:
                        print(output)
        except OSError as exc:
            parser.error(str(exc))
    else:
        while True:
            try:
                line = input("alloc> ")
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
            output = run_command(allocator, line)
            if output == "QUIT":
                print("Goodbye.")
                break
            if output:
                print(output)


if __name__ == "__main__":
    main()
