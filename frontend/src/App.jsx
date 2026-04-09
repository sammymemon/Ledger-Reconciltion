import React, { useState, useCallback } from 'react'
import axios from 'axios'
import { Settings, RefreshCw } from 'lucide-react'
import FileUpload from './components/FileUpload'
import ProcessingScreen from './components/ProcessingScreen'
import Dashboard from './components/Dashboard'
import ResultsTable from './components/ResultsTable'
import SettingsModal from './components/SettingsModal'
import ExportButton from './components/ExportButton'
import HistorySidebar from './components/HistorySidebar'

const API_BASE = '/api'

export default function App() {
  // App state: 'upload' | 'processing' | 'results'
  const [screen, setScreen] = useState('upload')
  const [sessionId, setSessionId] = useState(null)
  const [report, setReport] = useState(null)
  const [steps, setSteps] = useState([])
  const [error, setError] = useState(null)
  const [showSettings, setShowSettings] = useState(false)

  const handleUpload = useCallback(async (vendorFiles, bookFiles) => {
    setError(null)
    try {
      const formData = new FormData()
      
      // Append all vendor files
      vendorFiles.forEach(file => {
        formData.append('vendor_files', file)
      })
      
      // Append all book files
      bookFiles.forEach(file => {
        formData.append('book_files', file)
      })

      const uploadRes = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const sid = uploadRes.data.session_id
      setSessionId(sid)
      setScreen('processing')
      setSteps([])

      // Start reconciliation
      await axios.post(`${API_BASE}/reconcile/${sid}`)

      // Poll for results
      pollResults(sid)
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.response?.data?.detail || 'Failed to upload files. Make sure the backend is running.')
    }
  }, [])

  const pollResults = useCallback((sid) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/status/${sid}`)
        setSteps(res.data.steps || [])

        if (res.data.status === 'completed') {
          clearInterval(interval)
          const fullRes = await axios.get(`${API_BASE}/results/${sid}`)
          setReport(fullRes.data)
          setScreen('results')
        } else if (res.data.status === 'error') {
          clearInterval(interval)
          setError(res.data.error || 'Reconciliation failed')
          setScreen('upload')
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }, 1500)

    // Safety timeout: stop polling after 5 minutes
    setTimeout(() => clearInterval(interval), 300000)
  }, [])

  const handleReset = useCallback(() => {
    setScreen('upload')
    setSessionId(null)
    setReport(null)
    setSteps([])
    setError(null)
  }, [])

  const handleSelectSession = useCallback(async (sid) => {
    try {
      setSessionId(sid)
      setScreen('processing') // Show processing briefly while loading
      const res = await axios.get(`${API_BASE}/results/${sid}`)
      setReport(res.data)
      setScreen('results')
    } catch (err) {
      console.error('Failed to load session:', err)
      setError('Could not load past session.')
    }
  }, [])

  return (
    <div className="app-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand" style={{ cursor: 'pointer' }} onClick={handleReset}>
          <div className="navbar-logo">L</div>
          <div>
            <div className="navbar-title">LedgerAI</div>
            <div className="navbar-subtitle">Intelligent Reconciliation</div>
          </div>
        </div>
        <div className="navbar-actions">
          {screen === 'results' && (
            <>
              <ExportButton report={report} />
              <button className="btn btn-secondary btn-icon" onClick={handleReset} title="New Reconciliation">
                <RefreshCw size={18} />
              </button>
            </>
          )}
          <button
            className="btn btn-ghost btn-icon"
            onClick={() => setShowSettings(true)}
            title="Settings"
          >
            <Settings size={18} />
          </button>
        </div>
      </nav>

      {/* Error Banner */}
      {error && (
        <div style={{
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-md) var(--space-lg)',
          margin: '0 var(--space-xl) var(--space-xl) var(--space-xl)',
          color: 'var(--danger)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span>⚠️ {error}</span>
          <button className="btn btn-ghost" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Main Layout */}
      <div className="app-main">
        <HistorySidebar onSelectSession={handleSelectSession} currentSessionId={sessionId} />
        
        <div className="main-content">
          {/* Screens */}
          {screen === 'upload' && (
            <FileUpload onUpload={handleUpload} />
          )}

          {screen === 'processing' && (
            <ProcessingScreen steps={steps} />
          )}

          {screen === 'results' && report && (
            <div className="results-section">
              <Dashboard summary={report.summary} />
              <ResultsTable report={report} />
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </div>
  )
}
