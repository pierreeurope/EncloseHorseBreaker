import { useEffect, useRef, useMemo } from 'react';
import { solve } from '../solver';
import type { ParsedMap, SolveResult } from '../solver';

interface GameCanvasProps {
  parsedMap: ParsedMap;
  walls: number[];
  showSolution: boolean;
}

// Colors matching enclose.horse exactly
const COLORS = {
  // Grass colors
  grass: '#2d8a4e',
  grassLight: '#3a9d5c',
  grassDark: '#257a42',
  
  // Water colors (bright blue like the original)
  water: '#4a90d9',
  waterLight: '#5ba0e9',
  waterDark: '#3a80c9',
  
  // Wall colors (brown/tan like original)
  wall: '#c9a227',
  wallLight: '#d9b237',
  wallDark: '#a98217',
  wallBorder: '#8b6914',
  
  // Wheat colors (golden yellow)
  wheat: '#e8c833',
  wheatDark: '#d4b020',
  wheatStem: '#7d9a3a',
  
  // Grid lines
  gridLine: 'rgba(0, 0, 0, 0.2)',
  gridLineDark: 'rgba(0, 0, 0, 0.35)',
  
  // Cherry
  cherry: '#e53935',
  cherryHighlight: '#ff6659',
  cherryStem: '#4caf50',
};

