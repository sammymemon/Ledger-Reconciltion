import React, { useState } from 'react'
import axios from 'axios'
import { X, Key, CheckCircle, XCircle, Loader } from 'lucide-react'

export default function SettingsModal({ onClose }) {
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [status, setStatus] = useState(null) // null | 'success' | 'error'
  const [message, setMessage] = useState('')
  const [isKeySaved, setIsKeySaved] = useState(false)
  const [maskedKey, setMaskedKey] = useState('')
  const [model, setModel] = useState('grok-2-latest')

  React.useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const res = await axios.get('/api/settings')
      if (res.data.api_key_set) {
        setIsKeySaved(true)
        setMaskedKey(res.data.masked_key)
        if (res.data.model) setModel(res.data.model)
      }
    } catch (err) {
      console.error('Failed to fetch settings')
    }
  }

  const handleSave = async () => {
    const trimmedKey = apiKey.trim()
    if (!trimmedKey) return

    // User requirement: grok api key gsk se start hoti hai (support gsk- or gsk_)
    if (!trimmedKey.startsWith('gsk-') && !trimmedKey.startsWith('xai-') && !trimmedKey.startsWith('gsk_')) {
      setStatus('error')
      setMessage('⚠️ Key should start with "gsk_" or "gsk-" (Grok API Key syntax)')
      return
    }

    setSaving(true)
    try {
      await axios.post('/api/settings', { api_key: trimmedKey || undefined, model })
      setMessage('Settings saved successfully!')
      setStatus('success')
      if (trimmedKey) {
        setIsKeySaved(true)
        setApiKey('')
      }
      fetchSettings()
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to save settings')
      setStatus('error')
    }
    setSaving(false)
  }

  const handleTest = async () => {
    setTesting(true)
    setStatus(null)
    try {
      const res = await axios.get('/api/settings/test')
      if (res.data.connected) {
        setStatus('success')
        setMessage('✅ Connection successful! Grok API is working.')
      } else {
        setStatus('error')
        setMessage('❌ ' + (res.data.message || 'Connection failed'))
      }
    } catch (err) {
      setStatus('error')
      setMessage('Connection test failed. Make sure the backend is running.')
    }
    setTesting(false)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">
            <Key size={20} style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle' }} />
            Settings
          </h3>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="form-group">
          <label className="form-label">
            Grok API Key 
            {isKeySaved && <span style={{ marginLeft: 8, color: 'var(--success)', fontSize: '0.75rem' }}>(Saved: {maskedKey})</span>}
          </label>
          <input
            type="password"
            className="form-input"
            placeholder={isKeySaved ? "Update your API key..." : "gsk-xxxxxxxxxxxxxxxxxxxxxx"}
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
          />
          <p className="form-hint">
            Grok API keys usually start with <code style={{ color: 'var(--accent-primary-light)' }}>gsk_</code> or <code style={{ color: 'var(--accent-primary-light)' }}>gsk-</code>.
            Get it from <a href="https://console.x.ai" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-primary-light)' }}>console.x.ai</a>
          </p>
        </div>

        <div className="form-group" style={{ marginTop: 'var(--space-md)' }}>
          <label className="form-label">Grok Model (AI Engine)</label>
          <select 
            className="form-input" 
            value={model} 
            onChange={e => setModel(e.target.value)}
            style={{ appearance: 'auto', paddingRight: 'var(--space-md)' }}
          >
            <option value="grok-2-latest">Grok 2 (High Quality)</option>
            <option value="grok-beta">Grok Beta (Latest features)</option>
            <option value="grok-3-mini-fast">Grok 3 Mini (Fastest)</option>
          </select>
          <p className="form-hint">"Grok 2" is recommended for high accuracy ledger parsing.</p>
        </div>

        {status && (
          <div className={`connection-status ${status === 'success' ? 'connected' : 'disconnected'}`}>
            <span className={`status-dot ${status === 'success' ? 'green' : 'red'}`}></span>
            {message}
          </div>
        )}

        <div style={{ display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-lg)' }}>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || !apiKey.trim()}
            style={{ flex: 1 }}
          >
            {saving ? <Loader size={16} className="spin" /> : <CheckCircle size={16} />}
            Save Key
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleTest}
            disabled={testing}
          >
            {testing ? <Loader size={16} /> : '🔌'}
            Test Connection
          </button>
        </div>
      </div>
    </div>
  )
}
