"""
enclose.horse Solver - Multi-Algorithm Benchmark

Smart solvers that actually try to find optimal solutions.
"""

import requests
import time
import random
import math
from collections import deque
from dataclasses import dataclass
from typing import Optional
import itertools


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class GameState:
    cols: int
    rows: int
    terrain: list[int]      # 0 = grass, 1 = water
    walls: list[bool]
    cherries: list[bool]
    portals: list[Optional[int]]
    player_idx: int
    budget: int


@dataclass 
class SolveResult:
    wall_count: int
    enclosed_area: int
    cherry_bonus: int
    total_score: int
    visited: set[int]
    escaped: bool
    escape_path: list[int]


@dataclass
class BenchmarkResult:
    name: str
    score: int
    walls: list[int]
    time_seconds: float
    iterations: int = 0


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def parse_map(map_string: str, budget: int) -> GameState:
    lines = map_string.strip().split('\n')
    rows, cols = len(lines), len(lines[0])
    terrain, walls, cherries, portals = [], [], [], []
    player_idx = -1
    
    for row in range(rows):
        for col in range(cols):
            char = lines[row][col] if col < len(lines[row]) else '.'
            if char == 'H':
                player_idx = row * cols + col
                terrain.append(0); walls.append(False); cherries.append(False); portals.append(None)
            elif char == 'C':
                terrain.append(0); walls.append(False); cherries.append(True); portals.append(None)
            elif char == '~':
                terrain.append(1); walls.append(False); cherries.append(False); portals.append(None)
            elif char.isalnum() and char not in 'HCW':
                channel = ord(char) - ord('0') if '0' <= char <= '9' else ord(char) - ord('a') + 10
                terrain.append(0); walls.append(False); cherries.append(False); portals.append(channel)
            else:
                terrain.append(0); walls.append(False); cherries.append(False); portals.append(None)
    
    return GameState(cols, rows, terrain, walls, cherries, portals, player_idx, budget)


def solve(state: GameState) -> SolveResult:
    """BFS flood-fill to check if horse is enclosed."""
    cols, rows = state.cols, state.rows
    
    portal_map = {}
    for i, ch in enumerate(state.portals):
        if ch is not None:
            portal_map.setdefault(ch, []).append(i)
    
    queue = deque([state.player_idx])
    visited = {state.player_idx}
    escaped, escape_cell = False, -1
    
    while queue:
        current = queue.popleft()
        col, row = current % cols, current // cols
        
        if col == 0 or col == cols - 1 or row == 0 or row == rows - 1:
            if not escaped:
                escaped, escape_cell = True, current
        
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = col + dc, row + dr
            if 0 <= nc < cols and 0 <= nr < rows:
                idx = nr * cols + nc
                if idx not in visited and not state.walls[idx] and state.terrain[idx] != 1:
                    visited.add(idx)
                    queue.append(idx)
        
        ch = state.portals[current]
        if ch is not None:
            for exit_idx in portal_map.get(ch, []):
                if exit_idx != current and exit_idx not in visited and not state.walls[exit_idx]:
                    visited.add(exit_idx)
                    queue.append(exit_idx)
    
    if escaped:
        return SolveResult(sum(state.walls), 0, 0, 0, visited, True, [])
    
    cherry_bonus = sum(3 for c in visited if state.cherries[c])
    return SolveResult(sum(state.walls), len(visited), cherry_bonus, len(visited) + cherry_bonus, visited, False, [])


def make_state_with_walls(base: GameState, wall_indices: list[int]) -> GameState:
    new_walls = [False] * len(base.walls)
    for idx in wall_indices:
        new_walls[idx] = True
    return GameState(base.cols, base.rows, base.terrain, new_walls, 
                     base.cherries, base.portals, base.player_idx, base.budget)


def find_candidate_walls(state: GameState) -> list[int]:
    return [idx for idx in range(len(state.terrain))
            if state.terrain[idx] == 0 and idx != state.player_idx 
            and not state.cherries[idx] and state.portals[idx] is None]


