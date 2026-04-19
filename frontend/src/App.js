import React, { useState } from 'react'
import StatsBar from './components/StatsBar'
import PriceCards from './components/PriceCards'
import TopMovers from './components/TopMovers'
import PriceChart from './components/PriceChart'
import NewsPanel from './components/NewsPanel'
import ChatRAG from './components/ChatRAG'
import './App.css'

function App() {
  // selectedSymbol est partagé entre PriceChart et NewsPanel
  // quand l'utilisateur clique sur BTC → chart BTC + news BTC
  const [selectedSymbol, setSelectedSymbol] = useState('BTC')

  return (
    <div className="app">
      <header className="app-header">
        <h1>₿ Crypto RAG Intelligence</h1>
        <p className="subtitle">Real-time AI-powered market analysis</p>
      </header>

      <main className="app-main">
        {/* Ligne 1 : compteurs système */}
        <StatsBar />

        {/* Ligne 2 : prix en temps réel — cliquable pour changer selectedSymbol */}
        <PriceCards
          selectedSymbol={selectedSymbol}
          onSymbolSelect={setSelectedSymbol}
        />

        {/* Ligne 3 : graphique + top movers */}
        <div className="row-two-cols">
          <PriceChart symbol={selectedSymbol} />
          <TopMovers onSymbolSelect={setSelectedSymbol} />
        </div>

        {/* Ligne 4 : RAG chat + news */}
        <div className="row-two-cols">
          <ChatRAG />
          <NewsPanel symbol={selectedSymbol} />
        </div>
      </main>
    </div>
  )
}

export default App