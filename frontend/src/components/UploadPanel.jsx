import { useState, useRef } from 'react'
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { uploadPdf } from '../api/client'

function UploadPanel({ uploadedDocs, onUploadSuccess, selectedDocIds, onToggleDoc }) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileChange = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    setError(null)
    setIsUploading(true)

    try {
      const result = await uploadPdf(file)
      onUploadSuccess(result)
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Upload failed'
      setError(message)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleClickUpload = () => fileInputRef.current?.click()

  return (
    <aside className="upload-panel">
      <h2>Documents</h2>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md,.csv,.json,.log,.html,.xml,.yaml,.yml"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <button
        className="upload-btn"
        onClick={handleClickUpload}
        disabled={isUploading}
      >
        {isUploading ? (
          <>
            <Loader2 size={14} strokeWidth={1.75} className="spin" />
            <span>Uploading</span>
          </>
        ) : (
          <>
            <Upload size={14} strokeWidth={1.75} />
            <span>Upload File</span>
          </>
        )}
      </button>

      {error && (
        <div className="error-msg">
          <AlertCircle size={14} strokeWidth={1.75} />
          <span>{error}</span>
        </div>
      )}

      <div className="doc-list">
        <h3>Library ({uploadedDocs.length})</h3>

        {uploadedDocs.length === 0 ? (
          <p className="empty-msg">No documents uploaded</p>
        ) : (
          <>
            <p className="doc-hint">Select documents to query</p>
            {uploadedDocs.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.doc_id)
              return (
                <label
                  key={doc.doc_id}
                  className={`doc-item ${isSelected ? 'doc-item-selected' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onToggleDoc(doc.doc_id)}
                  />
                  <FileText size={14} strokeWidth={1.5} className="doc-icon" />
                  <div className="doc-info">
                    <div className="doc-name">{doc.filename}</div>
                    <div className="doc-stats">
                      {doc.pages} pages · {doc.chunks} chunks
                    </div>
                  </div>
                </label>
              )
            })}
          </>
        )}
      </div>
    </aside>
  )
}

export default UploadPanel
