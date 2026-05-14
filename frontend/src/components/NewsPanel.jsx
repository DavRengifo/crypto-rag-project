import React, { useState, useEffect } from 'react'
import { getNews } from '../services/api'

const SYMBOLS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'DOT']

function NewsPanel({ selectedSymbol }) {
    const [activeTab, setActiveTab] = useState('market')

    // Market tab — general news, loaded once on mount
    const [marketArticles, setMarketArticles] = useState([])
    const [marketLoading, setMarketLoading]   = useState(true)
    const [marketError, setMarketError]       = useState(null)

    // Token tab — local selection, independent of selectedSymbol after first mount
    const [tokenSymbol, setTokenSymbol]     = useState(selectedSymbol || 'BTC')
    const [tokenArticles, setTokenArticles] = useState([])
    const [tokenFiltered, setTokenFiltered] = useState(false)
    const [tokenLoading, setTokenLoading]   = useState(false)
    const [tokenError, setTokenError]       = useState(null)

    useEffect(() => {
        getNews()
            .then(data => setMarketArticles(data.articles))
            .catch(err => setMarketError(err.message))
            .finally(() => setMarketLoading(false))
    }, [])

    useEffect(() => {
        setTokenLoading(true)
        setTokenError(null)
        getNews(tokenSymbol)
            .then(data => {
                setTokenArticles(data.articles)
                setTokenFiltered(data.filtered)
            })
            .catch(err => setTokenError(err.message))
            .finally(() => setTokenLoading(false))
    }, [tokenSymbol])

    const formatDate = dateStr => {
        if (!dateStr) return ''
        return new Date(dateStr).toLocaleDateString('en-US', {
            month : 'short',
            day   : 'numeric',
            hour  : '2-digit',
            minute: '2-digit'
        })
    }

    const renderList = (articles, loading, error) => {
        if (loading) return <div className="news-loading">Loading...</div>
        if (error)   return <div className="error">{error}</div>
        if (!articles.length) return <div className="news-empty">No articles found.</div>
        return (
            <div className="news-list">
                {articles.map((article, i) => (
                    <div key={i} className="news-item">
                        <div className="news-source">
                            {article.source} · {formatDate(article.published_at)}
                        </div>
                        <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="news-title"
                        >
                            {article.title}
                        </a>
                    </div>
                ))}
            </div>
        )
    }

    return (
        <div className="news-section">
            <div className="news-tabs">
                <button
                    className={`news-tab ${activeTab === 'market' ? 'active' : ''}`}
                    onClick={() => setActiveTab('market')}
                >
                    Market
                </button>
                <button
                    className={`news-tab ${activeTab === 'token' ? 'active' : ''}`}
                    onClick={() => setActiveTab('token')}
                >
                    Token
                </button>
            </div>

            {activeTab === 'market' && renderList(marketArticles, marketLoading, marketError)}

            {activeTab === 'token' && (
                <>
                    <div className="news-token-row">
                        <select
                            className="news-select"
                            value={tokenSymbol}
                            onChange={e => setTokenSymbol(e.target.value)}
                        >
                            {SYMBOLS.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                        {!tokenLoading && !tokenFiltered && (
                            <span className="news-general-badge">General Market</span>
                        )}
                    </div>
                    {renderList(tokenArticles, tokenLoading, tokenError)}
                </>
            )}
        </div>
    )
}

export default NewsPanel
