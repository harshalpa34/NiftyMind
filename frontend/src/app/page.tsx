'use client';

import { useEffect, useState } from 'react';
import styles from './page.module.css';

export default function Home() {
  const [apiStatus, setApiStatus] = useState<string>('Loading...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/v1/health`);
        
        if (response.ok) {
          const data = await response.json();
          setApiStatus(data.status);
        } else {
          setError('API returned an error');
        }
      } catch (err) {
        setError('Failed to connect to API. Make sure the backend is running on port 8000.');
      }
    };

    checkApiHealth();
  }, []);

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1>Welcome to NiftyMind</h1>
        <p>A modern GenAI application built with Next.js and FastAPI</p>
        
        <div className={styles.status}>
          <h2>Backend Status</h2>
          {error ? (
            <p style={{ color: 'red' }}>{error}</p>
          ) : (
            <p style={{ color: 'green' }}>Status: {apiStatus}</p>
          )}
        </div>

        <div className={styles.features}>
          <h2>Features</h2>
          <ul>
            <li>⚡ FastAPI backend with async/await</li>
            <li>🚀 Next.js 14 frontend</li>
            <li>🔌 Type-safe API integration</li>
            <li>📝 Built for GenAI applications</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
