import React from 'react'
import { Loader, CheckCircle, Circle, Zap } from 'lucide-react'

export default function ProcessingScreen({ steps }) {
  return (
    <div className="processing-section">
      <div className="processing-spinner"></div>
      <h2 className="processing-title">Reconciling Ledgers...</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
        AI is analyzing and matching your entries
      </p>

      <ul className="processing-steps">
        {steps.map((step, idx) => (
          <li key={idx} className="processing-step">
            <span className="processing-step-icon">
              {idx === steps.length - 1 ? (
                step.startsWith('✅') || step.startsWith('❌') ? (
                  <CheckCircle size={18} style={{ color: step.startsWith('✅') ? 'var(--success)' : 'var(--danger)' }} />
                ) : (
                  <Zap size={18} style={{ color: 'var(--accent-primary-light)' }} />
                )
              ) : (
                <CheckCircle size={16} style={{ color: 'var(--success)', opacity: 0.6 }} />
              )}
            </span>
            {step}
          </li>
        ))}
        {steps.length === 0 && (
          <li className="processing-step">
            <span className="processing-step-icon">
              <Circle size={16} style={{ color: 'var(--text-muted)' }} />
            </span>
            Initializing...
          </li>
        )}
      </ul>
    </div>
  )
}
