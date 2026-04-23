import React, { useState, useEffect } from 'react'
import { getNews } from '../services/api'

function NewsPanel({ symbol }) {
    const [articles, setArticles] = useState([])
    const [loading, setLoading]   = useState(true)
    const [error, setError]       = useState(null)

    useEffect(() => {
        const fetchNews = async () => {
            setLoading(true)
            setError(null)
            try {
                const data = await getNews(symbol)
                setArticles(data)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
        fetchNews()
    }, [symbol]) // re-fetch when symbol changes

    const formatDate = (dateStr) => {
        if (!dateStr) return ''
        const d = new Date(dateStr)
        return d.toLocaleDateString('en-US', {
            month: 'short',
            day:   'numeric',
            hour:  '2-digit',
            minute:'2-digit'
        })
    }

    if (loading) return <div className="card">Loading news...</div>
    if (error)   return <div className="card error">Error: {error}</div>

    return (
        <div className="card news-panel">
            <div className="card-title">
                Latest News {symbol ? `— ${symbol}` : ''}
            </div>

            {articles.length === 0 ? (
                <div className="news-empty">No news available for {symbol}</div>
            ) : (
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
            )}
        </div>
    )
}

export default NewsPanel