import React, { useEffect, useState } from 'react'
import { getStats } from '../services/api'

function useCountUp(target, duration = 900) {
    const [value, setValue] = useState(0)
    useEffect(() => {
        if (!target) return
        let frame = 0
        const total = Math.ceil(duration / 16)
        const timer = setInterval(() => {
            frame++
            setValue(Math.round((frame / total) * target))
            if (frame >= total) clearInterval(timer)
        }, 16)
        return () => clearInterval(timer)
    }, [target, duration])
    return value
}

const IconCoins = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l3 3"/>
    </svg>
)
const IconChart = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
)
const IconNews = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
        <path d="M18 14h-8M15 18h-5M10 6h8v4h-8V6Z"/>
    </svg>
)
const IconEmbed = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
    </svg>
)
const IconClock = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
        <path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
    </svg>
)

function StatsBar() {
    const [stats, setStats] = useState(null)
    const [lastUpdate, setLastUpdate] = useState(null)

    const cTokens     = useCountUp(stats?.total_tokens)
    const cPrices     = useCountUp(stats?.total_price_snapshots)
    const cNews       = useCountUp(stats?.total_news_articles)
    const cEmbeddings = useCountUp(stats?.total_embeddings)

    useEffect(() => {
        getStats()
            .then(data => {
                setStats(data)
                if (data.last_update) {
                    const d = new Date(data.last_update)
                    setLastUpdate(
                        d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
                    )
                }
            })
            .catch(console.error)
    }, [])

    return (
        <div className="stats-bar">
            <div className="stat-item">
                <span className="stat-icon"><IconCoins /></span>
                <span className="stat-value">{stats ? cTokens : '—'}</span>
                <span className="stat-label">Tokens</span>
            </div>
            <div className="stat-item">
                <span className="stat-icon"><IconChart /></span>
                <span className="stat-value">{stats ? cPrices.toLocaleString() : '—'}</span>
                <span className="stat-label">Price Points</span>
            </div>
            <div className="stat-item">
                <span className="stat-icon"><IconNews /></span>
                <span className="stat-value">{stats ? cNews.toLocaleString() : '—'}</span>
                <span className="stat-label">News</span>
            </div>
            <div className="stat-item">
                <span className="stat-icon"><IconEmbed /></span>
                <span className="stat-value">{stats ? cEmbeddings.toLocaleString() : '—'}</span>
                <span className="stat-label">Embeddings</span>
            </div>
            <div className="stat-item">
                <span className="stat-icon"><IconClock /></span>
                <span className="stat-value stat-time">{lastUpdate || '—'}</span>
                <span className="stat-label">Last Update</span>
            </div>
        </div>
    )
}

export default StatsBar
