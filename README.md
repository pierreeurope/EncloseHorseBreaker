# EncloseHorseBreaker 🐴

A solver and analysis toolkit for [enclose.horse](https://enclose.horse/) - a puzzle game where you trap a horse in the largest possible enclosure.

## What is enclose.horse?

It's a daily puzzle game where you:
1. Place walls on a grid to trap a horse
2. The horse can move in 4 directions (not diagonally)
3. If the horse can reach any edge, it escapes (score = 0)
4. Your score = enclosed area + (cherries × 3)
5. You have a limited wall budget

## Files

- **`ANALYSIS.md`** - Complete reverse-engineering of the game: algorithm, API, data formats
- **`solver.py`** - Python implementation with:
  - Game state parser
  - BFS flood-fill solver (same algorithm as the game)
  - Greedy solver heuristic
  - Brute force solver (for small grids)
  - API client for fetching daily puzzles

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the solver on today's puzzle
python solver.py
```

## Example Output

```
Fetching puzzle for 2026-01-07...

Puzzle: Five of Cherries
By: Shivers
Budget: 12 walls
Optimal score: 66

--- Map ---
~~..~~~.~~~~
~C.C·······~
··C······~··
·C·C~~··~~·~
~·~·~~·····~
~··········~
····~·~~···~
~···~~H~····
~···········
~·····~~···~
··~~··~~C·C~
~·~······C·~
~·······C·C~
~·~~·~·~···~

--- Greedy Solver ---
Found solution with score: 58
Walls placed: 10 / 12
```

## The Algorithm

The game uses **BFS (Breadth-First Search)** to determine if the horse is enclosed:

1. Start from horse position
2. Expand to all reachable cells (not walls, not water)
3. If any edge cell is reached → horse escapes
4. Otherwise → count enclosed area

See `ANALYSIS.md` for the full deobfuscated algorithm and API documentation.

## Solving Strategies

The optimal solution problem is NP-hard (subset of cells to block all paths). Current approaches:

1. **Greedy** (implemented): Block escape paths one by one
2. **Brute Force** (implemented): Try all combinations (slow!)
3. **Min-Cut**: Model as graph, find minimum edge cut
4. **Genetic/MCTS**: Explore solution space with heuristics

## API Reference

```python
from solver import fetch_daily_puzzle, parse_map, solve, greedy_solve

# Fetch puzzle
puzzle = fetch_daily_puzzle("2026-01-07")

# Parse and solve
state = parse_map(puzzle['map'], puzzle['budget'])
walls, score = greedy_solve(state)

print(f"Score: {score}, Optimal: {puzzle['optimalScore']}")
```

## Contributing

Feel free to improve the solver! Some ideas:
- Implement min-cut algorithm
- Add Monte Carlo Tree Search
- Create web interface
- Optimize for speed

## License

MIT - Have fun!
