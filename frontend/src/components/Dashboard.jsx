import React from 'react'
import { FileStack, CheckCircle, XCircle, AlertTriangle, TrendingUp, Receipt, CreditCard, Landmark, Banknote } from 'lucide-react'

export default function Dashboard({ summary }) {
  if (!summary) return null

  const s = summary

  const accuracyClass = s.accuracy_rate >= 90 ? 'high' : s.accuracy_rate >= 70 ? 'medium' : 'low'

  const categories = [
    {
      name: 'Bills',
      icon: <Receipt size={18} />,
      matched: s.bills_matched,
      total: s.bills_total,
    },
    {
      name: 'Credit Notes',
      icon: <CreditCard size={18} />,
      matched: s.cn_matched,
      total: s.cn_total,
    },
    {
      name: 'TDS',
      icon: <Landmark size={18} />,
      matched: s.tds_matched,
      total: s.tds_total,
    },
    {
      name: 'Payments',
      icon: <Banknote size={18} />,
      matched: s.payments_matched,
      total: s.payments_total,
    },
  ]

  const formatAmount = (amt) => {
    if (amt === 0 || amt === null || amt === undefined) return '₹0'
    return '₹' + Number(amt).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return (
    <div>
      {/* Results Header */}
      <div className="results-header">
        <div>
          <h2 style={{ marginBottom: 4 }}>Reconciliation Results</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            {s.total_vendor_entries} vendor entries vs {s.total_book_entries} book entries
          </p>
        </div>
        <div className={`accuracy-badge ${accuracyClass}`}>
          <TrendingUp size={18} />
          {s.accuracy_rate}% Match Rate
        </div>
      </div>

      {/* Stat Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon purple">
            <FileStack size={22} />
          </div>
          <div className="stat-value">{s.total_vendor_entries + s.total_book_entries}</div>
          <div className="stat-label">Total Entries</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <CheckCircle size={22} />
          </div>
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, #10b981, #34d399)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {s.total_matched}
          </div>
          <div className="stat-label">Matched</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon red">
            <XCircle size={22} />
          </div>
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, #ef4444, #f87171)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {s.total_unmatched_vendor + s.total_unmatched_book}
          </div>
          <div className="stat-label">Unmatched</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon amber">
            <AlertTriangle size={22} />
          </div>
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, #f59e0b, #fbbf24)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {s.total_discrepancies}
          </div>
          <div className="stat-label">Discrepancies</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon blue">
            <TrendingUp size={22} />
          </div>
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {formatAmount(s.net_difference)}
          </div>
          <div className="stat-label">Net Difference</div>
        </div>
      </div>

      {/* Category Progress */}
      <div className="category-grid">
        {categories.map((cat) => {
          const pct = cat.total > 0 ? Math.round((cat.matched / cat.total) * 100) : 0
          const barClass = pct >= 80 ? 'green' : pct >= 50 ? 'amber' : 'red'
          return (
            <div className="category-card" key={cat.name}>
              <div className="category-header">
                <div className="category-name">
                  {cat.icon}
                  {cat.name}
                </div>
                <div className="category-count">
                  {cat.matched}/{cat.total} matched
                </div>
              </div>
              <div className="progress-bar">
                <div className={`progress-fill ${barClass}`} style={{ width: `${pct}%` }}></div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
