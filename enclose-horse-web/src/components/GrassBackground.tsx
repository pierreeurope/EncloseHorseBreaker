import { useEffect, useRef } from 'react';

// Grass background canvas matching enclose.horse style exactly
export function GrassBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      draw();
    };

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      
      // Main grass background - exact color from enclose.horse
      ctx.fillStyle = '#186b3b';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw subtle grass texture (darker blades)
      const grassColors = ['#1a7040', '#167035', '#148530', '#1c6538'];
      const bladeCount = Math.floor((canvas.width * canvas.height) / (300 * dpr));
      
      for (let i = 0; i < bladeCount; i++) {
        const x = Math.random() * canvas.width;
        const y = Math.random() * canvas.height;
        const color = grassColors[Math.floor(Math.random() * grassColors.length)];
        const size = (1.5 + Math.random() * 2.5) * dpr;
        
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.4 + Math.random() * 0.3;
        ctx.fillRect(x, y, size * 0.3, size);
      }
      ctx.globalAlpha = 1;
    };

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        imageRendering: 'pixelated',
        background: '#186b3b'
      }}
    />
  );
}
