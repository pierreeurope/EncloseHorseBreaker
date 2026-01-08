// Client-side solver using BFS flood fill to compute enclosed area

export interface PuzzleData {
  id: string;
  map: string;
  budget: number;
  name: string;
  creatorName: string;
  playCount: number;
  isDaily: boolean;
  dailyDate: string;
  dayNumber: number;
}

export interface StatsData {
  optimalScore: number;
  optimalWalls: number[];
}

export interface ParsedMap {
  cols: number;
  rows: number;
  terrain: number[];      // 0 = grass, 1 = water
  cherries: boolean[];
  playerIdx: number;
}

export function parseMap(mapString: string): ParsedMap {
  const lines = mapString.split('\n');
  const rows = lines.length;
  const cols = lines[0].length;
  const terrain: number[] = [];
  const cherries: boolean[] = [];
  let playerIdx = -1;

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const char = lines[row]?.[col] || '.';
      const idx = row * cols + col;
      
      if (char === 'H') {
        playerIdx = idx;
        terrain.push(0);
        cherries.push(false);
      } else if (char === 'C') {
        terrain.push(0);
        cherries.push(true);
      } else if (char === '~') {
        terrain.push(1);
        cherries.push(false);
      } else {
        terrain.push(0);
        cherries.push(false);
      }
    }
  }

  return { cols, rows, terrain, cherries, playerIdx };
}

export interface SolveResult {
  escaped: boolean;
  visited: Set<number>;
  area: number;
  cherryBonus: number;
  score: number;
}

export function solve(
  cols: number,
  rows: number,
  terrain: number[],
  walls: Set<number>,
  cherries: boolean[],
  playerIdx: number
): SolveResult {
  const visited = new Set<number>();
  const queue: number[] = [playerIdx];
  visited.add(playerIdx);
  let escaped = false;

  while (queue.length > 0) {
    const current = queue.shift()!;
    const col = current % cols;
    const row = Math.floor(current / cols);

    // Check if at boundary
    if (col === 0 || col === cols - 1 || row === 0 || row === rows - 1) {
      escaped = true;
    }

    // Check neighbors
    const neighbors = [
      { r: row - 1, c: col },
      { r: row + 1, c: col },
      { r: row, c: col - 1 },
      { r: row, c: col + 1 }
    ];

    for (const n of neighbors) {
      if (n.r < 0 || n.r >= rows || n.c < 0 || n.c >= cols) continue;
      const nIdx = n.r * cols + n.c;
      if (visited.has(nIdx)) continue;
      if (walls.has(nIdx)) continue;
      if (terrain[nIdx] === 1) continue; // Water
      visited.add(nIdx);
      queue.push(nIdx);
    }
  }

  if (escaped) {
    return { escaped: true, visited: new Set(), area: 0, cherryBonus: 0, score: 0 };
  }

  const area = visited.size;
  let cherryBonus = 0;
  visited.forEach(idx => {
    if (cherries[idx]) cherryBonus += 3;
  });

  return {
    escaped: false,
    visited,
    area,
    cherryBonus,
    score: area + cherryBonus
  };
}

// Fetch puzzle from API
export async function fetchPuzzle(date: string): Promise<PuzzleData> {
  const response = await fetch(`https://enclose.horse/api/daily/${date}`);
  if (!response.ok) throw new Error(`Failed to fetch puzzle: ${response.statusText}`);
  return response.json();
}

// Fetch optimal solution from API
export async function fetchStats(levelId: string): Promise<StatsData> {
  const response = await fetch(`https://enclose.horse/api/levels/${levelId}/stats`);
  if (!response.ok) throw new Error(`Failed to fetch stats: ${response.statusText}`);
  return response.json();
}

