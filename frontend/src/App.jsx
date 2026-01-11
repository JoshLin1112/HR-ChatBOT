import React, { useState, useEffect, useRef } from 'react';
import { Send, RefreshCw, Sparkles, Plus, MessageSquare, Menu, X, Trash2 } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChatMessage } from './components/ChatMessage';
import { WelcomeSection } from './components/WelcomeSection';
import { LoadingBubble } from './components/LoadingBubble';

export default function ModernRAGChat() {
  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem('chat_sessions');
    if (saved) {
      return JSON.parse(saved);
    }
    const initialId = crypto.randomUUID();
    return [{ id: initialId, title: '新對話', messages: [], createdAt: Date.now() }];
  });

  const [currentSessionId, setCurrentSessionId] = useState(() => {
    const saved = localStorage.getItem('chat_sessions');
    if (saved) {
      const parsed = JSON.parse(saved);
      return parsed[0]?.id || crypto.randomUUID();
    }
    return null;
  });

  useEffect(() => {
    if (!currentSessionId && sessions.length > 0) {
      setCurrentSessionId(sessions[0].id);
    }
  }, [sessions, currentSessionId]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  const currentSession = sessions.find(s => s.id === currentSessionId) || sessions[0];
  const messages = currentSession?.messages || [];

  useEffect(() => {
    localStorage.setItem('chat_sessions', JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, currentSessionId]);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      const data = await response.json();
      setApiStatus(data.system_initialized ? 'ready' : 'initializing');
    } catch (error) {
      setApiStatus('error');
    }
  };

  const handleNewChat = () => {
    if (currentSession?.messages.length === 0) {
      return;
    }
    const newId = crypto.randomUUID();
    const newSession = {
      id: newId,
      title: '新對話',
      messages: [],
      createdAt: Date.now()
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newId);
  };

  const handleSelectSession = (id) => {
    setCurrentSessionId(id);
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const updateSessionMessages = (sessionId, newMessages) => {
    setSessions(prev => prev.map(session => {
      if (session.id === sessionId) {
        let title = session.title;
        if (session.messages.length === 0 && newMessages.length > 0) {
          const firstMsg = newMessages[0];
          if (firstMsg.type === 'user') {
            title = firstMsg.content.slice(0, 15) + (firstMsg.content.length > 15 ? '...' : '');
          }
        }
        return { ...session, title, messages: newMessages };
      }
      return session;
    }));
  };

  const deleteSession = (e, sessionId) => {
    e.stopPropagation();
    const newSessions = sessions.filter(s => s.id !== sessionId);
    if (newSessions.length === 0) {
      const newId = crypto.randomUUID();
      setSessions([{
        id: newId,
        title: '新對話',
        messages: [],
        createdAt: Date.now()
      }]);
      setCurrentSessionId(newId);
    } else {
      setSessions(newSessions);
      if (sessionId === currentSessionId) {
        setCurrentSessionId(newSessions[0].id);
      }
    }
  };

  const sendMessage = async (text = input) => {
    const messageToSend = text.trim();
    if (!messageToSend || loading) return;

    const activeId = currentSessionId;
    const userMessage = {
      type: 'user',
      content: messageToSend,
      timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
    };

    const updatedMessages = [...(currentSession.messages || []), userMessage];
    updateSessionMessages(activeId, updatedMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: messageToSend,
          thread_id: activeId
        })
      });

      const data = await response.json();

      if (data.success) {
        const botMessage = {
          type: 'bot',
          content: data.answer,
          rewritten_query: data.rewritten_query,
          context: data.context,
          timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
        };
        updateSessionMessages(activeId, [...updatedMessages, botMessage]);
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      const errorMessage = {
        type: 'error',
        content: `抱歉，系統目前無法回應：${error.message}`,
        timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
      };
      updateSessionMessages(activeId, [...updatedMessages, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = () => {
    updateSessionMessages(currentSessionId, []);
  };

  return (
    <div className="flex h-screen bg-dark-950 text-slate-200 font-sans overflow-hidden">
      {/* Sidebar */}
      <AnimatePresence mode='wait'>
        {isSidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="bg-dark-900 border-r border-dark-700 flex flex-col h-full flex-shrink-0 absolute md:relative z-20"
          >
            <div className="p-4 border-b border-dark-700 flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold text-slate-100">
                <Sparkles className="w-5 h-5 text-primary-400" />
                <span>對話紀錄</span>
              </div>
              <button onClick={() => setIsSidebarOpen(false)} className="md:hidden p-1.5 text-slate-400 hover:text-slate-200 hover:bg-dark-700 rounded-lg transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4">
              <button
                onClick={handleNewChat}
                className="w-full flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white py-3 px-4 rounded-xl transition-all shadow-lg shadow-primary-600/20 active:scale-[0.98] font-medium"
              >
                <Plus className="w-5 h-5" />
                新對話
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
              {sessions.map(session => (
                <div key={session.id} className="relative group">
                  <button
                    onClick={() => handleSelectSession(session.id)}
                    className={`w-full text-left p-3 rounded-xl flex items-center gap-3 transition-all ${currentSessionId === session.id
                        ? 'bg-dark-700 text-white'
                        : 'hover:bg-dark-800 text-slate-300'
                      }`}
                  >
                    <MessageSquare className={`w-4 h-4 flex-shrink-0 ${currentSessionId === session.id ? 'text-primary-400' : 'text-slate-500'
                      }`} />
                    <div className="truncate text-sm font-medium flex-1 pr-6">
                      {session.title || '新對話'}
                    </div>
                  </button>
                  <button
                    onClick={(e) => deleteSession(e, session.id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                    title="刪除對話"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-dark-700 text-xs text-slate-500 flex justify-between items-center">
              <span>{sessions.length} 個對話</span>
              <div className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${apiStatus === 'ready' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="text-slate-400">{apiStatus === 'ready' ? 'Online' : 'Offline'}</span>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full relative w-full">
        <header className="h-16 border-b border-dark-800 bg-dark-900/80 backdrop-blur-xl flex items-center justify-between px-4 md:px-6 flex-shrink-0 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 -ml-2 text-slate-400 hover:text-slate-200 hover:bg-dark-700 rounded-lg transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="font-bold text-white tracking-tight text-lg">智能差勤助手</h1>
          </div>
          <button
            onClick={clearHistory}
            className="p-2 text-slate-400 hover:text-primary-400 hover:bg-dark-700 rounded-lg transition-all"
            title="清空此對話"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-8 scroll-smooth bg-dark-950">
          <div className="max-w-3xl mx-auto space-y-6 pb-32">
            <AnimatePresence>
              {messages.length === 0 ? (
                <WelcomeSection onSelectExample={(ex) => sendMessage(ex)} />
              ) : (
                <>
                  {messages.map((msg, idx) => (
                    <ChatMessage key={idx} msg={msg} />
                  ))}
                  {loading && <LoadingBubble />}
                </>
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-dark-950 via-dark-950/95 to-transparent pb-6 pt-12 px-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative bg-dark-800 border border-dark-600 rounded-2xl shadow-2xl shadow-black/40 focus-within:border-primary-500/50 focus-within:ring-2 focus-within:ring-primary-500/20 transition-all duration-300">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="請描述您的問題..."
                className="w-full bg-transparent pl-4 pr-16 py-4 resize-none outline-none text-slate-100 placeholder-slate-500 min-h-[60px] max-h-[200px]"
                rows="1"
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim() || apiStatus !== 'ready'}
                className="absolute right-2 bottom-2 p-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-500 disabled:bg-dark-600 disabled:text-slate-500 transition-all shadow-lg shadow-primary-600/30 active:scale-95"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <p className="text-center text-[11px] text-slate-500 mt-3">
              AI 生成內容僅供參考，正式請假規範請依照公司規章為準
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