export function GameCanvas({ parsedMap, walls, showSolution }: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  const wallSet = useMemo(() => new Set(walls), [walls]);
  
  const solveResult = useMemo<SolveResult>(() => {
    if (!showSolution) {
      return { escaped: true, visited: new Set(), area: 0, cherryBonus: 0, score: 0 };
    }
    return solve(
      parsedMap.cols,
      parsedMap.rows,
      parsedMap.terrain,
      wallSet,
      parsedMap.cherries,
      parsedMap.playerIdx
    );
  }, [parsedMap, wallSet, showSolution]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { cols, rows, terrain, cherries, playerIdx } = parsedMap;

    let tileSize = 32;
    let width = 0;
    let height = 0;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const maxWidth = Math.min(window.innerWidth - 32, 700);
      const maxHeight = Math.min(window.innerHeight - 250, 600);
      
      tileSize = Math.min(
        Math.floor(maxWidth / cols),
        Math.floor(maxHeight / rows),
        40
      );
      
      width = cols * tileSize;
      height = rows * tileSize;
      
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
    };

    const drawGrass = (x: number, y: number, size: number, isEnclosed: boolean) => {
      // Base grass
      ctx.fillStyle = isEnclosed ? COLORS.grassLight : COLORS.grass;
      ctx.fillRect(x, y, size, size);
      
      // Subtle texture
      ctx.fillStyle = isEnclosed ? COLORS.grass : COLORS.grassDark;
      for (let i = 0; i < 4; i++) {
        const gx = x + (Math.random() * 0.8 + 0.1) * size;
        const gy = y + (Math.random() * 0.8 + 0.1) * size;
        ctx.fillRect(gx, gy, 1, 2);
      }
    };

    const drawWater = (x: number, y: number, size: number, time: number, col: number, row: number) => {
      // Base water color
      ctx.fillStyle = COLORS.water;
      ctx.fillRect(x, y, size, size);
      
      // Animated wave pattern
      const phase = time * 0.003 + col * 0.5 + row * 0.3;
      ctx.fillStyle = COLORS.waterLight;
      
      // Draw wave highlights
      for (let i = 0; i < 3; i++) {
        const waveY = y + size * (0.3 + i * 0.25);
        const waveX = x + Math.sin(phase + i * 1.5) * size * 0.1;
        ctx.beginPath();
        ctx.moveTo(waveX, waveY);
        ctx.quadraticCurveTo(
          waveX + size * 0.25, waveY - size * 0.05,
          waveX + size * 0.5, waveY
        );
        ctx.quadraticCurveTo(
          waveX + size * 0.75, waveY + size * 0.05,
          waveX + size, waveY
        );
        ctx.lineTo(waveX + size, waveY + size * 0.1);
        ctx.lineTo(waveX, waveY + size * 0.1);
        ctx.closePath();
        ctx.fill();
      }
    };

    const drawWheat = (x: number, y: number, size: number, time: number, idx: number) => {
      // Draw multiple wheat stalks
      const numStalks = 5;
      const basePhase = time * 0.002 + idx * 0.7;
      
      for (let i = 0; i < numStalks; i++) {
        const stalkX = x + size * (0.15 + (i / numStalks) * 0.7);
        const sway = Math.sin(basePhase + i * 0.5) * size * 0.05;
        const stalkHeight = size * (0.5 + Math.random() * 0.15);
        
        // Stem
        ctx.strokeStyle = COLORS.wheatStem;
        ctx.lineWidth = Math.max(1, size * 0.04);
        ctx.beginPath();
        ctx.moveTo(stalkX, y + size);
        ctx.quadraticCurveTo(
          stalkX + sway,
          y + size - stalkHeight * 0.5,
          stalkX + sway * 1.5,
          y + size - stalkHeight
        );
        ctx.stroke();
        
        // Wheat head
        ctx.fillStyle = COLORS.wheat;
        const headX = stalkX + sway * 1.5;
        const headY = y + size - stalkHeight;
        const headWidth = size * 0.08;
        const headHeight = size * 0.2;
        
        ctx.beginPath();
        ctx.ellipse(headX, headY, headWidth, headHeight, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Wheat kernels (small lines)
        ctx.strokeStyle = COLORS.wheatDark;
        ctx.lineWidth = 1;
        for (let k = 0; k < 4; k++) {
          const kernelY = headY - headHeight * 0.6 + k * headHeight * 0.35;
          ctx.beginPath();
          ctx.moveTo(headX - headWidth * 0.8, kernelY);
          ctx.lineTo(headX - headWidth * 1.5, kernelY - size * 0.03);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(headX + headWidth * 0.8, kernelY);
          ctx.lineTo(headX + headWidth * 1.5, kernelY - size * 0.03);
          ctx.stroke();
        }
      }
    };

    const drawWall = (x: number, y: number, size: number) => {
      const padding = size * 0.08;
      const wallX = x + padding;
      const wallY = y + padding;
      const wallSize = size - padding * 2;
      
      // Main wall body
      ctx.fillStyle = COLORS.wall;
      ctx.fillRect(wallX, wallY, wallSize, wallSize);
      
      // Top and left highlight
      ctx.fillStyle = COLORS.wallLight;
      ctx.fillRect(wallX, wallY, wallSize, wallSize * 0.15);
      ctx.fillRect(wallX, wallY, wallSize * 0.15, wallSize);
      
      // Bottom and right shadow
      ctx.fillStyle = COLORS.wallDark;
      ctx.fillRect(wallX, wallY + wallSize * 0.85, wallSize, wallSize * 0.15);
      ctx.fillRect(wallX + wallSize * 0.85, wallY, wallSize * 0.15, wallSize);
      
      // Border
      ctx.strokeStyle = COLORS.wallBorder;
      ctx.lineWidth = 1;
      ctx.strokeRect(wallX, wallY, wallSize, wallSize);
      
      // Brick pattern
      ctx.strokeStyle = COLORS.wallBorder;
      ctx.lineWidth = 1;
      
      // Horizontal lines
      ctx.beginPath();
      ctx.moveTo(wallX, wallY + wallSize * 0.33);
      ctx.lineTo(wallX + wallSize, wallY + wallSize * 0.33);
      ctx.moveTo(wallX, wallY + wallSize * 0.66);
      ctx.lineTo(wallX + wallSize, wallY + wallSize * 0.66);
      ctx.stroke();
      
      // Vertical lines (offset per row)
      ctx.beginPath();
      ctx.moveTo(wallX + wallSize * 0.5, wallY);
      ctx.lineTo(wallX + wallSize * 0.5, wallY + wallSize * 0.33);
      ctx.moveTo(wallX + wallSize * 0.25, wallY + wallSize * 0.33);
      ctx.lineTo(wallX + wallSize * 0.25, wallY + wallSize * 0.66);
      ctx.moveTo(wallX + wallSize * 0.75, wallY + wallSize * 0.33);
      ctx.lineTo(wallX + wallSize * 0.75, wallY + wallSize * 0.66);
      ctx.moveTo(wallX + wallSize * 0.5, wallY + wallSize * 0.66);
      ctx.lineTo(wallX + wallSize * 0.5, wallY + wallSize);
      ctx.stroke();
    };

    const drawHorse = (x: number, y: number, size: number, time: number) => {
      const cx = x + size * 0.5;
      const cy = y + size * 0.55;
      const s = size * 0.35;
      
      // Subtle idle animation
      const bounce = Math.sin(time * 0.003) * s * 0.05;
      
      ctx.save();
      ctx.translate(cx, cy + bounce);
      
      // Body (ellipse)
      ctx.fillStyle = '#5d4037';
      ctx.beginPath();
      ctx.ellipse(0, 0, s * 0.9, s * 0.55, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Head
      ctx.beginPath();
      ctx.ellipse(-s * 0.65, -s * 0.35, s * 0.45, s * 0.35, -0.3, 0, Math.PI * 2);
      ctx.fill();
      
      // Snout
      ctx.fillStyle = '#6d5047';
      ctx.beginPath();
      ctx.ellipse(-s * 0.95, -s * 0.2, s * 0.22, s * 0.18, -0.2, 0, Math.PI * 2);
      ctx.fill();
      
      // Eye
      ctx.fillStyle = '#000';
      ctx.beginPath();
      ctx.arc(-s * 0.55, -s * 0.42, s * 0.08, 0, Math.PI * 2);
      ctx.fill();
      
      // Eye highlight
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(-s * 0.53, -s * 0.44, s * 0.03, 0, Math.PI * 2);
      ctx.fill();
      
      // Ears
      ctx.fillStyle = '#5d4037';
      ctx.beginPath();
      ctx.moveTo(-s * 0.45, -s * 0.55);
      ctx.lineTo(-s * 0.55, -s * 0.85);
      ctx.lineTo(-s * 0.35, -s * 0.6);
      ctx.closePath();
      ctx.fill();
      
      ctx.beginPath();
      ctx.moveTo(-s * 0.3, -s * 0.55);
      ctx.lineTo(-s * 0.25, -s * 0.8);
      ctx.lineTo(-s * 0.15, -s * 0.55);
      ctx.closePath();
      ctx.fill();
      
      // Mane
      ctx.fillStyle = '#3e2723';
      ctx.beginPath();
      ctx.moveTo(-s * 0.35, -s * 0.6);
      ctx.quadraticCurveTo(-s * 0.1, -s * 0.85, s * 0.15, -s * 0.55);
      ctx.quadraticCurveTo(s * 0.2, -s * 0.3, s * 0.1, 0);
      ctx.quadraticCurveTo(-s * 0.1, -s * 0.25, -s * 0.35, -s * 0.6);
      ctx.fill();
      
      // Legs
      ctx.fillStyle = '#5d4037';
      const legWidth = s * 0.14;
      const legHeight = s * 0.45;
      [-s * 0.5, -s * 0.2, s * 0.15, s * 0.45].forEach((legX, i) => {
        const legBounce = Math.sin(time * 0.004 + i * 0.8) * s * 0.03;
        ctx.fillRect(legX - legWidth / 2, s * 0.35, legWidth, legHeight + legBounce);
        // Hoof
        ctx.fillStyle = '#3e2723';
        ctx.fillRect(legX - legWidth / 2 - 1, s * 0.35 + legHeight + legBounce - s * 0.08, legWidth + 2, s * 0.1);
        ctx.fillStyle = '#5d4037';
      });
      
      // Tail
      ctx.fillStyle = '#3e2723';
      const tailSway = Math.sin(time * 0.004) * s * 0.15;
      ctx.beginPath();
      ctx.moveTo(s * 0.8, -s * 0.1);
      ctx.quadraticCurveTo(s * 1.1 + tailSway, s * 0.2, s * 0.95 + tailSway, s * 0.5);
      ctx.quadraticCurveTo(s * 0.75, s * 0.3, s * 0.8, -s * 0.1);
      ctx.fill();
      
      ctx.restore();
    };

    const drawCherry = (x: number, y: number, size: number, time: number) => {
      const cx = x + size * 0.5;
      const cy = y + size * 0.6;
      const r = size * 0.22;
      const bounce = Math.sin(time * 0.004) * size * 0.02;
      
      // Stem
      ctx.strokeStyle = COLORS.cherryStem;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy - r + bounce);
      ctx.quadraticCurveTo(cx + r * 0.5, cy - r * 2, cx + r * 0.3, cy - r * 2.5 + bounce);
      ctx.stroke();
      
      // Cherry body
      ctx.fillStyle = COLORS.cherry;
      ctx.beginPath();
      ctx.arc(cx, cy + bounce, r, 0, Math.PI * 2);
      ctx.fill();
      
      // Highlight
      ctx.fillStyle = COLORS.cherryHighlight;
      ctx.beginPath();
      ctx.arc(cx - r * 0.3, cy - r * 0.3 + bounce, r * 0.35, 0, Math.PI * 2);
      ctx.fill();
    };

    const draw = (timestamp: number) => {
      timeRef.current = timestamp;
      
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      // Draw all cells
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const idx = row * cols + col;
          const x = col * tileSize;
          const y = row * tileSize;
          const isWall = wallSet.has(idx);
          const isWater = terrain[idx] === 1;
          const isCherry = cherries[idx];
          const isHorse = idx === playerIdx;
          const isEnclosed = solveResult.visited.has(idx);

          // Draw base terrain
          if (isWater) {
            drawWater(x, y, tileSize, timestamp, col, row);
          } else {
            drawGrass(x, y, tileSize, isEnclosed && showSolution);
            
            // Draw wheat on enclosed grass
            if (isEnclosed && showSolution && !isWall && !isHorse) {
              drawWheat(x, y, tileSize, timestamp, idx);
            }
          }

          // Draw wall
          if (isWall) {
            drawWall(x, y, tileSize);
          }

          // Draw cherry
          if (isCherry && !isWall) {
            drawCherry(x, y, tileSize, timestamp);
          }

          // Draw horse
          if (isHorse && !isWall) {
            drawHorse(x, y, tileSize, timestamp);
          }
        }
      }

      // Draw grid lines
      ctx.strokeStyle = COLORS.gridLine;
      ctx.lineWidth = 1;
      
      for (let i = 0; i <= cols; i++) {
        ctx.beginPath();
        ctx.moveTo(i * tileSize + 0.5, 0);
        ctx.lineTo(i * tileSize + 0.5, height);
        ctx.stroke();
      }
      for (let i = 0; i <= rows; i++) {
        ctx.beginPath();
        ctx.moveTo(0, i * tileSize + 0.5);
        ctx.lineTo(width, i * tileSize + 0.5);
        ctx.stroke();
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener('resize', resize);
    animationRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationRef.current);
    };
  }, [parsedMap, wallSet, solveResult, showSolution]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        display: 'block',
        imageRendering: 'pixelated',
      }}
    />
  );
}
