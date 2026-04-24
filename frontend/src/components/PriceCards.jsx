import React, { useState, useEffect } from 'react'
import { getPrices } from '../services/api'

const DOT_COLORS = {
    BTC: '#f7931a', ETH: '#627eea', SOL: '#9945ff',
    BNB: '#f0b90b', XRP: '#00aae4', DOGE: '#c2a633',
    ADA: '#3cc8c8', DOT: '#e6007a',
}

function PriceCards({ selectedSymbol, onSymbolSelect }) {
    const [prices, setPrices] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError]     = useState(null)

    useEffect(() => {
        const load = async () => {
            try {
                const data = await getPrices()
                setPrices(data)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
        load()
        const iv = setInterval(() => getPrices().then(setPrices).catch(console.error), 30000)
        return () => clearInterval(iv)
    }, [])

    if (loading) return (
        <div style={{ padding: '16px', color: '#848e9c', fontSize: '0.78rem' }}>
            Loading markets...
        </div>
    )
    if (error) return (
        <div style={{ padding: '16px' }} className="error">{error}</div>
    )

    return (
        <>
            <div className="sidebar-header">Markets</div>
            {prices.map(token => {
                const positive = token.change_24h >= 0
                const dotColor = DOT_COLORS[token.symbol] || '#848e9c'
                return (
                    <div
                        key={token.symbol}
                        className={`sidebar-row ${selectedSymbol === token.symbol ? 'active' : ''}`}
                        onClick={() => onSymbolSelect(token.symbol)}
                    >
                        <span className="sidebar-dot" style={{ background: dotColor }} />
                        <div className="sidebar-info">
                            <span className="sidebar-sym">{token.symbol}</span>
                            <span className="sidebar-name">{token.name}</span>
                        </div>
                        <div className="sidebar-right">
                            <span className="sidebar-price">
                                ${token.price_usd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                            </span>
                            <span className={`sidebar-change ${positive ? 'positive' : 'negative'}`}>
                                {positive ? '+' : ''}{token.change_24h?.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                )
            })}
        </>
    )
}

export default PriceCards
