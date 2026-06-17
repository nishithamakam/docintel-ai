import { useState, useRef, useEffect } from 'react'
import { askQuestion } from '../api/client'

function ChatWindow({ onSourcesUpdate, hasDocuments, selectedDocIds }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    const userMsg = { role: 'user', content: trimmed }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setIsLoading(true)

    try {
      const result = await askQuestion(trimmed, messages, selectedDocIds)
      const aiMsg = { role: 'assistant', content: result.answer }
      setMessages([...newMessages, aiMsg])
      onSourcesUpdate(result.sources || [])
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to get answer'
      setMessages([
        ...newMessages,
        { role: 'assistant', content: `⚠️ Error: ${errorMsg}` },
      ])
      onSourcesUpdate([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <main className="chat-window">
      <div className="chat-header">
        <h2>💬 Ask Your Documents</h2>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome-msg">
            {hasDocuments ? (
              <>
                <h3>👋 Ready to answer questions!</h3>
                <p>Try asking:</p>
                <ul>
                  <li>"What is this document about?"</li>
                  <li>"Summarize the key points"</li>
                  <li>"What are the main sections?"</li>
                </ul>
              </>
            ) : (
              <>
                <h3>📤 Upload a PDF to get started</h3>
                <p>Use the panel on the left to upload your first document.</p>
              </>
            )}
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-role">
              {msg.role === 'user' ? '👤 You' : '🤖 DocIntel AI'}
            </div>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}

        {isLoading && (
          <div className="message message-assistant">
            <div className="message-role">🤖 DocIntel AI</div>
            <div className="message-content thinking">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="input-area">
        <textarea
          className="message-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            hasDocuments
              ? 'Ask a question... (Enter to send, Shift+Enter for new line)'
              : 'Upload a PDF first to start asking questions'
          }
          disabled={!hasDocuments || isLoading}
          rows={2}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!hasDocuments || !input.trim() || isLoading}
        >
          {isLoading ? '⏳' : '🚀'}
        </button>
      </div>
    </main>
  )
}

export default ChatWindow
