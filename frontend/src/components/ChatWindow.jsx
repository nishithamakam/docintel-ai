import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, FileUp, Loader2 } from 'lucide-react'
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
        { role: 'assistant', content: `Error: ${errorMsg}` },
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
        <MessageSquare size={14} strokeWidth={1.75} />
        <h2>Chat</h2>
      </div>

      <div className="messages">
                {messages.length === 0 && (
          <div className="welcome-msg">
            {hasDocuments ? (
              <>
                <div className="welcome-badge">
                  <MessageSquare size={22} strokeWidth={1.75} />
                </div>
                <h3>Ready when you are</h3>
                <p>Ask anything about your documents</p>
                <div className="suggestions">
                  <button className="suggestion-chip" onClick={() => setInput('What is this document about?')}>
                    What is this document about?
                  </button>
                  <button className="suggestion-chip" onClick={() => setInput('Summarize the key points')}>
                    Summarize the key points
                  </button>
                  <button className="suggestion-chip" onClick={() => setInput('What are the main sections?')}>
                    What are the main sections?
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="welcome-badge">
                  <FileUp size={22} strokeWidth={1.75} />
                </div>
                <h3>Upload a document</h3>
                <p>Add a PDF, Word, PowerPoint or text file to begin</p>
              </>
            )}
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-role">
              {msg.role === 'user' ? 'You' : 'DocIntel'}
            </div>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}

        {isLoading && (
          <div className="message message-assistant">
            <div className="message-role">DocIntel</div>
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
              ? 'Ask a question…'
              : 'Upload a document to begin'
          }
          disabled={!hasDocuments || isLoading}
          rows={1}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!hasDocuments || !input.trim() || isLoading}
          aria-label="Send message"
        >
          {isLoading
            ? <Loader2 size={15} strokeWidth={1.75} className="spin" />
            : <Send size={15} strokeWidth={1.75} />
          }
        </button>
      </div>
    </main>
  )
}

export default ChatWindow
