# enclose.horse - Complete Game Analysis

## Overview

**enclose.horse** is a puzzle game where you place walls to trap a horse in the largest possible enclosed area. The game has daily challenges and community-created levels.

Website: https://enclose.horse/

## Game Rules

1. **Objective**: Enclose the horse (🐴) in the biggest possible pen
2. **Mechanics**:
   - Click grass tiles to place walls
   - You have a limited wall budget
   - Horse can move in 4 directions (up, down, left, right) - NOT diagonally
   - Horse cannot move through water (`~`) or walls
   - If the horse can reach any edge of the map, it "escapes" and you score 0
   - Enclosed cherries (`C`) give +3 bonus points each
   - Portals connect distant cells - the horse can teleport through them
3. **Scoring**: `Score = Enclosed tiles + (Cherries × 3)`

## Map Format

Maps are stored as text with the following characters:
- `.` = Grass (walkable)
- `~` = Water (impassable)
- `H` = Horse starting position
- `C` = Cherry (bonus +3 when enclosed)
- `W` = Wall
- `0-9, a-z` = Portal pairs (same character = connected portals)

Example map:
```
~~..~~~.~~~~
~C.C.......~
..C......~..
.C.C~~..~~.~
~.~.~~.....~
~..........~
....~.~~...~
~...~~H~....
~...........
~.....~~...~
..~~..~~C.C~
~.~......C.~
~.......C.C~
~.~~.~.~...~
```

## Core Algorithm (The Solver)

The game uses a **BFS (Breadth-First Search)** flood-fill algorithm to determine:
1. Whether the horse is enclosed or can escape
2. The enclosed area size
3. The escape path if one exists

### Deobfuscated Solver Algorithm

```javascript
/**
 * Solves the enclose.horse puzzle
 * @param {number} cols - Grid width
 * @param {number} rows - Grid height  
 * @param {number[]} terrain - Array where 0=grass, 1=water
 * @param {boolean[]} walls - Array of wall positions (true = wall)
 * @param {boolean[]} cherries - Array of cherry positions
 * @param {number} playerIdx - Horse starting position (row * cols + col)
 * @param {(number|null)[]} portals - Portal connections (same number = connected)
 * @returns {Object} Result with escaped, visited cells, score, etc.
 */
function solve(cols, rows, terrain, walls, cherries, playerIdx, portals) {
    const wallCount = walls.filter(w => w).length;
    
    // Build portal lookup map
    const portalMap = new Map();
    if (portals) {
        for (let i = 0; i < portals.length; i++) {
            const channel = portals[i];
            if (channel !== null) {
                if (!portalMap.has(channel)) portalMap.set(channel, []);
                portalMap.get(channel).push(i);
            }
        }
    }
    
    // BFS setup
    const queue = [playerIdx];
    const visited = new Set([playerIdx]);
    const parent = new Map();  // For reconstructing escape path
    const distance = new Map([[playerIdx, 0]]);
    
    let escaped = false;
    let escapeCell = -1;
    let maxDistance = 0;
    
    const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]]; // left, right, up, down
    
    const tryVisit = (idx, fromIdx) => {
        if (!visited.has(idx) && !walls[idx] && terrain[idx] !== 1) {
            visited.add(idx);
            parent.set(idx, fromIdx);
            const dist = distance.get(fromIdx) + 1;
            distance.set(idx, dist);
            maxDistance = Math.max(maxDistance, dist);
            queue.push(idx);
        }
    };
    
    // BFS main loop
    while (queue.length > 0) {
        const current = queue.shift();
        const col = current % cols;
        const row = Math.floor(current / cols);
        
        // Check if reached edge (escape!)
        if (col === 0 || col === cols - 1 || row === 0 || row === rows - 1) {
            if (!escaped) {
                escaped = true;
                escapeCell = current;
            }
        }
        
        // Try all 4 directions
        for (const [dc, dr] of directions) {
            const newCol = col + dc;
            const newRow = row + dr;
            if (newCol >= 0 && newCol < cols && newRow >= 0 && newRow < rows) {
                const newIdx = newRow * cols + newCol;
                tryVisit(newIdx, current);
            }
        }
        
        // Try portal teleportation
        if (portals) {
            const channel = portals[current];
            if (channel !== null) {
                const portalExits = portalMap.get(channel) || [];
                for (const exit of portalExits) {
                    if (exit !== current) {
                        tryVisit(exit, current);
                    }
                }
            }
        }
    }
    
    // Reconstruct escape path
    const escapePath = [];
    if (escaped && escapeCell !== -1) {
        let cell = escapeCell;
        while (cell !== undefined) {
            escapePath.unshift(cell);
            cell = parent.get(cell);
        }
    }
    
    // Calculate cherry bonus (only if enclosed)
    let cherryBonus = 0;
    if (!escaped && cherries) {
        for (const cell of visited) {
            if (cherries[cell]) {
                cherryBonus += 3;
            }
        }
    }
    
    const enclosedArea = escaped ? 0 : visited.size;
    
    return {
        wallCount,
        enclosedArea,
        cherryBonus,
        totalScore: enclosedArea + cherryBonus,
        visited,
        escaped,
        escapePath,
        distance,
        maxDistance
    };
}
```

## API Endpoints

