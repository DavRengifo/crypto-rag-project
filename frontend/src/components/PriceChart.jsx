import React, { useState, useEffect } from 'react'
import {
    AreaChart, Area,
    XAxis, YAxis, Tooltip,
    ResponsiveContainer
} from 'recharts'
import { getPriceHistory } from '../services/api'

const PERIODS = ['24h', '7d', '30d', '1y', '5y']

const SYMBOL_NAMES = {
    BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana',   BNB: 'BNB',
    XRP: 'XRP',     DOGE: 'Dogecoin', ADA: 'Cardano', DOT: 'Polkadot',
}

function CustomTooltip({ active, payload, label, startPrice }) {
    if (!active || !payload?.length) return null
    const price = payload[0].value
    const delta = startPrice ? ((price - startPrice) / startPrice) * 100 : null
    return (
        <div className="chart-tooltip">
            <div className="chart-tooltip-time">{label}</div>
            <div className="chart-tooltip-price">
                ${price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </div>
            {delta !== null && (
                <div className={`chart-tooltip-delta ${delta >= 0 ? 'positive' : 'negative'}`}>
                    {delta >= 0 ? '+' : ''}{delta.toFixed(2)}% from open
                </div>
            )}
        </div>
    )
}

function PriceChart({ symbol }) {
    const [history, setHistory] = useState([])
    const [period, setPeriod]   = useState('24h')
    const [loading, setLoading] = useState(true)
    const [error, setError]     = useState(null)

    useEffect(() => {
        setLoading(true)
        setError(null)

        getPriceHistory(symbol, period)
            .then(data => {
                const formatted = data.map(point => ({
                    price: point.price_usd,
                    time : new Date(point.scraped_at).toLocaleDateString('en-US', {
                        month : 'short',
                        day   : 'numeric',
                        ...(period === '24h' ? { hour: '2-digit', minute: '2-digit' } : {})
                    })
                }))
                setHistory(formatted)
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false))
    }, [symbol, period])

    const delta      = history.length >= 2
        ? ((history[history.length - 1].price - history[0].price) / history[0].price) * 100
        : null
    const positive    = delta === null || delta >= 0
    const strokeColor = positive ? '#0ecb81' : '#f6465d'
    const gradientId  = positive ? 'gradGreen' : 'gradRed'
    const startPrice  = history.length > 0 ? history[0].price : null

    return (
        <div className="card">
            <div className="card-header">
                <div className="chart-title-group">
                    <span className="chart-symbol-title">{SYMBOL_NAMES[symbol] || symbol}</span>
                    <span className="chart-symbol-sub">{symbol}</span>
                    {delta !== null && (
                        <span className={`chart-delta ${positive ? 'positive' : 'negative'}`}>
                            {positive ? '+' : ''}{delta.toFixed(2)}%
                            <span style={{ color: '#848e9c', fontWeight: 400 }}> ({period})</span>
                        </span>
                    )}
                </div>
                <div className="period-buttons">
                    {PERIODS.map(p => (
                        <button
                            key={p}
                            className={`period-btn ${period === p ? 'active' : ''} ${p === '5y' ? 'disabled' : ''}`}
                            onClick={() => p !== '5y' && setPeriod(p)}
                            disabled={p === '5y'}
                            title={p === '5y' ? 'Coming soon — requires premium API' : undefined}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            {loading && <div className="chart-placeholder">Loading chart...</div>}
            {error   && (
                <div className="error" style={{ padding: '120px 0', textAlign: 'center' }}>
                    Error: {error}
                </div>
            )}

            {!loading && !error && history.length > 0 && (
                <ResponsiveContainer width="100%" height={380}>
                    <AreaChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                        <defs>
                            <linearGradient id="gradGreen" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%"  stopColor="#0ecb81" stopOpacity={0.22} />
                                <stop offset="95%" stopColor="#0ecb81" stopOpacity={0}    />
                            </linearGradient>
                            <linearGradient id="gradRed" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%"  stopColor="#f6465d" stopOpacity={0.22} />
                                <stop offset="95%" stopColor="#f6465d" stopOpacity={0}    />
                            </linearGradient>
                        </defs>

                        <XAxis
                            dataKey="time"
                            tick={{ fill: '#848e9c', fontSize: 10 }}
                            tickLine={false}
                            axisLine={false}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            tick={{ fill: '#848e9c', fontSize: 10 }}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={v =>
                                v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v.toLocaleString()}`
                            }
                            width={58}
                            domain={['auto', 'auto']}
                        />
                        <Tooltip content={<CustomTooltip startPrice={startPrice} />} />
                        <Area
                            type="monotone"
                            dataKey="price"
                            stroke={strokeColor}
                            strokeWidth={2}
                            fill={`url(#${gradientId})`}
                            dot={false}
                            activeDot={{ r: 4, fill: strokeColor, strokeWidth: 0 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            )}

            {!loading && !error && history.length === 0 && (
                <div className="chart-placeholder">No data for {symbol} ({period})</div>
            )}
        </div>
    )
}

export default PriceChart
