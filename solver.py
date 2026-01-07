"""
enclose.horse Solver

This module provides tools for solving and analyzing enclose.horse puzzles.
The game requires placing walls to trap a horse in the largest possible area.
"""

import requests
from collections import deque
from dataclasses import dataclass
from typing import Optional
import itertools


@dataclass
class GameState:
    """Represents the state of an enclose.horse puzzle."""
    cols: int
    rows: int
    terrain: list[int]      # 0 = grass, 1 = water
    walls: list[bool]       # True = wall present
    cherries: list[bool]    # True = cherry present
    portals: list[Optional[int]]  # Portal channel number or None
    player_idx: int         # Horse position (row * cols + col)
    budget: int            # Maximum walls allowed


@dataclass 
class SolveResult:
    """Result of solving/analyzing a puzzle state."""
    wall_count: int
    enclosed_area: int
    cherry_bonus: int
    total_score: int
    visited: set[int]
    escaped: bool
    escape_path: list[int]
    

def parse_map(map_string: str, budget: int) -> GameState:
    """
    Parse a map string into a GameState.
    
    Map characters:
    - '.' = Grass (walkable)
    - '~' = Water (impassable)
    - 'H' = Horse starting position
    - 'C' = Cherry (bonus +3 when enclosed)
    - 'W' = Wall
    - '0-9', 'a-z' = Portal pairs
    """
    lines = map_string.strip().split('\n')
    rows = len(lines)
    cols = len(lines[0])
    
    terrain = []
    walls = []
    cherries = []
    portals = []
    player_idx = -1
    
    for row in range(rows):
        for col in range(cols):
            idx = row * cols + col
            char = lines[row][col] if col < len(lines[row]) else '.'
            
            if char == 'H':
                player_idx = idx
                terrain.append(0)
                walls.append(False)
                cherries.append(False)
                portals.append(None)
            elif char == 'C':
                terrain.append(0)
                walls.append(False)
                cherries.append(True)
                portals.append(None)
            elif char == 'W':
                terrain.append(0)
                walls.append(True)
                cherries.append(False)
                portals.append(None)
            elif char == '~':
                terrain.append(1)
                walls.append(False)
                cherries.append(False)
                portals.append(None)
            elif char.isalnum() and char != 'H' and char != 'C' and char != 'W':
                # Portal
                if '0' <= char <= '9':
                    channel = ord(char) - ord('0')
                else:
                    channel = ord(char) - ord('a') + 10
                terrain.append(0)
                walls.append(False)
                cherries.append(False)
                portals.append(channel)
            else:
                terrain.append(0)
                walls.append(False)
                cherries.append(False)
                portals.append(None)
    
    if player_idx == -1:
        raise ValueError("Map must contain exactly one horse (H)")
    
    return GameState(
        cols=cols,
        rows=rows,
        terrain=terrain,
        walls=walls,
        cherries=cherries,
        portals=portals,
        player_idx=player_idx,
        budget=budget
    )


