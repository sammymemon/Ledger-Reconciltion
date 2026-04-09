import React from 'react'
import { Download } from 'lucide-react'

export default function ExportButton({ report }) {
  const handleExport = () => {
    if (!report) return

    // Build CSV content
    let csv = ''

    // Summary Section
    csv += 'RECONCILIATION SUMMARY\n'
    csv += '======================\n'
    if (report.summary) {
      const s = report.summary
      csv += `Total Vendor Entries,${s.total_vendor_entries}\n`
      csv += `Total Book Entries,${s.total_book_entries}\n`
      csv += `Total Matched,${s.total_matched}\n`
      csv += `Total Unmatched (Vendor),${s.total_unmatched_vendor}\n`
      csv += `Total Unmatched (Book),${s.total_unmatched_book}\n`
      csv += `Discrepancies,${s.total_discrepancies}\n`
      csv += `Accuracy Rate,${s.accuracy_rate}%\n`
      csv += `Net Difference,${s.net_difference}\n`
      csv += '\n'
      csv += `Bills Matched,${s.bills_matched}/${s.bills_total}\n`
      csv += `Credit Notes Matched,${s.cn_matched}/${s.cn_total}\n`
      csv += `TDS Matched,${s.tds_matched}/${s.tds_total}\n`
      csv += `Payments Matched,${s.payments_matched}/${s.payments_total}\n`
    }

    // Matched Entries
    csv += '\n\nMATCHED ENTRIES\n'
    csv += '===============\n'
    csv += 'Status,Type,Vendor Date,Vendor Particulars,Vendor Voucher No,Vendor Debit,Vendor Credit,Book Date,Book Particulars,Book Voucher No,Book Debit,Book Credit,Confidence,AI Reasoning\n'

    if (report.matched_entries) {
      report.matched_entries.forEach(m => {
        const v = m.vendor_entry || {}
        const b = m.book_entry || {}
        csv += `"${m.status}","${m.match_type}","${v.date || ''}","${(v.particulars || '').replace(/"/g, '""')}","${v.voucher_no || ''}",${v.debit || 0},${v.credit || 0},"${b.date || ''}","${(b.particulars || '').replace(/"/g, '""')}","${b.voucher_no || ''}",${b.debit || 0},${b.credit || 0},${Math.round(m.confidence * 100)}%,"${(m.ai_reasoning || '').replace(/"/g, '""')}"\n`
      })
    }

    // Unmatched Vendor
    csv += '\n\nUNMATCHED VENDOR ENTRIES\n'
    csv += '========================\n'
    csv += 'Type,Date,Particulars,Voucher Type,Voucher No,Debit,Credit\n'

    if (report.unmatched_vendor) {
      report.unmatched_vendor.forEach(e => {
        csv += `"${e.entry_type}","${e.date || ''}","${(e.particulars || '').replace(/"/g, '""')}","${e.voucher_type || ''}","${e.voucher_no || ''}",${e.debit || 0},${e.credit || 0}\n`
      })
    }

    // Unmatched Book
    csv += '\n\nUNMATCHED BOOK ENTRIES\n'
    csv += '======================\n'
    csv += 'Type,Date,Particulars,Voucher Type,Voucher No,Debit,Credit\n'

    if (report.unmatched_book) {
      report.unmatched_book.forEach(e => {
        csv += `"${e.entry_type}","${e.date || ''}","${(e.particulars || '').replace(/"/g, '""')}","${e.voucher_type || ''}","${e.voucher_no || ''}",${e.debit || 0},${e.credit || 0}\n`
      })
    }

    // Discrepancies
    csv += '\n\nDISCREPANCIES\n'
    csv += '=============\n'
    csv += 'Type,Vendor Date,Vendor Particulars,Vendor Voucher No,Vendor Debit,Vendor Credit,Book Date,Book Particulars,Book Voucher No,Book Debit,Book Credit,AI Reasoning\n'

    if (report.discrepancies) {
      report.discrepancies.forEach(m => {
        const v = m.vendor_entry || {}
        const b = m.book_entry || {}
        csv += `"${m.match_type}","${v.date || ''}","${(v.particulars || '').replace(/"/g, '""')}","${v.voucher_no || ''}",${v.debit || 0},${v.credit || 0},"${b.date || ''}","${(b.particulars || '').replace(/"/g, '""')}","${b.voucher_no || ''}",${b.debit || 0},${b.credit || 0},"${(m.ai_reasoning || '').replace(/"/g, '""')}"\n`
      })
    }

    // Download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `reconciliation_report_${report.session_id}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <button className="btn btn-secondary" onClick={handleExport} title="Export Report">
      <Download size={16} />
      Export CSV
    </button>
  )
}
