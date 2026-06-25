import { FileText, Quote } from 'lucide-react'

function SourceViewer({ sources }) {
  return (
    <aside className="source-viewer">
      <h2>Sources</h2>

      {sources.length === 0 ? (
        <div className="empty-sources">
          <Quote size={20} strokeWidth={1.5} className="empty-icon" />
          <p>Citations will appear here after you ask a question.</p>
        </div>
      ) : (
        <div className="source-list">
          <p className="source-count">
            {sources.length} chunk{sources.length !== 1 ? 's' : ''} retrieved
          </p>

          {sources.map((src, idx) => (
            <div key={idx} className="source-card">
              <div className="source-header">
                <FileText size={13} strokeWidth={1.5} className="source-icon" />
                <span className="source-filename">{src.doc_name}</span>
                <span className="source-page">{src.location || `p. ${src.page}`}</span>

              </div>

              <div className="score-row">
                <span className="score-label">Relevance</span>
                <div className="score-bar-bg">
                  <div
                    className="score-bar-fill"
                    style={{ width: `${Math.round(src.score * 100)}%` }}
                  />
                </div>
                <span className="score-value">
                  {Math.round(src.score * 100)}%
                </span>
              </div>

              <div className="source-snippet">
                {src.snippet}
                {src.snippet.length >= 300 ? '…' : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}

export default SourceViewer
