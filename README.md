# EncloseHorseBreaker 🐴

A solver for [enclose.horse](https://enclose.horse/) - a daily puzzle game where you trap a horse in the largest possible enclosure.

## What is enclose.horse?

It's a daily puzzle game where you:
1. Place walls on a grid to trap a horse
2. The horse can move in 4 directions (not diagonally)
3. Water (`~`) blocks movement
4. If the horse can reach any edge, it escapes (score = 0)
5. Your score = enclosed area + (cherries × 3)
6. You have a limited wall budget

## The Journey: From Heuristics to ASP

### Phase 1: Reverse Engineering

We started by scraping and analyzing the game:
- Deobfuscated the minified JavaScript
- Discovered the core algorithm: **BFS flood-fill** to check if horse can escape
- Found the API endpoints for fetching puzzles and optimal solutions
- Documented everything in `ANALYSIS.md`

### Phase 2: Implementing Search Algorithms (The Hard Way)

We tried many approaches to find optimal solutions:

| Algorithm | Best Score | Time | % of Optimal |
|-----------|-----------|------|--------------|
| Greedy | ~20 | <1s | ~30% |
| Simulated Annealing | 43 | 411s | 65% |
| Genetic Algorithm | 44 | 60s | 67% |
| Smart SA (pruned candidates) | 56 | 224s | 85% |
| A* Search | 1 | 380s | 1.5% |
| Beam Search | 3 | 60s | 4.5% |

**Why was it so hard?**

1. **Massive search space**: C(104, 12) ≈ 10^14 combinations
2. **Interdependent walls**: The optimal solution requires ALL 12 walls to work together
   - With 11 optimal walls: score = 0 (horse escapes)
   - With 12 optimal walls: score = 66 (perfect enclosure)
3. **Deceptive landscape**: Local optima everywhere, optimal is a needle in a haystack

### Phase 3: The Breakthrough - Answer Set Programming

Then we discovered that **the game itself uses ASP (Answer Set Programming)** with the Clingo solver!

We found this on HackerNews:
> "The site uses Answer Set Programming with the Clingo engine to compute the optimal solutions for smaller grids. Maximizing grids like this is probably NP-hard."

The ASP approach is **declarative** - you describe WHAT a valid solution looks like, not HOW to find it:

```asp
% Place walls anywhere (choice)
{ wall(R,C) } :- walkable(R,C), not horse(R,C).

% Budget constraint
:- #count { wall(R,C) } > budget.

% Horse can't escape (reachability constraint)
:- reachable(R,C), boundary(R,C).

% Maximize enclosed area
#maximize { 1,R,C : reachable(R,C) }.
```

**Result with Clingo:**

| Algorithm | Score | Time | % of Optimal |
|-----------|-------|------|--------------|
| **ASP (Clingo)** | **66** | **0.31s** | **100%** ✅ |

The ASP solver is **700x faster** and **guarantees the optimal solution**!

## Files

- **`solver_asp.py`** - The ASP/Clingo solver (recommended!)
- **`solver.py`** - Original Python solver with various heuristic algorithms
- **`ANALYSIS.md`** - Complete reverse-engineering of the game
- **`ASP_EXPLAINED.md`** - Deep dive into Answer Set Programming

## Quick Start

### Using the ASP Solver (Recommended)

```bash
# Install dependencies
pip install clingo requests

# Run on today's puzzle
python solver_asp.py

# Run on a specific date
python solver_asp.py 2026-01-07
```

### Example Output

```
🐴 enclose.horse Solver - ASP/Clingo Approach
============================================================
Fetching puzzle for 2026-01-07...

📋 Puzzle: Five of Cherries by Shivers
   Budget: 12 walls
   Known optimal: 66
   Grid: 12x14

🔧 Running Clingo solver...
    [Clingo] Generated ASP program (4383 chars)
    [Clingo] Model 1: score 1, walls 11
    ...
    [Clingo] Model 16: score 66, walls 12
    [Clingo] Found 17 models in 0.31s

============================================================
RESULT
============================================================
Score: 66
Optimal: 66
Match: ✅ YES!
Time: 0.31s

📊 Solution:

~~.#~~~#~~~~
~C#©·······~
..C#·····~·#
.C.C~~··~~·~
~.~.~~·····~
~..#·······~
....~·~~···~
~...~~H~···#
~....#·····#
~.....~~···~
..~~..~~©·©~
~.~.....#©·~
~.......C#©~
~.~~.~.~..#~
```

## Key Learnings

1. **Choose the right paradigm**: Constraint satisfaction problems are better solved declaratively than with search heuristics

2. **ASP is powerful**: For combinatorial optimization with complex constraints, ASP/Clingo can find guaranteed optimal solutions quickly

3. **The problem structure matters**: The interdependence of walls (need ALL of them for enclosure) makes gradient-based search ineffective

4. **Research existing solutions**: The game's own approach (ASP) was the key insight

## API Reference

```python
from solver_asp import fetch_daily_puzzle, parse_map, solve_with_clingo

# Fetch puzzle
puzzle = fetch_daily_puzzle("2026-01-07")

# Parse and solve
state = parse_map(puzzle['map'], puzzle['budget'])
score, walls, time = solve_with_clingo(state)

print(f"Score: {score}, Optimal: {puzzle.get('optimalScore', 'unknown')}")
```

## Requirements

- Python 3.10+
- `clingo` - ASP solver
- `requests` - HTTP client

## Further Reading

- **ASP_EXPLAINED.md** - Comprehensive guide to Answer Set Programming
- **ANALYSIS.md** - Game reverse engineering details
- [Potassco (Clingo)](https://potassco.org/) - The ASP solver we use
- [enclose.horse](https://enclose.horse/) - Play the game!

## License

MIT - Have fun! 🐴
