import React, { useState, useEffect } from 'react'
import { getPrices } from '../services/api'

function PriceCard({ token, isSelected, onSelect }) {
    // token contient : symbol, name, price_usd, change_24h
    // isSelected : booléen — cette card est-elle sélectionnée ?
    // onSelect : fonction à appeler quand on clique

    const isPositive = token.change_24h >= 0

    return (
        <div
            className={`price-card ${isSelected ? 'selected' : ''}`}
            onClick={() => onSelect(token.symbol)}
        >
            <div className="price-card-symbol">{token.symbol}</div>
            <div className="price-card-name">{token.name}</div>
            <div className="price-card-price">
                ${token.price_usd.toLocaleString()}
            </div>
            <div className={`price-card-change ${isPositive ? 'positive' : 'negative'}`}>
                {isPositive ? '▲' : '▼'} {Math.abs(token.change_24h).toFixed(2)}%
            </div>
        </div>        
    )
}

function PriceCards({ selectedSymbol, onSymbolSelect }) {
    const [prices, setPrices] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        const fetchPrices = async () => {
            try {
                const data = await getPrices()
                setPrices(data)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
        fetchPrices()
    }, [])

    useEffect(() => {
        const interval = setInterval(() => {
            getPrices()
                .then(data => setPrices(data))
                .catch(err => console.error(err))
        }, 30000)

        return () => clearInterval(interval) // cleanup
    }, [])

    if (loading) return <div className="card">Loading prices...</div>
    if (error) return <div className="card error">Error: {error}</div>

    return (
        <div className="price-cards-grid">
            {prices.map(token => (
                <PriceCard
                    key={token.symbol}
                    token={token}
                    isSelected={selectedSymbol === token.symbol}
                    onSelect={onSymbolSelect}
                />
            ))}
        </div>
    )  
}

export default PriceCards