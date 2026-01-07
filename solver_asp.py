"""
enclose.horse Solver using Answer Set Programming (Clingo)

Based on the actual method used by the game!
ASP is a declarative constraint programming approach.
"""

import requests
from dataclasses import dataclass
from typing import Optional
import time

try:
    import clingo
    HAS_CLINGO = True
except ImportError:
    HAS_CLINGO = False
    print("⚠️  Clingo not installed. Run: pip install clingo")


@dataclass
class GameState:
    cols: int
    rows: int
    terrain: list[int]  # 0 = grass, 1 = water
    cherries: list[bool]
    player_idx: int
    budget: int


def parse_map(map_string: str, budget: int) -> GameState:
    lines = map_string.strip().split('\n')
    rows, cols = len(lines), len(lines[0])
    terrain, cherries = [], []
    player_idx = -1
    
    for row in range(rows):
        for col in range(cols):
            char = lines[row][col] if col < len(lines[row]) else '.'
            if char == 'H':
                player_idx = row * cols + col
                terrain.append(0)
                cherries.append(False)
            elif char == 'C':
                terrain.append(0)
                cherries.append(True)
            elif char == '~':
                terrain.append(1)
                cherries.append(False)
            else:
                terrain.append(0)
                cherries.append(False)
    
    return GameState(cols, rows, terrain, cherries, player_idx, budget)


def generate_asp_program(state: GameState) -> str:
    """Generate ASP program for Clingo from puzzle state."""
    
    lines = []
    lines.append(f"#const budget={state.budget}.")
    
    # Horse position
    horse_row = state.player_idx // state.cols
    horse_col = state.player_idx % state.cols
    lines.append(f"horse({horse_row},{horse_col}).")
    
    # Cells, boundaries, water, cherries
    for idx in range(len(state.terrain)):
        row = idx // state.cols
        col = idx % state.cols
        
        lines.append(f"cell({row},{col}).")
        
        # Boundary = edge of grid
        if row == 0 or row == state.rows - 1 or col == 0 or col == state.cols - 1:
            lines.append(f"boundary({row},{col}).")
        
        if state.terrain[idx] == 1:
            lines.append(f"water({row},{col}).")
        
        if state.cherries[idx]:
            lines.append(f"cherry({row},{col}).")
    
    # Adjacency rules (4-way connectivity)
    lines.append("")
    lines.append("% Adjacent cells (4-way connectivity)")
    lines.append("adj(R,C, R+1,C) :- cell(R,C), cell(R+1,C).")
    lines.append("adj(R,C, R-1,C) :- cell(R,C), cell(R-1,C).")
    lines.append("adj(R,C, R,C+1) :- cell(R,C), cell(R,C+1).")
    lines.append("adj(R,C, R,C-1) :- cell(R,C), cell(R,C-1).")
    
    # Walkable = not water
    lines.append("")
    lines.append("% Walkable = not water")
    lines.append("walkable(R,C) :- cell(R,C), not water(R,C).")
    
    # Wall choice
    lines.append("")
    lines.append("% Choice: place wall on any walkable cell except horse and cherries")
    lines.append("{ wall(R,C) } :- walkable(R,C), not horse(R,C), not cherry(R,C).")
    
    # Budget constraint
    lines.append("")
    lines.append("% Budget constraint")
    lines.append(":- #count { R,C : wall(R,C) } > budget.")
    
    # Reachability from horse (flood fill)
    lines.append("")
    lines.append("% Reachability from horse (enclosed/reachable cells)")
    lines.append("z(R,C) :- horse(R,C).")
    lines.append("z(R2,C2) :- z(R1,C1), adj(R1,C1, R2,C2), walkable(R2,C2), not wall(R2,C2).")
    
    # Horse cannot reach boundary
    lines.append("")
    lines.append("% Horse cannot reach boundary (would escape)")
    lines.append(":- z(R,C), boundary(R,C).")
    
    # Maximize enclosed area
    lines.append("")
    lines.append("% Maximize enclosed area (cherries worth +3 bonus = 4 total)")
    lines.append("#maximize { 4,R,C : z(R,C), cherry(R,C) ; 1,R,C : z(R,C), not cherry(R,C) }.")
    
    # Output
    lines.append("")
    lines.append("% Output wall positions")
    lines.append("#show wall/2.")
    
    return "\n".join(lines)


def solve_with_clingo(state: GameState, time_limit: int = 60) -> tuple[int, list[int], float]:
    """
    Solve using Clingo ASP solver.
    Returns (score, wall_indices, solve_time)
    """
    if not HAS_CLINGO:
        return 0, [], 0.0
    
    asp_program = generate_asp_program(state)
    
    print(f"    [Clingo] Generated ASP program ({len(asp_program)} chars)")
    
    # Create control object
    ctl = clingo.Control([
        "--opt-mode=optN",  # Find optimal
        "0",  # Find all optimal models
    ])
    
    ctl.add("base", [], asp_program)
    ctl.ground([("base", [])])
    
    best_walls = []
    best_score = 0
    models_found = 0
    
    start_time = time.time()
    
    def on_model(model):
        nonlocal best_walls, best_score, models_found
        models_found += 1
        
        walls = []
        for atom in model.symbols(shown=True):
            if atom.name == "wall":
                row = atom.arguments[0].number
                col = atom.arguments[1].number
                idx = row * state.cols + col
                walls.append(idx)
        
        # Calculate score
        score = calculate_score(state, walls)
        
        if score > best_score:
            best_score = score
            best_walls = walls.copy()
            print(f"    [Clingo] Model {models_found}: score {score}, walls {len(walls)}")
    
    ctl.solve(on_model=on_model)
    
    solve_time = time.time() - start_time
    print(f"    [Clingo] Found {models_found} models in {solve_time:.2f}s")
    
    return best_score, best_walls, solve_time


