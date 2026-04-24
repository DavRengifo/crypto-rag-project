import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { getMarketReport, generateReport } from '../services/api'

const SYMBOLS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'DOT']

function ReportsPanel() {
    // Daily report
    const [dailyReport, setDailyReport] = useState(null)
    const [dailyLoading, setDailyLoading] = useState(true)
    const [dailyError, setDailyError]   = useState(null)

    // Custom report
    const [selected, setSelected]     = useState(['BTC', 'ETH'])
    const [customReport, setCustomReport] = useState(null)
    const [generating, setGenerating] = useState(false)
    const [genError, setGenError]     = useState(null)

    const loadDaily = () => {
        setDailyLoading(true)
        setDailyError(null)
        getMarketReport()
            .then(setDailyReport)
            .catch(() => setDailyError('not_found'))
            .finally(() => setDailyLoading(false))
    }

    useEffect(() => { loadDaily() }, [])

    const toggleSymbol = sym =>
        setSelected(prev =>
            prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym]
        )

    const handleGenerate = async () => {
        if (!selected.length) return
        setGenerating(true)
        setGenError(null)
        setCustomReport(null)
        try {
            const data = await generateReport(selected)
            setCustomReport(data)
        } catch (err) {
            setGenError(err.message)
        } finally {
            setGenerating(false)
        }
    }

    const fmtDate = str => {
        if (!str) return ''
        return new Date(str).toLocaleString('en-US', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        })
    }

    return (
        <div className="reports-panel">

            {/* ── Daily market report ── */}
            <div className="report-card">
                <div className="report-card-header">
                    <span className="report-card-title">Daily Market Report</span>
                    <button className="report-refresh-btn" onClick={loadDaily} disabled={dailyLoading}>
                        ↻ Refresh
                    </button>
                </div>

                {dailyLoading && <div className="report-loading">Loading report...</div>}

                {!dailyLoading && dailyError && (
                    <div className="report-empty">
                        Daily market report not yet generated. Check back after 08:00 UTC.
                    </div>
                )}

                {!dailyLoading && dailyReport && (
                    <>
                        <div className="report-meta">Generated {fmtDate(dailyReport.generated_at)}</div>
                        <div className="report-content">
                            <ReactMarkdown>{dailyReport.content}</ReactMarkdown>
                        </div>
                    </>
                )}
            </div>

            {/* ── Custom report generator ── */}
            <div className="report-card">
                <div className="report-card-header">
                    <span className="report-card-title">Generate Custom Report</span>
                </div>

                <div className="report-sym-grid">
                    {SYMBOLS.map(sym => (
                        <label
                            key={sym}
                            className={`report-sym-check ${selected.includes(sym) ? 'active' : ''}`}
                        >
                            <input
                                type="checkbox"
                                checked={selected.includes(sym)}
                                onChange={() => toggleSymbol(sym)}
                            />
                            {sym}
                        </label>
                    ))}
                </div>

                <button
                    className="report-generate-btn"
                    onClick={handleGenerate}
                    disabled={generating || !selected.length}
                >
                    {generating ? 'Generating…' : 'Generate Report'}
                </button>

                {generating && (
                    <div className="report-loading">
                        <span className="report-spinner" />
                        Generating report… this may take up to 30 seconds
                    </div>
                )}

                {genError && (
                    <div className="error" style={{ marginTop: 12 }}>{genError}</div>
                )}

                {customReport && (
                    <div style={{ marginTop: 16 }}>
                        <div className="report-meta">
                            {customReport.symbols.join(', ')} · {customReport.period}
                        </div>
                        <div className="report-content">
                            <ReactMarkdown>{customReport.content}</ReactMarkdown>
                        </div>
                    </div>
                )}
            </div>

        </div>
    )
}

export default ReportsPanel
