import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { sendChatMessage, getConversations, getConversation, deleteConversation, getProject } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Send, Plus, MessageSquare, Trash2 } from 'lucide-react';

export default function ChatPage() {
  const { projectId } = useParams();
  const { user } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [projectDetail, setProjectDetail] = useState(null);

  const messagesEndRef = useRef(null);
  const skipFetchRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversations on mount
  useEffect(() => {
    fetchConversations();
    fetchProject();
  }, []);

  const fetchProject = async () => {
    try {
      const res = await getProject(projectId);
      setProjectDetail(res.project);
    } catch (err) {
      console.error("Failed to load project details", err);
    }
  };

  const fetchConversations = async (forceActiveId = null) => {
    try {
      setLoadingConversations(true);
      const res = await getConversations(projectId, 1);
      const fetchedConvs = res.conversations || [];
      setConversations(fetchedConvs);

      const currentActive = forceActiveId || activeConversationId;
      if (fetchedConvs.length > 0 && !currentActive) {
        setActiveConversationId(fetchedConvs[0].id);
      }
    } catch (err) {
      console.error("Failed to load conversations", err);
    } finally {
      setLoadingConversations(false);
    }
  };

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([
        { role: 'assistant', content: 'Hello! I am DocMind. Start a new conversation or select an existing one from the sidebar.' }
      ]);
      return;
    }

    if (skipFetchRef.current) {
      skipFetchRef.current = false;
      return;
    }

    fetchMessages(activeConversationId);
  }, [activeConversationId]);


  const fetchMessages = async (id) => {
    try {
      setLoading(true);
      const res = await getConversation(id);
      setMessages(res.conversation?.messages || []);
    } catch (err) {
      console.error("Failed to load messages", err);
      setMessages([
        { role: 'system', content: `Error loading conversation: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
  };

  const handleDeleteConversation = async (id) => {
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await deleteConversation(id);
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
      fetchConversations();
    } catch (err) {
      alert(`Failed to delete conversation: ${err.message}`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      setMessages(prev => [...prev, { role: "assistant", content: "", reasoning: "" }]);

      await sendChatMessage(
        userMsg,
        projectId,
        activeConversationId,   // pass active conversation
        5,

        // onNewConversation - update current conversation id in state and fetch list
        (new_conversation) => {
          setActiveConversationId(new_conversation.conversation_id);
          skipFetchRef.current = true;
          fetchConversations(new_conversation.conversation_id);
        },

        // onToken — append each token to the last message
        (token) => {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: updated[updated.length - 1].content + token,
            };
            return updated;
          });
        },

        // onDone
        (meta) => {
          setMessages(prev => {
            const updated = [...prev];
            if (meta.pipeline && meta.pipeline.reasoning_output) {
              updated[updated.length - 1].reasoning = meta.pipeline.reasoning_output;
            }
            return updated;
          });
          setLoading(false);
        },

        // onError — replace empty bubble with error message
        (errMsg) => {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: "⚠️ Something went wrong. Please try again.",
              error: true,
            };
            return updated;
          });
          setLoading(false);
        }
      )
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'system', content: `Error: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-layout">
      {/* Sidebar */}
      <div className="chat-sidebar">
        <div className="chat-sidebar-header">
          <button className="btn btn-primary btn-block" onClick={handleNewChat}>
            <Plus size={16} /> New Chat
          </button>
        </div>
        <div className="chat-list">
          {loadingConversations ? (
            <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--color-text-muted)' }}>Loading...</div>
          ) : conversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--color-text-muted)' }}>No conversations yet</div>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                className={`chat-item ${activeConversationId === conv.id ? 'active' : ''}`}
                onClick={() => setActiveConversationId(conv.id)}
                title={conv.title}
              >
                <span className="chat-item-text">
                  <MessageSquare size={14} style={{ flexShrink: 0 }} />
                  <span className="chat-item-title">{conv.title || "New Conversation"}</span>
                </span>
                <button
                  className="chat-item-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  title="Delete conversation"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        <div className="chat-header">
          <h2>{activeConversationId ? conversations.find(c => c.id === activeConversationId)?.title || "Chat" : "New Chat"}</h2>
          <p>{projectDetail ? `Project: ${projectDetail.project_name}` : "Ask questions about your uploaded documents"}</p>
        </div>

        <div className="chat-messages">
          {messages.length == 0 ? (
            <p>No Messages Yet</p>
          ) :
            (
              messages.map((msg, idx) => (
                <div key={idx} className={`message-wrapper ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? (user?.email?.[0]?.toUpperCase() || 'U') : 'AI'}
                  </div>
                  <div className="message-bubble">
                    {msg.role === 'assistant' && msg.reasoning && (
                      <details style={{ marginBottom: '10px', fontSize: '0.9em', color: 'var(--color-text-muted)' }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>Thinking Process</summary>
                        <div style={{ padding: '8px', background: 'var(--color-bg-secondary)', borderRadius: '4px', marginTop: '4px', whiteSpace: 'pre-wrap' }}>
                          {msg.reasoning}
                        </div>
                      </details>
                    )}
                    <div className="message-content">
                      {msg.content}
                    </div>
                  </div>
                </div>
              ))
            )
          }
          {loading && (
            <div className="message-wrapper assistant">
              <div className="message-avatar">AI</div>
              <div className="message-bubble">
                <div className="message-typing">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-wrapper" onSubmit={handleSubmit}>
          <input
            type="text"
            className="chat-input"
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button type="submit" className="btn-send" disabled={!input.trim() || loading}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
