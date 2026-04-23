import React, { useState, useRef, useEffect } from 'react'
import { askQuestion } from '../services/api'

function ChatRAG() {
    const [messages, setMessages] = useState([
        {
            role:    'assistant',
            content: 'Ask me anything about crypto markets. I answer based on the latest news in our database.'
        }
    ])
    const [input,   setInput]   = useState('')
    const [loading, setLoading] = useState(false)
    const bottomRef = useRef(null)

    // Auto-scroll to latest message
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const handleSend = async () => {
        const question = input.trim()
        if (!question || loading) return

        // Add user message immediately
        setMessages(prev => [...prev, { role: 'user', content: question }])
        setInput('')
        setLoading(true)

        try {
            const data = await askQuestion(question)

            // Add assistant answer
            setMessages(prev => [...prev, {
                role:    'assistant',
                content: data.answer,
                sources: data.sources
            }])
        } catch (err) {
            setMessages(prev => [...prev, {
                role:    'assistant',
                content: `Error: ${err.message}`
            }])
        } finally {
            setLoading(false)
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    return (
        <div className="card chat-rag">
            <div className="card-title">AI Market Analyst</div>

            <div className="chat-messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`chat-message ${msg.role}`}>
                        <div className="chat-bubble">
                            {msg.content}
                        </div>

                        {/* Sources under assistant messages */}
                        {msg.sources && msg.sources.length > 0 && (
                            <div className="chat-sources">
                                <span className="sources-label">Sources:</span>
                                {msg.sources.map((s, j) => (
                                    <span key={j} className="source-tag">
                                        {s.source} · {s.title.slice(0, 40)}…
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="chat-message assistant">
                        <div className="chat-bubble loading">
                            <span className="dot">.</span>
                            <span className="dot">.</span>
                            <span className="dot">.</span>
                        </div>
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
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                />
                <button
                    className="chat-send"
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    )
}

export default ChatRAG