Base URL: `https://enclose.horse/api`

### Get Daily Puzzle
```
GET /api/daily/{date}
```
Response:
```json
{
    "id": "ZtiI9g",
    "map": "~~..~~~.~~~~\n~C.C.......~\n...",
    "budget": 12,
    "name": "Five of Cherries",
    "creatorName": "Shivers",
    "playCount": 23381,
    "isDaily": true,
    "dailyDate": "2026-01-07",
    "dayNumber": 9,
    "optimalScore": 66
}
```

### Submit Solution
```
POST /api/levels/{levelId}/submit
Headers: 
  Content-Type: application/json
  x-player-id: {uuid}
Body: { "walls": [5, 12, 23, ...], "name": "PlayerName" }
```

### Get Level Stats/Leaderboard
```
GET /api/levels/{levelId}/stats
Headers: x-player-id: {uuid}
```

### Get Specific Submission
```
GET /api/levels/submission/{submissionId}
```

### Vote on Level
```
POST /api/community/levels/{levelId}/vote
Headers: x-player-id: {uuid}
Body: { "vote": 1 } // 1 = upvote, -1 = downvote, 0 = remove vote
```

## Daily Levels Info

Daily levels are pre-loaded in the HTML:
```javascript
window.__DAILY_LEVELS__ = [
    {"id":"xPt_fu","date":"2026-01-08","dayNumber":10,"optimalScore":73},
    {"id":"ZtiI9g","date":"2026-01-07","dayNumber":9,"optimalScore":66},
    // ...
];
```

## Building a Solver

### Strategy for Optimal Solution

The problem is essentially: **Find the wall placement that maximizes the enclosed area while using at most `budget` walls.**

This is a challenging optimization problem because:
1. The search space is huge: C(n, budget) where n = number of grass cells
2. Walls must form a complete enclosure (no escape routes)

### Approaches

1. **Brute Force** (small grids only): Try all combinations of wall placements
2. **Greedy**: Place walls on cells that block the most escape routes
3. **BFS from Edges**: Find minimum cut between horse and all edges
4. **Min-Cut / Max-Flow**: Model as graph problem - find minimum walls to separate horse from edges

### Key Insight

The optimal strategy often involves:
1. Finding natural barriers (water, map edges)
2. Placing walls to complete an enclosure using these barriers
3. Maximizing interior area while minimizing walls used

### Helper Functions

```javascript
// Parse map string to game state
function parseMap(mapString, budget) {
    const lines = mapString.trim().split('\n');
    const rows = lines.length;
    const cols = lines[0].length;
    
    const terrain = [];
    const walls = [];
    const cherries = [];
    const portals = [];
    let playerIdx = -1;
    
    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            const idx = row * cols + col;
            const char = lines[row][col] || '.';
            
            if (char === 'H') {
                playerIdx = idx;
                terrain.push(0);
                walls.push(false);
                cherries.push(false);
                portals.push(null);
            } else if (char === 'C') {
                terrain.push(0);
                walls.push(false);
                cherries.push(true);
                portals.push(null);
            } else if (char === 'W') {
                terrain.push(0);
                walls.push(true);
                cherries.push(false);
                portals.push(null);
            } else if (char === '~') {
                terrain.push(1);
                walls.push(false);
                cherries.push(false);
                portals.push(null);
            } else if (/[0-9a-z]/.test(char)) {
                const channel = char >= '0' && char <= '9' 
                    ? char.charCodeAt(0) - 48 
                    : char.charCodeAt(0) - 97 + 10;
                terrain.push(0);
                walls.push(false);
                cherries.push(false);
                portals.push(channel);
            } else {
                terrain.push(0);
                walls.push(false);
                cherries.push(false);
                portals.push(null);
            }
        }
    }
    
    return { cols, rows, terrain, walls, cherries, portals, playerIdx, budget };
}

// Convert wall indices to submission format
function wallsToIndices(walls) {
    const indices = [];
    for (let i = 0; i < walls.length; i++) {
        if (walls[i]) indices.push(i);
    }
    return indices;
}
```

## Tech Stack

- **Frontend**: Vanilla JavaScript, HTML5 Canvas
- **Styling**: CSS with CSS variables for theming
- **Font**: Schoolbell (Google Fonts)
- **Backend**: REST API (likely Node.js based on patterns)
- **Rendering**: Canvas 2D with sprite sheets for tiles

## Themes

Available themes (stored in localStorage as `enclose_theme`):
- `default` - Green grass (#186b3b)
- `classic` - Dark green (#365022)
- `girl` - Purple (#7c507e)
- `hot` - Dark (#272727)

## Local Storage Keys

- `enclose_submissions` - Your solutions for each level
- `enclose_theme` - Selected theme
- `enclose_name` - Player name
- `enclose_animations` - Animation toggle
- `vote_{levelId}` - Your vote on each level
- `unusedWallsTipDismissed` - Whether to show the unused walls tip

---

## Next Steps for Building a Solver

1. Implement the `solve()` function in your preferred language
2. Model the problem as a graph optimization
3. Consider using:
   - A* search for finding good enclosures
   - Genetic algorithms for exploring the solution space
   - Monte Carlo Tree Search (MCTS)
4. Test against known optimal scores from daily puzzles

