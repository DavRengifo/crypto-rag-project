import React, { useState, useEffect } from 'react'
import { getTopMovers } from '../services/api'

function TopMovers({ onSymbolSelect }) {
    const [movers, setMovers] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError]     = useState(null)

    const fetchMovers = async () => {
        try {
            const data = await getTopMovers()
            setMovers(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchMovers()
        const iv = setInterval(fetchMovers, 60000)
        return () => clearInterval(iv)
    }, [])

    if (loading) return (
        <div className="right-section">
            <div className="right-section-title">Top Movers 24h</div>
            <div style={{ color: '#848e9c', fontSize: '0.78rem' }}>Loading...</div>
        </div>
    )
    if (error) return (
        <div className="right-section">
            <div className="right-section-title">Top Movers 24h</div>
            <div className="error">{error}</div>
        </div>
    )

    const gainers  = movers.filter(t => t.change_24h >= 0)
    const losers   = movers.filter(t => t.change_24h < 0).reverse()
    const maxGain  = gainers.length ? Math.max(...gainers.map(t => t.change_24h)) : 1
    const maxLoss  = losers.length  ? Math.abs(Math.min(...losers.map(t => t.change_24h))) : 1

    const renderRow = (token, maxVal, positive) => {
        const pct      = Math.abs(token.change_24h)
        const barWidth = Math.round((pct / maxVal) * 100)

        return (
            <div
                key={token.symbol}
                className="mover-row"
                onClick={() => onSymbolSelect(token.symbol)}
            >
                <span className="mover-symbol">{token.symbol}</span>
                <div className="mover-bar-wrap">
                    <div
                        className={`mover-bar ${positive ? 'positive' : 'negative'}`}
                        style={{ width: `${barWidth}%` }}
                    />
                </div>
                <span className={`mover-change ${positive ? 'positive' : 'negative'}`}>
                    {positive ? '+' : ''}{token.change_24h.toFixed(2)}%
                </span>
            </div>
        )
    }

    return (
        <div className="right-section">
            <div className="right-section-title">Top Movers 24h</div>

            {gainers.length > 0 && (
                <div className="movers-section">
                    <div className="movers-label positive">▲ Gainers</div>
                    {gainers.map(t => renderRow(t, maxGain, true))}
                </div>
            )}

            {gainers.length > 0 && losers.length > 0 && (
                <div className="movers-divider" />
            )}

            {losers.length > 0 && (
                <div className="movers-section">
                    <div className="movers-label negative">▼ Losers</div>
                    {losers.map(t => renderRow(t, maxLoss, false))}
                </div>
            )}
        </div>
    )
}

export default TopMovers