def solve(state: GameState) -> SolveResult:
    """
    Solve the puzzle using BFS flood-fill.
    
    Returns whether the horse can escape and the enclosed area if trapped.
    """
    cols, rows = state.cols, state.rows
    
    # Build portal lookup
    portal_map: dict[int, list[int]] = {}
    for i, channel in enumerate(state.portals):
        if channel is not None:
            if channel not in portal_map:
                portal_map[channel] = []
            portal_map[channel].append(i)
    
    # BFS
    queue = deque([state.player_idx])
    visited = {state.player_idx}
    parent: dict[int, int] = {}
    
    escaped = False
    escape_cell = -1
    
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # left, right, up, down
    
    def try_visit(idx: int, from_idx: int):
        if idx not in visited and not state.walls[idx] and state.terrain[idx] != 1:
            visited.add(idx)
            parent[idx] = from_idx
            queue.append(idx)
    
    while queue:
        current = queue.popleft()
        col = current % cols
        row = current // cols
        
        # Check if reached edge (escape!)
        if col == 0 or col == cols - 1 or row == 0 or row == rows - 1:
            if not escaped:
                escaped = True
                escape_cell = current
        
        # Try all 4 directions
        for dc, dr in directions:
            new_col = col + dc
            new_row = row + dr
            if 0 <= new_col < cols and 0 <= new_row < rows:
                new_idx = new_row * cols + new_col
                try_visit(new_idx, current)
        
        # Try portal teleportation
        channel = state.portals[current]
        if channel is not None:
            for exit_idx in portal_map.get(channel, []):
                if exit_idx != current:
                    try_visit(exit_idx, current)
    
    # Reconstruct escape path
    escape_path = []
    if escaped and escape_cell != -1:
        cell = escape_cell
        while cell in parent:
            escape_path.insert(0, cell)
            cell = parent[cell]
        escape_path.insert(0, state.player_idx)
    
    # Calculate score
    wall_count = sum(state.walls)
    
    if escaped:
        return SolveResult(
            wall_count=wall_count,
            enclosed_area=0,
            cherry_bonus=0,
            total_score=0,
            visited=visited,
            escaped=True,
            escape_path=escape_path
        )
    
    # Calculate cherry bonus
    cherry_bonus = sum(3 for cell in visited if state.cherries[cell])
    enclosed_area = len(visited)
    
    return SolveResult(
        wall_count=wall_count,
        enclosed_area=enclosed_area,
        cherry_bonus=cherry_bonus,
        total_score=enclosed_area + cherry_bonus,
        visited=visited,
        escaped=False,
        escape_path=[]
    )


def fetch_daily_puzzle(date: str) -> dict:
    """
    Fetch a daily puzzle from the API.
    
    Args:
        date: Date string in format 'YYYY-MM-DD'
    
    Returns:
        Puzzle data including map, budget, optimal score, etc.
    """
    response = requests.get(f"https://enclose.horse/api/daily/{date}")
    response.raise_for_status()
    return response.json()


def visualize_state(state: GameState, result: Optional[SolveResult] = None) -> str:
    """Create a text visualization of the game state."""
    lines = []
    for row in range(state.rows):
        line = ""
        for col in range(state.cols):
            idx = row * state.cols + col
            
            if idx == state.player_idx:
                line += "H"
            elif state.walls[idx]:
                line += "#"
            elif state.terrain[idx] == 1:
                line += "~"
            elif state.cherries[idx]:
                if result and idx in result.visited:
                    line += "©"  # Enclosed cherry
                else:
                    line += "C"
            elif state.portals[idx] is not None:
                ch = state.portals[idx]
                line += chr(ord('0') + ch) if ch < 10 else chr(ord('a') + ch - 10)
            elif result and idx in result.visited:
                line += "·"  # Visited/enclosed area
            else:
                line += "."
        lines.append(line)
    return "\n".join(lines)


def find_edge_cells(state: GameState) -> set[int]:
    """Find all grass cells on the map edges (potential escape points)."""
    edges = set()
    for row in range(state.rows):
        for col in range(state.cols):
            if row == 0 or row == state.rows - 1 or col == 0 or col == state.cols - 1:
                idx = row * state.cols + col
                if state.terrain[idx] == 0:  # Grass
                    edges.add(idx)
    return edges


def find_candidate_walls(state: GameState) -> list[int]:
    """Find all cells where walls could potentially be placed."""
    candidates = []
    for idx in range(len(state.terrain)):
        # Can place wall on grass that isn't horse or cherry or portal
        if (state.terrain[idx] == 0 and 
            idx != state.player_idx and 
            not state.cherries[idx] and
            state.portals[idx] is None):
            candidates.append(idx)
    return candidates


