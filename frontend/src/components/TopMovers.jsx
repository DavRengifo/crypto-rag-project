import React, { useState, useEffect } from 'react'
import { getTopMovers } from '../services/api'

function TopMovers({ onSymbolSelect }) {
    const [movers, setMovers] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

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
        // Refresh every 60 seconds — matches Redis cache TTL
        const interval = setInterval(fetchMovers, 60000)
        return () => clearInterval(interval)
    }, [])

    if (loading) return <div className="card">Loading movers...</div>
    if (error)   return <div className="card error">Error: {error}</div>

    const gainers = movers.filter(t => t.change_24h >= 0)
    const losers  = movers.filter(t => t.change_24h < 0).reverse()

    return (
        <div className="card">
            <div className="card-title">Top Movers 24h</div>

            <div className="movers-section">
                <div className="movers-label positive">▲ Gainers</div>
                {gainers.map(token => (
                    <div
                        key={token.symbol}
                        className="mover-row"
                        onClick={() => onSymbolSelect(token.symbol)}
                    >
                        <span className="mover-symbol">{token.symbol}</span>
                        <span className="mover-price">
                            ${token.price_usd.toLocaleString()}
                        </span>
                        <span className="mover-change positive">
                            +{token.change_24h.toFixed(2)}%
                        </span>
                    </div>
                ))}
            </div>

            {losers.length > 0 && (
                <div className="movers-section">
                    <div className="movers-label negative">▼ Losers</div>
                    {losers.map(token => (
                        <div
                            key={token.symbol}
                            className="mover-row"
                            onClick={() => onSymbolSelect(token.symbol)}
                        >
                            <span className="mover-symbol">{token.symbol}</span>
                            <span className="mover-price">
                                ${token.price_usd.toLocaleString()}
                            </span>
                            <span className="mover-change negative">
                                {token.change_24h.toFixed(2)}%
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

export default TopMovers