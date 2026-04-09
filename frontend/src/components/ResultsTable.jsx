import React, { useState, useMemo } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Eye, Search } from 'lucide-react'

export default function ResultsTable({ report }) {
  const [activeTab, setActiveTab] = useState('matched')
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedRow, setExpandedRow] = useState(null)

  const tabs = [
    { id: 'matched', label: 'Matched', count: report.matched_entries?.length || 0, icon: <CheckCircle size={14} /> },
    { id: 'unmatched_vendor', label: 'Unmatched Vendor', count: report.unmatched_vendor?.length || 0, icon: <XCircle size={14} /> },
    { id: 'unmatched_book', label: 'Unmatched Book', count: report.unmatched_book?.length || 0, icon: <XCircle size={14} /> },
    { id: 'discrepancies', label: 'Discrepancies', count: report.discrepancies?.length || 0, icon: <AlertTriangle size={14} /> },
  ]

  const formatAmount = (amt) => {
    if (!amt || amt === 0) return '-'
    return '₹' + Number(amt).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const getStatusBadge = (status) => {
    const map = {
      matched: { cls: 'matched', label: '✅ Matched' },
      unmatched: { cls: 'unmatched', label: '❌ Unmatched' },
      discrepancy: { cls: 'discrepancy', label: '⚠️ Discrepancy' },
      needs_review: { cls: 'review', label: '🔍 Review' },
    }
    const s = map[status] || map.unmatched
    return <span className={`status-badge ${s.cls}`}>{s.label}</span>
  }

  const getTypeLabel = (type) => {
    const map = {
      bill: '📄 Bill',
      credit_note: '📝 Credit Note',
      tds: '🏛️ TDS',
      payment: '💳 Payment',
      unknown: '❓ Other',
    }
    return map[type] || map.unknown
  }

  // Filter data based on search
  const filteredData = useMemo(() => {
    let data = []

    if (activeTab === 'matched') {
      data = report.matched_entries || []
    } else if (activeTab === 'unmatched_vendor') {
      data = report.unmatched_vendor || []
    } else if (activeTab === 'unmatched_book') {
      data = report.unmatched_book || []
    } else if (activeTab === 'discrepancies') {
      data = report.discrepancies || []
    }

    if (!searchTerm) return data

    const term = searchTerm.toLowerCase()
    return data.filter(item => {
      const searchFields = activeTab === 'matched' || activeTab === 'discrepancies'
        ? [
            item.vendor_entry?.particulars,
            item.vendor_entry?.voucher_no,
            item.book_entry?.particulars,
            item.book_entry?.voucher_no,
          ]
        : [item.particulars, item.voucher_no, item.date]

      return searchFields.some(f => f && f.toLowerCase().includes(term))
    })
  }, [activeTab, report, searchTerm])

  const renderMatchedTable = () => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Status</th>
            <th>Type</th>
            <th>Vendor - Date</th>
            <th>Vendor - Particulars</th>
            <th>Vendor - Voucher No</th>
            <th>Vendor - Amt</th>
            <th>Book - Date</th>
            <th>Book - Particulars</th>
            <th>Book - Voucher No</th>
            <th>Book - Amt</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {filteredData.map((match, idx) => {
            const v = match.vendor_entry || {}
            const b = match.book_entry || {}
            const rowClass = match.status === 'matched' ? 'row-matched'
              : match.status === 'discrepancy' ? 'row-discrepancy'
              : match.status === 'needs_review' ? 'row-review' : ''

            return (
              <React.Fragment key={idx}>
                <tr
                  className={rowClass}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setExpandedRow(expandedRow === idx ? null : idx)}
                >
                  <td>{idx + 1}</td>
                  <td>{getStatusBadge(match.status)}</td>
                  <td>{getTypeLabel(match.match_type)}</td>
                  <td>{v.date || '-'}</td>
                  <td style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {v.particulars || '-'}
                  </td>
                  <td>{v.voucher_no || '-'}</td>
                  <td>
                    {v.debit > 0 && <span className="amount-debit">{formatAmount(v.debit)}</span>}
                    {v.credit > 0 && <span className="amount-credit">{formatAmount(v.credit)}</span>}
                    {!v.debit && !v.credit && '-'}
                  </td>
                  <td>{b.date || '-'}</td>
                  <td style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {b.particulars || '-'}
                  </td>
                  <td>{b.voucher_no || '-'}</td>
                  <td>
                    {b.debit > 0 && <span className="amount-debit">{formatAmount(b.debit)}</span>}
                    {b.credit > 0 && <span className="amount-credit">{formatAmount(b.credit)}</span>}
                    {!b.debit && !b.credit && '-'}
                  </td>
                  <td>
                    <span style={{
                      color: (match.confidence > 90 || match.confidence >= 0.9 && match.confidence <= 1) ? 'var(--success)' : 
                             (match.confidence > 70 || match.confidence >= 0.7 && match.confidence <= 1) ? 'var(--warning)' : 'var(--danger)',
                      fontWeight: 600
                    }}>
                      {match.confidence > 1 ? Math.round(match.confidence) : Math.round(match.confidence * 100)}%
                    </span>
                  </td>
                </tr>
                {expandedRow === idx && match.ai_reasoning && (
                  <tr>
                    <td colSpan={12} style={{ background: 'var(--bg-glass)', padding: '12px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <Eye size={14} style={{ color: 'var(--accent-primary-light)', flexShrink: 0, marginTop: 2 }} />
                        <div>
                          <strong style={{ fontSize: '0.8rem', color: 'var(--accent-primary-light)' }}>AI Reasoning:</strong>
                          <p className="ai-reasoning" style={{ marginTop: 4, maxWidth: '100%' }}>{match.ai_reasoning}</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            )
          })}
        </tbody>
      </table>

      {filteredData.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon"><CheckCircle size={32} /></div>
          <p>No entries found</p>
        </div>
      )}
    </div>
  )

  const renderUnmatchedTable = () => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Type</th>
            <th>Date</th>
            <th>Particulars</th>
            <th>Voucher Type</th>
            <th>Voucher No</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          {filteredData.map((entry, idx) => (
            <tr key={idx} className="row-unmatched">
              <td>{idx + 1}</td>
              <td>{getTypeLabel(entry.entry_type)}</td>
              <td>{entry.date || '-'}</td>
              <td style={{ maxWidth: 250 }}>{entry.particulars || '-'}</td>
              <td>{entry.voucher_type || '-'}</td>
              <td>{entry.voucher_no || '-'}</td>
              <td>{entry.debit > 0 ? <span className="amount-debit">{formatAmount(entry.debit)}</span> : '-'}</td>
              <td>{entry.credit > 0 ? <span className="amount-credit">{formatAmount(entry.credit)}</span> : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {filteredData.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon"><CheckCircle size={32} /></div>
          <p>All entries matched! 🎉</p>
        </div>
      )}
    </div>
  )

  return (
    <div>
      {/* Tabs */}
      <div className="tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => { setActiveTab(tab.id); setExpandedRow(null) }}
          >
            {tab.icon}
            {tab.label}
            <span className="tab-badge">{tab.count}</span>
          </button>
        ))}
      </div>

      {/* Search */}
      <div style={{ marginBottom: 'var(--space-md)', position: 'relative' }}>
        <Search size={16} style={{
          position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
          color: 'var(--text-muted)'
        }} />
        <input
          type="text"
          className="form-input"
          placeholder="Search by name, voucher number..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ paddingLeft: 40 }}
        />
      </div>

      {/* Table */}
      {(activeTab === 'matched' || activeTab === 'discrepancies') ? renderMatchedTable() : renderUnmatchedTable()}
    </div>
  )
}
