import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getPriceHistory } from '../services/api'

const PERIODS = ['24h', '7d', '30d', '1y', '5y']

function PriceChart({ symbol }) {
    const [history, setHistory] = useState([])
    const [period, setPeriod] = useState('24h')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        setLoading(true)
        setError(null)

        const fetchHistory = async () => {
            try {
                const data = await getPriceHistory(symbol, period)
                // recharts attend des objets avec des clés nommées
                // on transforme les données pour recharts
                const formatted = data.map(point => ({
                    price: point.price_usd,
                    time : new Date(point.scraped_at).toLocaleDateString()
                }))
                setHistory(formatted)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }

        fetchHistory()
    }, [symbol, period])  // ← re-fetch si symbol OU period change

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">{symbol} Price</span>
                {/* Boutons de période */}
                <div className="period-buttons">
                    {PERIODS.map(p => (
                        <button
                            key={p}
                            className={`period-btn ${period === p ? 'active' : ''}`}
                            onClick={() => setPeriod(p)}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            {loading && <div className="chart-placeholder">Loading chart...</div>}
            {error && <div className="error">Error: {error}</div>}

            {!loading && !error && (
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={history}>
                        <XAxis
                            dataKey="time"
                            tick={{ fill: '#888', fontSize: 11 }}
                            tickLine={false}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            tick={{ fill: '#888', fontSize: 11 }}
                            tickLine={false}
                            tickFormatter={v => `$${v.toLocaleString()}`}
                            width={80}
                        />
                        <Tooltip
                            formatter={(value) => [`$${value.toLocaleString()}`, 'Price']}
                            contentStyle={{
                                background: '#1a1a2e',
                                border: '1px solid #2a2a3e',
                                borderRadius: '8px',
                                color: '#e0e0e0'
                            }}
                        />
                        <Line
                            type="monotone"
                            dataKey="price"
                            stroke="#f7931a"
                            strokeWidth={2}
                            dot={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            )}
        </div>
    )
}

export default PriceChart