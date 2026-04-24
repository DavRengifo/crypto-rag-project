import React, { useState, useRef, useEffect } from 'react'
import { askQuestion } from '../services/api'

const SUGGESTIONS = [
    'What is happening with Bitcoin today?',
    'Which crypto has the best momentum this week?',
    'What are the main risks in the current market?',
]

const fmtTime = date =>
    date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })

function ChatRAG() {
    const [messages, setMessages] = useState([{
        role   : 'assistant',
        content: 'Ask me anything about crypto markets. I answer based on the latest news in our database.',
        ts     : new Date(),
    }])
    const [input,   setInput]   = useState('')
    const [loading, setLoading] = useState(false)
    const bottomRef = useRef(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const send = async (question) => {
        const q = (question ?? input).trim()
        if (!q || loading) return

        setMessages(prev => [...prev, { role: 'user', content: q, ts: new Date() }])
        setInput('')
        setLoading(true)

        try {
            const data = await askQuestion(q)
            setMessages(prev => [...prev, {
                role   : 'assistant',
                content: data.answer,
                sources: data.sources,
                ts     : new Date(),
            }])
        } catch (err) {
            setMessages(prev => [...prev, {
                role   : 'assistant',
                content: `Error: ${err.message}`,
                ts     : new Date(),
            }])
        } finally {
            setLoading(false)
        }
    }

    const onKey = e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
    }

    const showSuggestions = messages.length <= 1 && !loading

    return (
        <div className="card chat-rag">
            <div className="card-title">AI Market Analyst</div>

            <div className="chat-messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`chat-msg-row ${msg.role}`}>
                        <div className="chat-bubble">{msg.content}</div>

                        {msg.sources?.length > 0 && (
                            <div className="chat-sources">
                                {msg.sources.map((s, j) => (
                                    <a
                                        key={j}
                                        href={s.url || '#'}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="source-chip"
                                    >
                                        {s.source}
                                    </a>
                                ))}
                            </div>
                        )}

                        <div className="chat-ts">{fmtTime(msg.ts)}</div>
                    </div>
                ))}

                {loading && (
                    <div className="chat-msg-row assistant">
                        <div className="chat-bubble loading">
                            <span className="dot" /><span className="dot" /><span className="dot" />
                        </div>
                    </div>
                )}

                {showSuggestions && (
                    <div className="chat-suggestions">
                        {SUGGESTIONS.map((s, i) => (
                            <button key={i} className="suggestion-btn" onClick={() => send(s)}>
                                {s}
                            </button>
                        ))}
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            <div className="chat-input-row">
                <input
                    type="text"
                    className="chat-input"
                    placeholder="What is happening with Bitcoin?"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={onKey}
                    disabled={loading}
                />
                <button
                    className="chat-send"
                    onClick={() => send()}
                    disabled={loading || !input.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    )
}

export default ChatRAG
