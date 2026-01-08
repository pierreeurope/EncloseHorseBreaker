import { useState, useEffect, useMemo } from 'react';
import { GrassBackground } from './components/GrassBackground';
import { GameCanvas } from './components/GameCanvas';
import { fetchPuzzle, fetchStats, parseMap, solve } from './solver';
import type { PuzzleData, StatsData } from './solver';
import './App.css';

function getTodayDate(): string {
  const now = new Date();
  return now.toISOString().split('T')[0];
}

function getDateFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get('date');
}

function App() {
  const [date, setDate] = useState<string>(getDateFromUrl() || getTodayDate());
  const [puzzle, setPuzzle] = useState<PuzzleData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load puzzle and stats
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const puzzleData = await fetchPuzzle(date);
        setPuzzle(puzzleData);
        
        const statsData = await fetchStats(puzzleData.id);
        setStats(statsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load puzzle');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [date]);

  // Parse the map
  const parsedMap = useMemo(() => {
    if (!puzzle) return null;
    return parseMap(puzzle.map);
  }, [puzzle]);

  // Calculate score
  const score = useMemo(() => {
    if (!parsedMap || !stats) return 0;
    const wallSet = new Set(stats.optimalWalls);
    const result = solve(
      parsedMap.cols,
      parsedMap.rows,
      parsedMap.terrain,
      wallSet,
      parsedMap.cherries,
      parsedMap.playerIdx
    );
    return result.score;
  }, [parsedMap, stats]);

  // Navigate to different dates
  const goToDate = (newDate: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set('date', newDate);
    window.history.pushState({}, '', url);
    setDate(newDate);
  };

  const goToPreviousDay = () => {
    const d = new Date(date);
    d.setDate(d.getDate() - 1);
    goToDate(d.toISOString().split('T')[0]);
  };

  const goToNextDay = () => {
    const d = new Date(date);
    d.setDate(d.getDate() + 1);
    const today = getTodayDate();
    if (d.toISOString().split('T')[0] <= today) {
      goToDate(d.toISOString().split('T')[0]);
    }
  };

  const isToday = date === getTodayDate();

  return (
    <div className="app">
      <GrassBackground />
      
      <div className="content">
        {/* Navbar */}
        <nav className="navbar">
          <div className="navbar-row">
            <button className="navbar-btn" onClick={() => window.location.href = '/'}>
              ←
            </button>
            <h1 className="navbar-title">
              enclose.horse
              <span className="solved-badge">SOLVED</span>
            </h1>
            <button className="navbar-btn" disabled>
              ☰
            </button>
          </div>
          {puzzle && (
            <div className="navbar-row navbar-row-subtitle">
              <span className="navbar-subtitle">Day {puzzle.dayNumber}</span>
            </div>
          )}
        </nav>

        {/* Main content */}
        <main className="grid-area">
          {loading && (
            <div className="loading">
              <span className="loading-horse">🐴</span>
              <p>Loading puzzle...</p>
            </div>
          )}
          
          {error && (
            <div className="error">
              <p>⚠️ {error}</p>
              <button className="btn" onClick={() => setDate(getTodayDate())}>
                Go to Today
              </button>
            </div>
          )}

          {!loading && !error && parsedMap && stats && (
            <GameCanvas
              parsedMap={parsedMap}
              walls={stats.optimalWalls}
              showSolution={true}
            />
          )}
        </main>

        {/* Stats */}
        {!loading && !error && puzzle && stats && (
          <footer className="bottom-container">
            <div className="stats-row">
              <div className="stat">
                <span className="stat-label">Walls:</span>
                <span className="stat-value">{stats.optimalWalls.length}/{puzzle.budget}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Score:</span>
                <span className="stat-value gold">{score}</span>
              </div>
            </div>
            
            <div className="optimal-badge">
              ✓ Optimal Solution ({stats.optimalScore} pts)
            </div>
            
            <div className="puzzle-info">
              <p className="puzzle-name">"{puzzle.name}" by {puzzle.creatorName}</p>
            </div>

            <div className="date-nav">
              <button className="btn btn-nav" onClick={goToPreviousDay}>
                ← Previous
              </button>
              <span className="date-display">{date}</span>
              <button 
                className="btn btn-nav" 
                onClick={goToNextDay}
                disabled={isToday}
              >
                Next →
              </button>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}

export default App;
