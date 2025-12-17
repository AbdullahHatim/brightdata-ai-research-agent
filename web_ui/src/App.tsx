
import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Search, Loader2, Citrus, ExternalLink, History, Trash2, X } from 'lucide-react'
import './index.css'

interface Source {
    title: string;
    url: string;
    snippet: string;
    source_type: string;
}

interface ResearchResponse {
    answer: string;
    sources: Source[];
}

interface HistoryItem {
    id: string;
    agent: string;
    question: string;
    timestamp: string;
}

function App() {
    const [query, setQuery] = useState('')
    const [mode, setMode] = useState<'basic' | 'discovery'>('basic')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<ResearchResponse | null>(null)
    const [error, setError] = useState<string | null>(null)

    const [showHistory, setShowHistory] = useState(false)
    const [history, setHistory] = useState<HistoryItem[]>([])

    const fetchHistory = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/history')
            if (res.ok) {
                const data = await res.json()
                setHistory(data.history)
            }
        } catch (e) {
            console.error("Failed to fetch history", e)
        }
    }

    useEffect(() => {
        if (showHistory) {
            fetchHistory()
        }
    }, [showHistory])

    const handleDelete = async (e: React.MouseEvent, item: HistoryItem) => {
        e.stopPropagation()
        if (!confirm('Are you sure you want to delete this chat?')) return
        try {
            await fetch(`http://localhost:8000/api/history/${item.agent}/${item.id}`, { method: 'DELETE' })
            setHistory(prev => prev.filter(h => h.id !== item.id))
        } catch (err) {
            console.error(err)
        }
    }

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!query.trim()) return

        setLoading(true)
        setResult(null)
        setError(null)
        setShowHistory(false)

        try {
            const res = await fetch('http://localhost:8000/api/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ params: query, mode: mode })
            })

            const data = await res.json()

            if (!res.ok) {
                // Show detailed error from backend
                throw new Error(data.detail || `Error: ${res.statusText}`)
            }

            setResult(data)
        } catch (err: any) {
            setError(err.message || 'Something went wrong')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="lemon-container">
            <header className="title-header">
                <Citrus size={48} color="#E6D200" />
                <span>Lemon Agent</span>
            </header>

            <div style={{ position: 'absolute', top: '2rem', right: '2rem' }}>
                <button
                    onClick={() => setShowHistory(!showHistory)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#666' }}
                >
                    <History size={28} />
                    <span style={{ fontSize: '0.8rem' }}>History</span>
                </button>
            </div>

            {showHistory && (
                <div className="history-drawer">
                    <div className="history-header">
                        <h3>Past Research</h3>
                        <button onClick={() => setShowHistory(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X /></button>
                    </div>
                    <div className="history-list">
                        {history.length === 0 && <p style={{ padding: '1rem', color: '#888' }}>No history yet.</p>}
                        {history.map(item => (
                            <div key={item.id} className="history-item">
                                <div className="history-content">
                                    <div className="history-q">{item.question}</div>
                                    <div className="history-meta">{item.agent} • {new Date(item.timestamp).toLocaleDateString()}</div>
                                </div>
                                <button className="delete-btn" onClick={(e) => handleDelete(e, item)}>
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <form className="search-box" onSubmit={handleSearch}>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Ask anything..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    disabled={loading}
                />
                <button type="submit" className="search-btn" disabled={loading}>
                    {loading ? <Loader2 className="animate-spin" size={24} color="#FFF" /> : <Search size={24} color="#FFF" />}
                </button>
            </form>

            <div className="toggle-group">
                <div
                    className={`toggle-opt ${mode === 'basic' ? 'active' : ''}`}
                    onClick={() => setMode('basic')}
                >
                    Basic (Fast)
                </div>
                <div
                    className={`toggle-opt ${mode === 'discovery' ? 'active' : ''}`}
                    onClick={() => setMode('discovery')}
                >
                    Deep Discovery
                </div>
            </div>

            {loading && (
                <div className="loading-overlay">
                    <Citrus size={64} className="loading-lemon" color="#E6D200" />
                    <div className="thinking-text">Squeezing out fresh insights... 🍋</div>
                </div>
            )}

            {error && (
                <div style={{ color: '#D8000C', marginTop: '2rem', padding: '1rem', background: '#FFD2D2', borderRadius: '10px', width: '100%', maxWidth: '700px', border: '1px solid #D8000C' }}>
                    <strong>Error:</strong> {error}
                </div>
            )}

            {result && (
                <div className="results-area">
                    <div className="answer-card">
                        <ReactMarkdown>{result.answer}</ReactMarkdown>
                    </div>

                    <h3 style={{ marginTop: '2rem', color: '#6B7280' }}>Sources</h3>
                    <div className="sources-grid">
                        {result.sources.map((s, i) => (
                            <div key={i} className="source-card">
                                <div className="source-title" title={s.title}>{s.title}</div>
                                <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-link">
                                    <ExternalLink size={12} style={{ display: 'inline', marginRight: '4px' }} />
                                    {(() => {
                                        try { return new URL(s.url).hostname.replace('www.', '') } catch { return 'Link' }
                                    })()}
                                </a>
                                <div style={{ marginTop: '0.5rem', color: '#888', fontSize: '0.8rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                    {s.snippet}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
