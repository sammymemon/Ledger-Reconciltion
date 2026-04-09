import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { History, Calendar, FileText, Trash2, ChevronRight } from 'lucide-react'

export default function HistorySidebar({ onSelectSession, currentSessionId }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/history')
      setHistory(res.data)
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [currentSessionId])

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear all history? This cannot be undone.')) return
    try {
      await axios.delete('/api/history')
      setHistory([])
    } catch (err) {
      console.error('Failed to clear history:', err)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-IN', { 
      day: 'numeric', 
      month: 'short', 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <div className="history-sidebar glass-panel">
      <div className="sidebar-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <History size={18} color="var(--accent-primary-light)" />
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Past Sessions</h3>
        </div>
        <button className="btn-icon" onClick={handleClearHistory} title="Clear All History">
          <Trash2 size={16} color="var(--danger)" />
        </button>
      </div>

      <div className="sidebar-content">
        {loading && <div style={{ textAlign: 'center', padding: 20, opacity: 0.6 }}>Loading...</div>}
        
        {!loading && history.length === 0 && (
          <div style={{ textAlign: 'center', padding: 30, opacity: 0.5, fontSize: '0.85rem' }}>
            No history yet
          </div>
        )}

        {history.map((session) => {
          const summary = session.summary ? JSON.parse(session.summary) : null
          const isActive = session.session_id === currentSessionId

          return (
            <div 
              key={session.session_id} 
              className={`history-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectSession(session.session_id)}
            >
              <div className="history-item-main">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <Calendar size={12} color="var(--text-muted)" />
                  <span className="history-date">{formatDate(session.created_at)}</span>
                </div>
                <div className="history-party">
                  {session.vendor_party || "New Reconciliation"}
                </div>
                {summary && (
                  <div className="history-stats">
                    <span className="match-pct">{summary.accuracy_rate}% matched</span>
                    <span className="entry-count">{summary.total_vendor_entries} files</span>
                  </div>
                )}
              </div>
              <ChevronRight size={16} className="history-arrow" />
            </div>
          )
        })}
      </div>
    </div>
  )
}