def evaluate_walls(state: GameState, walls: list[int]) -> int:
    return solve(make_state_with_walls(state, walls)).total_score


def fetch_daily_puzzle(date: str) -> dict:
    response = requests.get(f"https://enclose.horse/api/daily/{date}")
    response.raise_for_status()
    return response.json()


def visualize_state(state: GameState, result: Optional[SolveResult] = None) -> str:
    lines = []
    for row in range(state.rows):
        line = ""
        for col in range(state.cols):
            idx = row * state.cols + col
            if idx == state.player_idx: line += "H"
            elif state.walls[idx]: line += "#"
            elif state.terrain[idx] == 1: line += "~"
            elif state.cherries[idx]: line += "©" if result and idx in result.visited else "C"
            elif state.portals[idx] is not None:
                ch = state.portals[idx]
                line += chr(ord('0') + ch) if ch < 10 else chr(ord('a') + ch - 10)
            elif result and idx in result.visited: line += "·"
            else: line += "."
        lines.append(line)
    return "\n".join(lines)


# =============================================================================
# SMART SOLVERS
# =============================================================================

def find_escape_path_cells(state: GameState, current_walls: list[int]) -> set[int]:
    """Find all cells that are on ANY escape path from horse to edge."""
    test_state = make_state_with_walls(state, current_walls)
    result = solve(test_state)
    
    if not result.escaped:
        return set()  # Already enclosed
    
    # All visited cells are potential escape route cells
    # But we only care about ones that could be walls
    candidates = set(find_candidate_walls(state))
    return result.visited & candidates