def calculate_score(state: GameState, walls: list[int]) -> int:
    """Calculate score for given wall placement using BFS."""
    from collections import deque
    
    wall_set = set(walls)
    
    # BFS from horse
    visited = {state.player_idx}
    queue = deque([state.player_idx])
    escaped = False
    
    while queue:
        current = queue.popleft()
        
        row, col = current // state.cols, current % state.cols
        if row == 0 or row == state.rows - 1 or col == 0 or col == state.cols - 1:
            escaped = True
        
        # Check neighbors
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < state.rows and 0 <= nc < state.cols:
                neighbor = nr * state.cols + nc
                if (neighbor not in visited and 
                    neighbor not in wall_set and 
                    state.terrain[neighbor] != 1):
                    visited.add(neighbor)
                    queue.append(neighbor)
    
    if escaped:
        return 0
    
    # Calculate score
    area = len(visited)
    cherry_bonus = sum(3 for c in visited if state.cherries[c])
    return area + cherry_bonus


def visualize_solution(state: GameState, walls: list[int]) -> str:
    """Visualize the solution."""
    from collections import deque
    
    wall_set = set(walls)
    
    # BFS to find enclosed area
    visited = {state.player_idx}
    queue = deque([state.player_idx])
    
    while queue:
        current = queue.popleft()
        row, col = current // state.cols, current % state.cols
        
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < state.rows and 0 <= nc < state.cols:
                neighbor = nr * state.cols + nc
                if (neighbor not in visited and 
                    neighbor not in wall_set and 
                    state.terrain[neighbor] != 1):
                    visited.add(neighbor)
                    queue.append(neighbor)
    
    lines = []
    for row in range(state.rows):
        line = ""
        for col in range(state.cols):
            idx = row * state.cols + col
            if idx == state.player_idx:
                line += "H"
            elif idx in wall_set:
                line += "#"
            elif state.terrain[idx] == 1:
                line += "~"
            elif state.cherries[idx]:
                line += "©" if idx in visited else "C"
            elif idx in visited:
                line += "·"
            else:
                line += "."
        lines.append(line)
    return "\n".join(lines)


def fetch_daily_puzzle(date: str) -> dict:
    response = requests.get(f"https://enclose.horse/api/daily/{date}")
    response.raise_for_status()
    return response.json()


def get_optimal_solution(level_id: str) -> tuple[int, list[int]]:
    response = requests.get(f"https://enclose.horse/api/levels/{level_id}/stats")
    stats = response.json()
    return stats.get('optimalScore', 0), stats.get('optimalWalls', [])


if __name__ == "__main__":
    import sys
    from datetime import date
    
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    
    print(f"🐴 enclose.horse Solver - ASP/Clingo Approach")
    print(f"=" * 60)
    
    if not HAS_CLINGO:
        print("\n❌ Clingo not installed!")
        print("   Install with: pip install clingo")
        sys.exit(1)
    
    print(f"Fetching puzzle for {target_date}...")
    
    try:
        puzzle_data = fetch_daily_puzzle(target_date)
        optimal_score, optimal_walls = get_optimal_solution(puzzle_data['id'])
        
        print(f"\n📋 Puzzle: {puzzle_data['name']} by {puzzle_data['creatorName']}")
        print(f"   Budget: {puzzle_data['budget']} walls")
        print(f"   Known optimal: {optimal_score}")
        
        state = parse_map(puzzle_data['map'], puzzle_data['budget'])
        print(f"   Grid: {state.cols}x{state.rows}")
        
        print(f"\n🔧 Running Clingo solver...")
        score, walls, solve_time = solve_with_clingo(state, time_limit=120)
        
        print(f"\n" + "=" * 60)
        print(f"RESULT")
        print(f"=" * 60)
        print(f"Score: {score}")
        print(f"Optimal: {optimal_score}")
        print(f"Match: {'✅ YES!' if score == optimal_score else f'❌ {score/optimal_score*100:.1f}%'}")
        print(f"Time: {solve_time:.2f}s")
        print(f"Walls: {sorted(walls)}")
        
        if optimal_walls:
            common = len(set(walls) & set(optimal_walls))
            print(f"Common with known optimal: {common}/{len(optimal_walls)}")
        
        print(f"\n📊 Solution:\n")
        print(visualize_solution(state, walls))
        
    except Exception as e:
        print(f"Error: {e}")
        raise

