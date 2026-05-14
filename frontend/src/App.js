import React, { useState, useEffect } from 'react'
import StatsBar from './components/StatsBar'
import PriceCards from './components/PriceCards'
import TopMovers from './components/TopMovers'
import PriceChart from './components/PriceChart'
import NewsPanel from './components/NewsPanel'
import ChatRAG from './components/ChatRAG'
import ReportsPanel from './components/ReportsPanel'
import { getPrices } from './services/api'
import './App.css'

function App() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC')
  const [headerPrices, setHeaderPrices] = useState({})

  useEffect(() => {
    const load = () =>
      getPrices()
        .then(data => {
          const map = {}
          data.forEach(p => { map[p.symbol] = p })
          setHeaderPrices(map)
        })
        .catch(console.error)
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [])

  const fmt = p =>
    p ? `$${p.price_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—'
  const chg = p =>
    p ? `${p.change_24h >= 0 ? '+' : ''}${p.change_24h?.toFixed(2)}%` : ''

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-logo">
          <span className="logo-icon">₿</span>
          <span className="logo-text">CryptoRAG</span>
        </div>

        <div className="header-tickers">
          {['BTC', 'ETH'].map(sym => {
            const p = headerPrices[sym]
            return (
              <div key={sym} className="header-ticker">
                <span className="ticker-symbol">{sym}</span>
                <span className="ticker-price">{fmt(p)}</span>
                <span className={`ticker-change ${p?.change_24h >= 0 ? 'positive' : 'negative'}`}>
                  {chg(p)}
                </span>
              </div>
            )
          })}
        </div>

        <StatsBar />
      </header>

      {/* ── 3-column body ── */}
      <div className="app-body">

        <aside className="sidebar">
          <PriceCards
            selectedSymbol={selectedSymbol}
            onSymbolSelect={setSelectedSymbol}
          />
        </aside>

        <main className="main-content">
          <PriceChart symbol={selectedSymbol} />
          <ChatRAG />
        </main>

        <aside className="right-panel">
          <TopMovers onSymbolSelect={setSelectedSymbol} />
          <NewsPanel selectedSymbol={selectedSymbol} />
        </aside>

      </div>

      {/* ── AI Reports — full width below ── */}
      <section className="reports-section">
        <div className="section-label">AI Market Reports</div>
        <ReportsPanel />
      </section>

    </div>
  )
}

export default App
