import React, { useState } from 'react'
import StatsBar from './components/StatsBar'
import PriceCards from './components/PriceCards'
import TopMovers from './components/TopMovers'
import PriceChart from './components/PriceChart'
import NewsPanel from './components/NewsPanel'
import ChatRAG from './components/ChatRAG'
import './App.css'

function App() {
  // selectedSymbol is shared between PriceChart and NewsPanel
  // when user click on BTC → chart BTC + news BTC
  const [selectedSymbol, setSelectedSymbol] = useState('BTC')

  return (
    <div className="app">
      <header className="app-header">
        <h1>₿ Crypto RAG Intelligence</h1>
        <p className="subtitle">Real-time AI-powered market analysis</p>
      </header>

      <main className="app-main">
        {/* Row 1: system counters */}
        <StatsBar />

        {/* Row 2: real-time prices — clickable to change selectedSymbol */}
        <PriceCards
          selectedSymbol={selectedSymbol}
          onSymbolSelect={setSelectedSymbol}
        />

        {/* Row 3: chart + top movers */}
        <div className="row-two-cols">
          <PriceChart symbol={selectedSymbol} />
          <TopMovers onSymbolSelect={setSelectedSymbol} />
        </div>

        {/* Row 4: RAG chat + news */}
        <div className="row-two-cols">
          <ChatRAG />
          <NewsPanel symbol={selectedSymbol} />
        </div>
      </main>
    </div>
  )
}

export default App