def brute_force_solve(state: GameState, max_walls: Optional[int] = None) -> tuple[list[int], int]:
    """
    Brute force solver - tries all combinations.
    WARNING: Very slow for large grids!
    
    Returns:
        Tuple of (best wall positions, best score)
    """
    max_walls = max_walls or state.budget
    candidates = find_candidate_walls(state)
    
    best_walls = []
    best_score = 0
    
    # Try all combinations from 0 to max_walls
    for num_walls in range(max_walls + 1):
        for wall_combo in itertools.combinations(candidates, num_walls):
            # Apply walls
            test_state = GameState(
                cols=state.cols,
                rows=state.rows,
                terrain=state.terrain.copy(),
                walls=[False] * len(state.walls),
                cherries=state.cherries.copy(),
                portals=state.portals.copy(),
                player_idx=state.player_idx,
                budget=state.budget
            )
            for idx in wall_combo:
                test_state.walls[idx] = True
            
            result = solve(test_state)
            
            if result.total_score > best_score:
                best_score = result.total_score
                best_walls = list(wall_combo)
                print(f"New best: {best_score} with {len(best_walls)} walls")
    
    return best_walls, best_score


def greedy_solve(state: GameState) -> tuple[list[int], int]:
    """
    Greedy solver - blocks escape paths one by one.
    
    This is a heuristic approach that:
    1. Finds current escape paths
    2. Greedily places walls to block them
    3. Repeats until enclosed or budget exhausted
    """
    current_walls = []
    candidates = set(find_candidate_walls(state))
    
    def make_test_state(walls_list):
        test_state = GameState(
            cols=state.cols,
            rows=state.rows,
            terrain=state.terrain.copy(),
            walls=[False] * len(state.walls),
            cherries=state.cherries.copy(),
            portals=state.portals.copy(),
            player_idx=state.player_idx,
            budget=state.budget
        )
        for idx in walls_list:
            test_state.walls[idx] = True
        return test_state
    
    while len(current_walls) < state.budget:
        test_state = make_test_state(current_walls)
        result = solve(test_state)
        
        if not result.escaped:
            # Already enclosed!
            break
        
        # Find best wall to place
        # Strategy: try all candidate walls and pick the one that:
        # 1. Encloses the horse with best score, OR
        # 2. Reduces reachable area the most
        best_wall = None
        best_score = -1
        best_is_enclosed = False
        
        for wall_candidate in candidates:
            if wall_candidate == state.player_idx:
                continue
            
            # Test placing this wall
            test_walls = current_walls + [wall_candidate]
            test_state = make_test_state(test_walls)
            test_result = solve(test_state)
            
            if not test_result.escaped:
                # This wall encloses the horse!
                if not best_is_enclosed or test_result.total_score > best_score:
                    best_is_enclosed = True
                    best_score = test_result.total_score
                    best_wall = wall_candidate
            elif not best_is_enclosed:
                # Not enclosed yet, prefer smaller reachable area
                # (closer to being enclosed)
                area = len(test_result.visited)
                if area < best_score or best_score == -1:
                    best_score = area
                    best_wall = wall_candidate
        
        if best_wall is None:
            # No valid wall placement found
            break
        
        current_walls.append(best_wall)
        candidates.remove(best_wall)
        
        # Early exit if we found an enclosure
        if best_is_enclosed:
            break
    
    # Calculate final score
    final_state = make_test_state(current_walls)
    final_result = solve(final_state)
    
    return current_walls, final_result.total_score


