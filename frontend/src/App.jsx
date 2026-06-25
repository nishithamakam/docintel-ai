import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import UploadPanel from './components/UploadPanel'
import ChatWindow from './components/ChatWindow'
import SourceViewer from './components/SourceViewer'

function App() {
  const [uploadedDocs, setUploadedDocs] = useState([])
  const [sources, setSources] = useState([])
  const [selectedDocIds, setSelectedDocIds] = useState([])

  const handleUploadSuccess = (newDoc) => {
    setUploadedDocs((prev) => [...prev, newDoc])
    setSelectedDocIds((prev) => [...prev, newDoc.doc_id])
  }

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
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={16} strokeWidth={2} />
          </div>
          <h1>Document Intelligence</h1>
        </div>
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
          selectedDocIds={selectedDocIds}
        />

        <SourceViewer sources={sources} />
      </div>
    </div>
  )
}

export default App