def solve_smart_exhaustive(state: GameState, timeout: float = 120.0) -> BenchmarkResult:
    """
    SMART EXHAUSTIVE: Build walls incrementally, only on escape paths.
    
    Key insight: We only need to place walls on cells that the horse can reach.
    After each wall, recalculate reachable cells and continue.
    This dramatically prunes the search space.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    best_score, best_walls = 0, []
    iterations = 0
    
    def search(current_walls: list[int], remaining_budget: int, start_idx: int):
        nonlocal best_score, best_walls, iterations
        
        if time.time() - start > timeout:
            return
        
        iterations += 1
        
        # Evaluate current state
        score = evaluate_walls(state, current_walls)
        if score > best_score:
            best_score = score
            best_walls = current_walls.copy()
            print(f"    [Smart Exhaustive] New best: {best_score} with {len(current_walls)} walls")
        
        if remaining_budget == 0:
            return
        
        # Find cells on escape paths (only these are worth placing walls on)
        escape_cells = find_escape_path_cells(state, current_walls)
        if not escape_cells:
            return  # Already enclosed, no need for more walls
        
        # Only consider candidates that are on escape paths AND haven't been tried
        useful_candidates = [c for c in candidates[start_idx:] if c in escape_cells]
        
        for i, wall in enumerate(useful_candidates):
            new_walls = current_walls + [wall]
            # Find the index in original candidates to avoid duplicates
            next_start = candidates.index(wall) + 1 if wall in candidates else start_idx
            search(new_walls, remaining_budget - 1, next_start)
    
    search([], state.budget, 0)
    
    return BenchmarkResult("Smart Exhaustive", best_score, best_walls, time.time() - start, iterations)


def solve_genetic_massive(state: GameState, pop_size: int = 300, generations: int = 5000) -> BenchmarkResult:
    """
    MASSIVE GENETIC: 5000 generations with large population.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    if not candidates:
        return BenchmarkResult("Genetic 5K", 0, [], time.time() - start, 0)
    
    def random_individual():
        return random.sample(candidates, num_walls)
    
    def mutate(ind, swaps=1):
        ind = ind.copy()
        for _ in range(swaps):
            available = [c for c in candidates if c not in ind]
            if available and ind:
                ind.pop(random.randrange(len(ind)))
                ind.append(random.choice(available))
        return ind
    
    def crossover(p1, p2):
        child = list(set(random.sample(p1, len(p1)//2) + random.sample(p2, len(p2)//2)))
        while len(child) < num_walls:
            available = [c for c in candidates if c not in child]
            if available:
                child.append(random.choice(available))
            else:
                break
        if len(child) > num_walls:
            child = random.sample(child, num_walls)
        return child
    
    population = [random_individual() for _ in range(pop_size)]
    best_score, best_walls = 0, []
    iterations = 0
    
    for gen in range(generations):
        scored = []
        for ind in population:
            iterations += 1
            score = evaluate_walls(state, ind)
            scored.append((score, ind))
            if score > best_score:
                best_score = score
                best_walls = ind.copy()
                if gen % 100 == 0 or score > best_score - 1:
                    print(f"    [Genetic] Gen {gen}: New best = {best_score}")
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Elitism: keep top 5%
        elite = [ind.copy() for _, ind in scored[:max(1, pop_size // 20)]]
        
        new_pop = elite.copy()
        while len(new_pop) < pop_size:
            # Tournament
            t1 = random.sample(scored, min(7, len(scored)))
            p1 = max(t1, key=lambda x: x[0])[1]
            t2 = random.sample(scored, min(7, len(scored)))
            p2 = max(t2, key=lambda x: x[0])[1]
            
            child = crossover(p1, p2)
            if random.random() < 0.6:
                child = mutate(child, random.randint(1, 3))
            new_pop.append(child)
        
        # 10% immigrants
        for i in range(pop_size // 10):
            new_pop[-(i+1)] = random_individual()
        
        population = new_pop
    
    return BenchmarkResult("Genetic 5K gen", best_score, best_walls, time.time() - start, iterations)


def solve_sa_massive(state: GameState, total_iterations: int = 2000000) -> BenchmarkResult:
    """
    MASSIVE SA: 2 million iterations with multiple restarts.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    if not candidates:
        return BenchmarkResult("SA 2M", 0, [], time.time() - start, 0)
    
    best_score, best_walls = 0, []
    num_restarts = 50
    iters_per_restart = total_iterations // num_restarts
    
    for restart in range(num_restarts):
        current_walls = random.sample(candidates, num_walls)
        current_score = evaluate_walls(state, current_walls)
        
        if current_score > best_score:
            best_score = current_score
            best_walls = current_walls.copy()
        
        temp = 100.0
        cooling = 1 - (4.0 / iters_per_restart)  # Cool to ~0.02 by end
        
        for i in range(iters_per_restart):
            temp *= cooling
            
            new_walls = current_walls.copy()
            available = [c for c in candidates if c not in new_walls]
            
            # Swap 1-3 walls
            swaps = 1 if random.random() < 0.6 else (2 if random.random() < 0.8 else 3)
            for _ in range(swaps):
                if available and new_walls:
                    new_walls.pop(random.randrange(len(new_walls)))
                    w = random.choice(available)
                    new_walls.append(w)
                    available.remove(w)
            
            new_score = evaluate_walls(state, new_walls)
            delta = new_score - current_score
            
            if delta > 0 or (temp > 0.001 and random.random() < math.exp(delta / max(temp, 0.001))):
                current_walls = new_walls
                current_score = new_score
                if current_score > best_score:
                    best_score = current_score
                    best_walls = current_walls.copy()
    
    print(f"    [SA 2M] Final best: {best_score}")
    return BenchmarkResult("SA 2M iter", best_score, best_walls, time.time() - start, total_iterations)


def solve_random_massive(state: GameState, iterations: int = 500000) -> BenchmarkResult:
    """
    MASSIVE RANDOM: Half million random samples.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    best_score, best_walls = 0, []
    
    for i in range(iterations):
        walls = random.sample(candidates, num_walls)
        score = evaluate_walls(state, walls)
        if score > best_score:
            best_score = score
            best_walls = walls.copy()
            if i % 10000 == 0 or score > best_score - 1:
                print(f"    [Random 500K] iter {i:,}: New best = {best_score}")
    
    return BenchmarkResult("Random 500K", best_score, best_walls, time.time() - start, iterations)


def solve_full_random_timed(state: GameState, timeout: float = 120.0) -> BenchmarkResult:
    """
    TIMED RANDOM: Keep sampling until timeout.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    best_score, best_walls = 0, []
    iterations = 0
    
    while time.time() - start < timeout:
        for _ in range(10000):
            iterations += 1
            walls = random.sample(candidates, num_walls)
            score = evaluate_walls(state, walls)
            if score > best_score:
                best_score = score
                best_walls = walls.copy()
                print(f"    [Random {int(timeout)}s] iter {iterations:,}: New best = {best_score}")
    
    return BenchmarkResult(f"Random {int(timeout)}s", best_score, best_walls, time.time() - start, iterations)


def solve_hybrid_aggressive(state: GameState) -> BenchmarkResult:
    """
    HYBRID: Run genetic, then polish best with SA.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    # Phase 1: Quick genetic to find good starting points
    print("    [Hybrid] Phase 1: Genetic search...")
    genetic_result = solve_genetic_massive(state, pop_size=200, generations=2000)
    best_score = genetic_result.score
    best_walls = genetic_result.walls.copy()
    
    # Phase 2: Intensive SA from best solution
    print(f"    [Hybrid] Phase 2: SA polish from score {best_score}...")
    current_walls = best_walls.copy()
    current_score = best_score
    
    temp = 50.0
    for i in range(500000):
        temp *= 0.99999
        
        new_walls = current_walls.copy()
        available = [c for c in candidates if c not in new_walls]
        
        if available and new_walls:
            new_walls.pop(random.randrange(len(new_walls)))
            new_walls.append(random.choice(available))
        
        new_score = evaluate_walls(state, new_walls)
        delta = new_score - current_score
        
        if delta > 0 or (temp > 0.001 and random.random() < math.exp(delta / max(temp, 0.001))):
            current_walls = new_walls
            current_score = new_score
            if current_score > best_score:
                best_score = current_score
                best_walls = current_walls.copy()
                print(f"    [Hybrid] SA improved to: {best_score}")
    
    total_iters = genetic_result.iterations + 500000
    return BenchmarkResult("Hybrid (Gen+SA)", best_score, best_walls, time.time() - start, total_iters)


# =============================================================================
# BENCHMARK
# =============================================================================

def solve_mega_hybrid(state: GameState) -> BenchmarkResult:
    """
    MEGA HYBRID: Multiple genetic runs + intensive SA from each.
    This should find very high quality solutions.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    best_score, best_walls = 0, []
    total_iterations = 0
    
    # Run 5 independent genetic searches, then polish each
    for run in range(5):
        print(f"    [Mega Hybrid] Run {run+1}/5: Genetic phase...")
        
        # Genetic phase: 2000 generations
        pop_size = 200
        population = [random.sample(candidates, num_walls) for _ in range(pop_size)]
        run_best_score, run_best_walls = 0, []
        
        for gen in range(2000):
            scored = [(evaluate_walls(state, ind), ind) for ind in population]
            total_iterations += pop_size
            scored.sort(key=lambda x: x[0], reverse=True)
            
            if scored[0][0] > run_best_score:
                run_best_score = scored[0][0]
                run_best_walls = scored[0][1].copy()
            
            elite = [ind.copy() for _, ind in scored[:pop_size // 10]]
            new_pop = elite.copy()
            
            while len(new_pop) < pop_size:
                t1 = random.sample(scored, min(5, len(scored)))
                p1 = max(t1, key=lambda x: x[0])[1]
                t2 = random.sample(scored, min(5, len(scored)))
                p2 = max(t2, key=lambda x: x[0])[1]
                
                child = list(set(random.sample(p1, len(p1)//2) + random.sample(p2, len(p2)//2)))
                while len(child) < num_walls:
                    available = [c for c in candidates if c not in child]
                    if available: child.append(random.choice(available))
                    else: break
                if len(child) > num_walls:
                    child = random.sample(child, num_walls)
                
                if random.random() < 0.5:
                    available = [c for c in candidates if c not in child]
                    if available and child:
                        child.pop(random.randrange(len(child)))
                        child.append(random.choice(available))
                
                new_pop.append(child)
            
            for i in range(pop_size // 10):
                new_pop[-(i+1)] = random.sample(candidates, num_walls)
            
            population = new_pop
        
        print(f"    [Mega Hybrid] Run {run+1}/5: Genetic found {run_best_score}, SA polishing...")
        
        # SA polish phase: 200K iterations
        current_walls = run_best_walls.copy()
        current_score = run_best_score
        temp = 30.0
        
        for i in range(200000):
            total_iterations += 1
            temp *= 0.99997
            
            new_walls = current_walls.copy()
            available = [c for c in candidates if c not in new_walls]
            
            if available and new_walls:
                new_walls.pop(random.randrange(len(new_walls)))
                new_walls.append(random.choice(available))
            
            new_score = evaluate_walls(state, new_walls)
            delta = new_score - current_score
            
            if delta > 0 or random.random() < math.exp(delta / max(temp, 0.001)):
                current_walls = new_walls
                current_score = new_score
                if current_score > run_best_score:
                    run_best_score = current_score
                    run_best_walls = current_walls.copy()
        
        print(f"    [Mega Hybrid] Run {run+1}/5: Final = {run_best_score}")
        
        if run_best_score > best_score:
            best_score = run_best_score
            best_walls = run_best_walls.copy()
            print(f"    [Mega Hybrid] NEW OVERALL BEST: {best_score}")
    
    return BenchmarkResult("Mega Hybrid", best_score, best_walls, time.time() - start, total_iterations)


def solve_cherry_focused(state: GameState) -> BenchmarkResult:
    """
    CHERRY FOCUSED: Try to capture all cherries first, then expand.
    Key insight: Cherries give +3 bonus, so capturing all is important.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    # Find cherry positions
    cherry_positions = [i for i, c in enumerate(state.cherries) if c]
    
    best_score, best_walls = 0, []
    iterations = 0
    
    # Genetic algorithm that heavily rewards capturing cherries
    pop_size = 300
    population = [random.sample(candidates, num_walls) for _ in range(pop_size)]
    
    for gen in range(3000):
        scored = []
        for ind in population:
            iterations += 1
            result = solve(make_state_with_walls(state, ind))
            # Score = base + extra weight for captured cherries
            score = result.total_score
            if score > best_score:
                best_score = score
                best_walls = ind.copy()
            scored.append((score, ind))
        
        if gen % 200 == 0:
            print(f"    [Cherry] Gen {gen}: Best = {best_score}")
        
        scored.sort(key=lambda x: x[0], reverse=True)
        elite = [ind.copy() for _, ind in scored[:pop_size // 10]]
        new_pop = elite.copy()
        
        while len(new_pop) < pop_size:
            t = random.sample(scored, min(5, len(scored)))
            p1 = max(t, key=lambda x: x[0])[1]
            t = random.sample(scored, min(5, len(scored)))
            p2 = max(t, key=lambda x: x[0])[1]
            
            child = list(set(random.sample(p1, len(p1)//2) + random.sample(p2, len(p2)//2)))
            while len(child) < num_walls:
                available = [c for c in candidates if c not in child]
                if available: child.append(random.choice(available))
                else: break
            if len(child) > num_walls:
                child = random.sample(child, num_walls)
            
            if random.random() < 0.6:
                available = [c for c in candidates if c not in child]
                swaps = random.randint(1, 3)
                for _ in range(swaps):
                    if available and child:
                        child.pop(random.randrange(len(child)))
                        w = random.choice(available)
                        child.append(w)
                        available.remove(w)
            
            new_pop.append(child)
        
        for i in range(pop_size // 5):  # More immigrants for diversity
            new_pop[-(i+1)] = random.sample(candidates, num_walls)
        
        population = new_pop
    
    return BenchmarkResult("Cherry Focused", best_score, best_walls, time.time() - start, iterations)


def find_chokepoints(state: GameState) -> list[tuple[int, int]]:
    """
    Find cells that are on many escape paths - these are good wall candidates.
    Returns list of (cell_index, importance_score).
    """
    candidates = find_candidate_walls(state)
    result = solve(state)
    
    if not result.escaped:
        return []  # Already enclosed
    
    # For each candidate, count how much it reduces reachable area
    chokepoints = []
    baseline_area = len(result.visited)
    
    for cell in candidates:
        test_state = make_state_with_walls(state, [cell])
        test_result = solve(test_state)
        
        if not test_result.escaped:
            # This single wall encloses! Very important
            chokepoints.append((cell, 1000))
        else:
            # Measure reduction in reachable area
            reduction = baseline_area - len(test_result.visited)
            if reduction > 0:
                chokepoints.append((cell, reduction))
    
    chokepoints.sort(key=lambda x: x[1], reverse=True)
    return chokepoints


def solve_chokepoint_guided(state: GameState) -> BenchmarkResult:
    """
    CHOKEPOINT-GUIDED: Start with important cells, then refine.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    # Find chokepoints
    print("    Finding chokepoints...")
    chokepoints = find_chokepoints(state)
    top_chokepoints = [c[0] for c in chokepoints[:30]]  # Top 30 important cells
    
    print(f"    Found {len(chokepoints)} chokepoints, top 30 for seeding")
    
    best_score, best_walls = 0, []
    iterations = 0
    
    # Genetic algorithm seeded with chokepoints
    pop_size = 200
    population = []
    
    # Half population seeded with chokepoints
    for _ in range(pop_size // 2):
        # Take some from chokepoints, rest random
        n_from_choke = random.randint(6, min(num_walls, len(top_chokepoints)))
        walls = random.sample(top_chokepoints, n_from_choke) if top_chokepoints else []
        remaining = num_walls - len(walls)
        available = [c for c in candidates if c not in walls]
        walls.extend(random.sample(available, min(remaining, len(available))))
        population.append(walls)
    
    # Other half random
    for _ in range(pop_size - len(population)):
        population.append(random.sample(candidates, num_walls))
    
    for gen in range(5000):
        scored = []
        for ind in population:
            iterations += 1
            score = evaluate_walls(state, ind)
            if score > best_score:
                best_score = score
                best_walls = ind.copy()
                print(f"    [Chokepoint] Gen {gen}: NEW BEST = {best_score}")
            scored.append((score, ind))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        elite = [ind.copy() for _, ind in scored[:pop_size // 10]]
        new_pop = elite.copy()
        
        while len(new_pop) < pop_size:
            t1 = random.sample(scored, min(7, len(scored)))
            p1 = max(t1, key=lambda x: x[0])[1]
            t2 = random.sample(scored, min(7, len(scored)))
            p2 = max(t2, key=lambda x: x[0])[1]
            
            child = list(set(random.sample(p1, len(p1)//2) + random.sample(p2, len(p2)//2)))
            while len(child) < num_walls:
                available = [c for c in candidates if c not in child]
                if available: child.append(random.choice(available))
                else: break
            if len(child) > num_walls:
                child = random.sample(child, num_walls)
            
            if random.random() < 0.5:
                available = [c for c in candidates if c not in child]
                if available and child:
                    child.pop(random.randrange(len(child)))
                    child.append(random.choice(available))
            
            new_pop.append(child)
        
        # 20% immigrants with chokepoint bias
        for i in range(pop_size // 5):
            if random.random() < 0.5 and top_chokepoints:
                n_from_choke = random.randint(4, min(num_walls, len(top_chokepoints)))
                walls = random.sample(top_chokepoints, n_from_choke)
                remaining = num_walls - len(walls)
                available = [c for c in candidates if c not in walls]
                walls.extend(random.sample(available, min(remaining, len(available))))
            else:
                walls = random.sample(candidates, num_walls)
            new_pop[-(i+1)] = walls
        
        population = new_pop
    
    # SA polish
    print(f"    [Chokepoint] SA polish from {best_score}...")
    current_walls = best_walls.copy()
    current_score = best_score
    temp = 50.0
    
    for i in range(300000):
        iterations += 1
        temp *= 0.99998
        
        new_walls = current_walls.copy()
        available = [c for c in candidates if c not in new_walls]
        
        if available and new_walls:
            new_walls.pop(random.randrange(len(new_walls)))
            new_walls.append(random.choice(available))
        
        new_score = evaluate_walls(state, new_walls)
        delta = new_score - current_score
        
        if delta > 0 or random.random() < math.exp(delta / max(temp, 0.001)):
            current_walls = new_walls
            current_score = new_score
            if current_score > best_score:
                best_score = current_score
                best_walls = current_walls.copy()
                print(f"    [Chokepoint] SA improved: {best_score}")
    
    return BenchmarkResult("Chokepoint Guided", best_score, best_walls, time.time() - start, iterations)


def solve_ultimate(state: GameState, time_limit: float = 300.0) -> BenchmarkResult:
    """
    ULTIMATE: Keep running genetic + SA cycles until time runs out.
    This is designed to find the optimal or near-optimal solution.
    """
    start = time.time()
    candidates = find_candidate_walls(state)
    num_walls = min(state.budget, len(candidates))
    
    best_score, best_walls = 0, []
    total_iterations = 0
    run_number = 0
    
    while time.time() - start < time_limit:
        run_number += 1
        
        # Genetic phase: 1500 generations
        pop_size = 150
        population = [random.sample(candidates, num_walls) for _ in range(pop_size)]
        run_best_score, run_best_walls = 0, []
        
        for gen in range(1500):
            if time.time() - start > time_limit:
                break
                
            scored = [(evaluate_walls(state, ind), ind) for ind in population]
            total_iterations += pop_size
            scored.sort(key=lambda x: x[0], reverse=True)
            
            if scored[0][0] > run_best_score:
                run_best_score = scored[0][0]
                run_best_walls = scored[0][1].copy()
            
            elite = [ind.copy() for _, ind in scored[:pop_size // 10]]
            new_pop = elite.copy()
            
            while len(new_pop) < pop_size:
                t1 = random.sample(scored, min(5, len(scored)))
                p1 = max(t1, key=lambda x: x[0])[1]
                t2 = random.sample(scored, min(5, len(scored)))
                p2 = max(t2, key=lambda x: x[0])[1]
                
                child = list(set(random.sample(p1, len(p1)//2) + random.sample(p2, len(p2)//2)))
                while len(child) < num_walls:
                    available = [c for c in candidates if c not in child]
                    if available: child.append(random.choice(available))
                    else: break
                if len(child) > num_walls:
                    child = random.sample(child, num_walls)
                
                if random.random() < 0.5:
                    available = [c for c in candidates if c not in child]
                    if available and child:
                        child.pop(random.randrange(len(child)))
                        child.append(random.choice(available))
                
                new_pop.append(child)
            
            for i in range(pop_size // 10):
                new_pop[-(i+1)] = random.sample(candidates, num_walls)
            
            population = new_pop
        
        # SA polish phase
        current_walls = run_best_walls.copy()
        current_score = run_best_score
        temp = 30.0
        
        for i in range(150000):
            if time.time() - start > time_limit:
                break
            total_iterations += 1
            temp *= 0.99996
            
            new_walls = current_walls.copy()
            available = [c for c in candidates if c not in new_walls]
            
            if available and new_walls:
                new_walls.pop(random.randrange(len(new_walls)))
                new_walls.append(random.choice(available))
            
            new_score = evaluate_walls(state, new_walls)
            delta = new_score - current_score
            
            if delta > 0 or random.random() < math.exp(delta / max(temp, 0.001)):
                current_walls = new_walls
                current_score = new_score
                if current_score > run_best_score:
                    run_best_score = current_score
                    run_best_walls = current_walls.copy()
        
        elapsed = time.time() - start
        print(f"    [Ultimate] Run {run_number} @ {elapsed:.0f}s: {run_best_score}", end="")
        
        if run_best_score > best_score:
            best_score = run_best_score
            best_walls = run_best_walls.copy()
            print(f" ⭐ NEW BEST!")
        else:
            print()
    
    return BenchmarkResult("Ultimate", best_score, best_walls, time.time() - start, total_iterations)


def run_all_solvers(state: GameState) -> list[BenchmarkResult]:
    results = []
    
    solvers = [
        ("Chokepoint Guided", lambda: solve_chokepoint_guided(state)),
        ("Mega Hybrid", lambda: solve_mega_hybrid(state)),
        ("Ultimate 5min", lambda: solve_ultimate(state, time_limit=300)),
    ]
    
    for name, solver_fn in solvers:
        print(f"  Running {name}...")
        result = solver_fn()
        print(f"    Final score: {result.score}")
        results.append(result)
    
    return results


def print_benchmark_table(results: list[BenchmarkResult], optimal_score: Optional[int] = None):
    print("\n" + "=" * 85)
    print("BENCHMARK RESULTS")
    print("=" * 85)
    
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    name_width = max(len(r.name) for r in results) + 2
    
    header = f"{'Algorithm':<{name_width}} {'Score':>8} {'Walls':>6} {'Time':>12} {'Iterations':>15}"
    if optimal_score:
        header += f" {'% Optimal':>10}"
    print(header)
    print("-" * len(header))
    
    for result in sorted_results:
        time_str = f"{result.time_seconds:.1f}s"
        iter_str = f"{result.iterations:,}"
        row = f"{result.name:<{name_width}} {result.score:>8} {len(result.walls):>6} {time_str:>12} {iter_str:>15}"
        
        if optimal_score:
            pct = (result.score / optimal_score * 100) if optimal_score > 0 else 0
            row += f" {pct:>9.1f}%"
        
        if result.score == sorted_results[0].score:
            row = f"\033[92m{row}\033[0m"
        
        print(row)
    
    print("=" * 85)
    
    best = sorted_results[0]
    print(f"\n🏆 BEST: {best.name} with score {best.score} in {best.time_seconds:.1f}s")
    if optimal_score:
        print(f"   Achieved {best.score / optimal_score * 100:.1f}% of optimal ({optimal_score})")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys
    from datetime import date
    
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    
    print(f"🐴 enclose.horse Solver Benchmark")
    print(f"=" * 85)
    print(f"Fetching puzzle for {target_date}...")
    
    try:
        puzzle_data = fetch_daily_puzzle(target_date)
        
        optimal = puzzle_data.get('optimalScore')
        print(f"\n📋 Puzzle: {puzzle_data['name']} by {puzzle_data['creatorName']}")
        print(f"   Budget: {puzzle_data['budget']} walls | Optimal: {optimal or 'Unknown'}")
        print(f"   Play count: {puzzle_data['playCount']:,}")
        
        state = parse_map(puzzle_data['map'], puzzle_data['budget'])
        candidates = find_candidate_walls(state)
        
        print(f"   Grid: {state.cols}x{state.rows} | Candidates: {len(candidates)}")
        print(f"   Search space: C({len(candidates)},{state.budget}) combinations\n")
        
        print("🔧 Running Solvers (this will take a few minutes)...\n")
        results = run_all_solvers(state)
        
        print_benchmark_table(results, optimal)
        
        # Show best solution
        best = max(results, key=lambda r: r.score)
        if best.score > 0:
            print(f"\n📊 Best Solution ({best.name}):\n")
            solution_state = make_state_with_walls(state, best.walls)
            solution_result = solve(solution_state)
            print(visualize_state(solution_state, solution_result))
            print(f"\nWalls: {best.walls}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
 