def smart_solve(state: GameState, verbose: bool = False) -> tuple[list[int], int]:
    """
    Smarter solver that tries multiple strategies and picks the best.
    
    Strategies:
    1. Greedy (minimize reachable area)
    2. Try to find small enclosures first
    3. Random restarts with greedy
    """
    import random
    
    best_walls = []
    best_score = 0
    
    # Strategy 1: Basic greedy
    walls, score = greedy_solve(state)
    if score > best_score:
        best_score = score
        best_walls = walls
        if verbose:
            print(f"Greedy found: {score}")
    
    # Strategy 2: Try blocking edges near the horse first
    cols, rows = state.cols, state.rows
    horse_col = state.player_idx % cols
    horse_row = state.player_idx // cols
    
    candidates = find_candidate_walls(state)
    
    # Sort candidates by distance to horse
    def dist_to_horse(idx):
        col = idx % cols
        row = idx // cols
        return abs(col - horse_col) + abs(row - horse_row)
    
    candidates_by_dist = sorted(candidates, key=dist_to_horse)
    
    # Try building walls in rings around the horse
    for start_dist in range(1, min(cols, rows) // 2):
        ring_candidates = [c for c in candidates_by_dist 
                         if start_dist <= dist_to_horse(c) <= start_dist + 2]
        
        if len(ring_candidates) < state.budget:
            continue
        
        # Try combinations in this ring
        for combo in itertools.combinations(ring_candidates[:min(20, len(ring_candidates))], 
                                           min(state.budget, len(ring_candidates))):
            test_state = GameState(
                cols=state.cols,
                rows=state.rows,
                terrain=state.terrain.copy(),
                walls=[False] * len(state.walls),
                cherries=state.cherries.copy(),
                portals=state.portals.copy(),
                player_idx=state.player_idx,
                budget=state.budget
            )
            for idx in combo:
                test_state.walls[idx] = True
            
            result = solve(test_state)
            if result.total_score > best_score:
                best_score = result.total_score
                best_walls = list(combo)
                if verbose:
                    print(f"Ring {start_dist} found: {best_score}")
    
    # Strategy 3: Random search with local improvement
    for _ in range(100):
        # Random wall placement
        sample_size = min(state.budget, len(candidates))
        random_walls = random.sample(candidates, sample_size)
        
        test_state = GameState(
            cols=state.cols,
            rows=state.rows,
            terrain=state.terrain.copy(),
            walls=[False] * len(state.walls),
            cherries=state.cherries.copy(),
            portals=state.portals.copy(),
            player_idx=state.player_idx,
            budget=state.budget
        )
        for idx in random_walls:
            test_state.walls[idx] = True
        
        result = solve(test_state)
        if result.total_score > best_score:
            best_score = result.total_score
            best_walls = random_walls
            if verbose:
                print(f"Random found: {best_score}")
    
    return best_walls, best_score


# Example usage
if __name__ == "__main__":
    # Fetch today's puzzle
    from datetime import date
    
    today = date.today().isoformat()
    print(f"Fetching puzzle for {today}...")
    
    try:
        puzzle_data = fetch_daily_puzzle(today)
        print(f"\nPuzzle: {puzzle_data['name']}")
        print(f"By: {puzzle_data['creatorName']}")
        print(f"Budget: {puzzle_data['budget']} walls")
        print(f"Optimal score: {puzzle_data.get('optimalScore', 'Unknown')}")
        print(f"Play count: {puzzle_data['playCount']}")
        
        # Parse and analyze
        state = parse_map(puzzle_data['map'], puzzle_data['budget'])
        print(f"\nGrid size: {state.cols}x{state.rows}")
        
        # Initial state (no walls)
        result = solve(state)
        print(f"\nWithout walls:")
        print(f"  Horse escapes: {result.escaped}")
        print(f"  Reachable area: {len(result.visited)}")
        
        print(f"\n--- Map ---")
        print(visualize_state(state, result))
        
        # Try smart solver
        print(f"\n--- Smart Solver ---")
        walls, score = smart_solve(state, verbose=True)
        print(f"\nBest solution found with score: {score}")
        print(f"Walls placed: {len(walls)} / {state.budget}")
        print(f"Wall positions: {walls}")
        
        # Visualize solution
        for idx in walls:
            state.walls[idx] = True
        final_result = solve(state)
        print(f"\n--- Solution ---")
        print(visualize_state(state, final_result))
        
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching puzzle: {e}")
    except Exception as e:
        print(f"Error: {e}")
        raise

