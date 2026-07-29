# Interface Design

When the user wants to explore alternative interfaces for a chosen deepening candidate, use this "Design It Twice" pattern (Ousterhout): the first idea is unlikely to be the best.

Use the vocabulary in [LANGUAGE.md](LANGUAGE.md) — **module**, **interface**, **seam**, **adapter**, **leverage**.

## Process

### 1. Frame the problem space

Write a user-facing explanation of the problem space for the chosen candidate:

- The constraints any new interface would need to satisfy
- The dependencies it would rely on, and which category they fall into (see [DEEPENING.md](DEEPENING.md))
- A rough illustrative code sketch to ground the constraints — not a proposal, just a way to make the constraints concrete

### 2. Develop alternatives

Develop at least three **radically different** interfaces for the deepened module. If parallel agents are available, give each the same technical brief with a different design constraint. Otherwise, analyze the alternatives sequentially:

- Alternative 1: minimize the interface — aim for 1–3 entry points and maximize leverage per entry point.
- Alternative 2: maximize flexibility — support many use cases and extension.
- Alternative 3: optimize for the most common caller — make the default case trivial.
- Alternative 4, when applicable: design around ports and adapters for cross-seam dependencies.

Use both [LANGUAGE.md](LANGUAGE.md) vocabulary and the project's domain vocabulary so every alternative names things consistently.

Each alternative includes:

1. Interface (types, methods, params — plus invariants, ordering, error modes)
2. Usage example showing how callers use it
3. What the implementation hides behind the seam
4. Dependency strategy and adapters (see [DEEPENING.md](DEEPENING.md))
5. Trade-offs — where leverage is high, where it's thin

### 3. Present and compare

Present designs sequentially so the user can absorb each one, then compare them in prose. Contrast by **depth** (leverage at the interface), **locality** (where change concentrates), and **seam placement**.

After comparing, give your own recommendation: which design you think is strongest and why. If elements from different designs would combine well, propose a hybrid. Be opinionated — the user wants a strong read, not a menu.
