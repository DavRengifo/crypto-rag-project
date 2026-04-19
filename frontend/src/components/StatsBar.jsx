import React, { useEffect, useState } from 'react'
import { getStats } from '../services/api'

function StatsBar() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const data = await getStats()
                setStats(data)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
        fetchStats()
    }, [])

    if (loading) return <div className="stats-bar">Loading stats...</div>
    if (error) return <div className="stats-bar error">Error: {error}</div>

    return (
        <div className="stats-bar">
            <div className="stat-item">
                <span className="stat-value">{stats.total_tokens}</span>
                <span className="stat-label">Tokens</span>
            </div>
            <div className="stat-item">
                <span className="stat-value">{stats.total_price_snapshots}</span>
                <span className="stat-label">Price Points</span>
            </div>
            <div className="stat-item">
                <span className="stat-value">{stats.total_news_articles}</span>
                <span className="stat-label">News Articles</span>
            </div>
            <div className="stat-item">
                <span className="stat-value">{stats.total_embeddings}</span>
                <span className="stat-label">Embeddings</span>
            </div>
        </div>
    )
} 

export default StatsBar
