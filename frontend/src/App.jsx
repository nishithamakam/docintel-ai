import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import ChatWindow from './components/ChatWindow'
import SourceViewer from './components/SourceViewer'

function App() {
  const [uploadedDocs, setUploadedDocs] = useState([])
  const [sources, setSources] = useState([])
  const [selectedDocIds, setSelectedDocIds] = useState([])  // ← NEW

  // After upload: add doc AND auto-select it
  const handleUploadSuccess = (newDoc) => {
    setUploadedDocs((prev) => [...prev, newDoc])
    setSelectedDocIds((prev) => [...prev, newDoc.doc_id])  // auto-select
  }

  // Toggle a doc's selection state
  const handleToggleDoc = (docId) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    )
  }

  const handleSourcesUpdate = (newSources) => {
    setSources(newSources)
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>🧠 DocIntel AI</h1>
        <span className="app-subtitle">Enterprise Document Intelligence</span>
      </header>

      <div className="app-main">
        <UploadPanel
          uploadedDocs={uploadedDocs}
          onUploadSuccess={handleUploadSuccess}
          selectedDocIds={selectedDocIds}
          onToggleDoc={handleToggleDoc}
        />

        <ChatWindow
          onSourcesUpdate={handleSourcesUpdate}
          hasDocuments={uploadedDocs.length > 0}
          selectedDocIds={selectedDocIds}    // ← pass to chat
        />

        <SourceViewer sources={sources} />
      </div>
    </div>
  )
}

export default App
