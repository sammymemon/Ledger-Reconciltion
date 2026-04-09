import React, { useState, useRef, useCallback } from 'react'
import { Upload, FileSpreadsheet, FileText, CheckCircle2, Sparkles, X, Plus } from 'lucide-react'

export default function FileUpload({ onUpload }) {
  const [vendorFiles, setVendorFiles] = useState([])
  const [bookFiles, setBookFiles] = useState([])
  const [dragOverVendor, setDragOverVendor] = useState(false)
  const [dragOverBook, setDragOverBook] = useState(false)
  const [uploading, setUploading] = useState(false)

  const vendorRef = useRef(null)
  const bookRef = useRef(null)

  const getFileIcon = (filename) => {
    if (!filename) return null
    const ext = filename.split('.').pop().toLowerCase()
    if (ext === 'pdf') return <FileText size={18} />
    return <FileSpreadsheet size={18} />
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const handleFiles = (files, type) => {
    const validFiles = Array.from(files).filter(file => {
      const ext = file.name.split('.').pop().toLowerCase()
      return ['pdf', 'xlsx', 'xls'].includes(ext)
    })

    if (validFiles.length < files.length) {
      alert('Some files were skipped. Only PDF and Excel files are supported.')
    }

    if (type === 'vendor') {
      setVendorFiles(prev => [...prev, ...validFiles])
      setDragOverVendor(false)
    } else {
      setBookFiles(prev => [...prev, ...validFiles])
      setDragOverBook(false)
    }
  }

  const handleDrop = useCallback((e, type) => {
    e.preventDefault()
    e.stopPropagation()
    handleFiles(e.dataTransfer.files, type)
  }, [])

  const handleFileSelect = useCallback((e, type) => {
    handleFiles(e.target.files, type)
    // Reset input so the same file can be selected again if removed
    e.target.value = ''
  }, [])

  const removeFile = (index, type) => {
    if (type === 'vendor') {
      setVendorFiles(prev => prev.filter((_, i) => i !== index))
    } else {
      setBookFiles(prev => prev.filter((_, i) => i !== index))
    }
  }

  const handleSubmit = async () => {
    if (vendorFiles.length === 0 || bookFiles.length === 0) return
    setUploading(true)
    try {
      await onUpload(vendorFiles, bookFiles)
    } catch (err) {
      console.error(err)
    }
    setUploading(false)
  }

  const renderFileList = (files, type) => {
    if (files.length === 0) return null
    return (
      <div className="file-list">
        {files.map((file, idx) => (
          <div key={`${type}-${idx}`} className="file-item">
            <div className="file-item-info">
              {getFileIcon(file.name)}
              <span className="file-name" title={file.name}>{file.name}</span>
              <span className="file-size">({formatFileSize(file.size)})</span>
            </div>
            <button 
              className="btn-remove" 
              onClick={(e) => { e.stopPropagation(); removeFile(idx, type); }}
              title="Remove file"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="upload-section">
      <div className="upload-header">
        <h1>
          <Sparkles size={32} style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle', color: 'var(--accent-primary-light)' }} />
          Ledger Reconciliation
        </h1>
        <p>Upload multiple vendor & book ledger files for AI-powered matching</p>
      </div>

      <div className="upload-grid">
        {/* Vendor Ledger */}
        <div className="upload-column">
          <div
            className={`upload-zone ${vendorFiles.length > 0 ? 'has-file' : ''} ${dragOverVendor ? 'drag-over' : ''}`}
            onClick={() => vendorRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOverVendor(true) }}
            onDragLeave={() => setDragOverVendor(false)}
            onDrop={(e) => handleDrop(e, 'vendor')}
          >
            <input
              ref={vendorRef}
              type="file"
              multiple
              accept=".pdf,.xlsx,.xls"
              onChange={(e) => handleFileSelect(e, 'vendor')}
              style={{ display: 'none' }}
            />
            <div className="upload-zone-icon">
              {vendorFiles.length > 0 ? <Plus size={28} /> : <Upload size={28} />}
            </div>
            <div className="upload-zone-title">
              {vendorFiles.length > 0 ? 'Add More Vendor Files' : 'Vendor Ledger'}
            </div>
            <div className="upload-zone-subtitle">
              Drop PDF or Excel files here
            </div>
          </div>
          {renderFileList(vendorFiles, 'vendor')}
        </div>

        {/* Book Ledger */}
        <div className="upload-column">
          <div
            className={`upload-zone ${bookFiles.length > 0 ? 'has-file' : ''} ${dragOverBook ? 'drag-over' : ''}`}
            onClick={() => bookRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOverBook(true) }}
            onDragLeave={() => setDragOverBook(false)}
            onDrop={(e) => handleDrop(e, 'book')}
          >
            <input
              ref={bookRef}
              type="file"
              multiple
              accept=".pdf,.xlsx,.xls"
              onChange={(e) => handleFileSelect(e, 'book')}
              style={{ display: 'none' }}
            />
            <div className="upload-zone-icon">
              {bookFiles.length > 0 ? <Plus size={28} /> : <Upload size={28} />}
            </div>
            <div className="upload-zone-title">
              {bookFiles.length > 0 ? 'Add More Book Files' : 'Book Ledger'}
            </div>
            <div className="upload-zone-subtitle">
              Drop PDF or Excel files here
            </div>
          </div>
          {renderFileList(bookFiles, 'book')}
        </div>
      </div>

      <div className="upload-actions">
        <button
          className="btn btn-primary btn-lg"
          disabled={vendorFiles.length === 0 || bookFiles.length === 0 || uploading}
          onClick={handleSubmit}
        >
          {uploading ? (
            <>
              <span className="processing-spinner" style={{ width: 18, height: 18, borderWidth: 2, marginRight: 8 }}></span>
              Uploading...
            </>
          ) : (
            <>
              <Sparkles size={18} style={{ marginRight: 8 }} />
              Start Reconciliation
            </>
          )}
        </button>
      </div>

      <div style={{ marginTop: 'var(--space-xl)', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          Supports multiple PDF & Excel (.xlsx) files • AI extraction & matching • Powered by Grok
        </p>
      </div>
    </div>
  )
}

