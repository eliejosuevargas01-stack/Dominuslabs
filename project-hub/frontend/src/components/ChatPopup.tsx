import { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, Search, ArrowLeft, X, Loader2, MessageCircle } from 'lucide-react';
import { API_BASE, fetchWithAuth } from '../services/api';

export default function ChatPopup() {
  const [isOpen, setIsOpen] = useState(false);
  const [leads, setLeads] = useState<any[]>([]);
  const [loadingLeads, setLoadingLeads] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Active conversation state
  const [activeLeadId, setActiveLeadId] = useState<string | null>(null);
  const [activeLead, setActiveLead] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  
  // Message composing state
  const [replyText, setReplyText] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  
  // Real-time notifications state
  const [unreadLeads, setUnreadLeads] = useState<Record<string, boolean>>({});
  const [hasNewUpdate, setHasNewUpdate] = useState(false);
  
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Helper to sort leads by last interaction time descending
  const sortLeadsByInteraction = (leadsList: any[]) => {
    return [...leadsList].sort((a: any, b: any) => {
      const t1 = a.last_interaction ? new Date(a.last_interaction).getTime() : 0;
      const t2 = b.last_interaction ? new Date(b.last_interaction).getTime() : 0;
      return t2 - t1;
    });
  };

  // Fetch CRM leads list
  const fetchLeads = async (silent = false) => {
    if (!silent) setLoadingLeads(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/leads`);
      if (res.ok) {
        const data = await res.json();
        setLeads(prevLeads => {
          const merged = data.map((fetchedLead: any) => {
            const localLead = prevLeads.find(l => String(l.id) === String(fetchedLead.id));
            if (localLead && localLead.last_interaction) {
              if (!fetchedLead.last_interaction) {
                return { ...fetchedLead, last_interaction: localLead.last_interaction };
              }
              const localTime = new Date(localLead.last_interaction).getTime();
              const fetchedTime = new Date(fetchedLead.last_interaction).getTime();
              if (localTime > fetchedTime) {
                return { ...fetchedLead, last_interaction: localLead.last_interaction };
              }
            }
            return fetchedLead;
          });
          return sortLeadsByInteraction(merged);
        });
      }
    } catch (err) {
      console.error('Erro ao buscar leads no popup:', err);
    } finally {
      if (!silent) setLoadingLeads(false);
    }
  };

  // Fetch messages for a specific lead
  const fetchConversation = async (leadId: string, silent = false) => {
    if (!silent) setLoadingMessages(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/conversations/${leadId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (err) {
      console.error('Erro ao buscar conversas no popup:', err);
    } finally {
      if (!silent) setLoadingMessages(false);
    }
  };

  // Initial load
  useEffect(() => {
    const token = localStorage.getItem("admin_token");
    if (!token || token === "null" || token === "undefined") return;
    
    fetchLeads();
  }, []);

  // Listen to SSE updates
  useEffect(() => {
    const token = localStorage.getItem("admin_token");
    if (!token || token === "null" || token === "undefined") return;

    const sseUrl = `${API_BASE}/webhooks/events/crm-chats?token=${encodeURIComponent(token)}`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'reload' && data.lead_id) {
          const updatedLeadId = String(data.lead_id);
          
          // 1. If currently chatting with this lead, refresh conversation
          if (activeLeadId && String(activeLeadId) === updatedLeadId) {
            fetchConversation(updatedLeadId, true);
          } else {
            // 2. Otherwise mark as unread and trigger global badge
            setUnreadLeads(prev => ({ ...prev, [updatedLeadId]: true }));
            setHasNewUpdate(true);
          }
          
          // Instantly update local last_interaction and move to the top
          setLeads(prevLeads => {
            const updated = prevLeads.map(l => {
              if (String(l.id) === updatedLeadId) {
                return { ...l, last_interaction: new Date().toISOString() };
              }
              return l;
            });
            return sortLeadsByInteraction(updated);
          });
          
          // 3. Silently update leads list to show last_interaction updates
          fetchLeads(true);
        }
      } catch (err) {
        // Fallback if message is plain string "reload"
        if (event.data === 'reload') {
          fetchLeads(true);
          if (activeLeadId) {
            fetchConversation(activeLeadId, true);
          }
        }
      }
    };

    eventSource.onerror = (err) => {
      console.error('Global SSE Error in ChatPopup:', err);
    };

    return () => {
      eventSource.close();
    };
  }, [activeLeadId]);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeLeadId]);

  const handleOpenLeadChat = (lead: any) => {
    setActiveLeadId(lead.id);
    setActiveLead(lead);
    
    // Clear unread flag for this lead
    setUnreadLeads(prev => {
      const updated = { ...prev };
      delete updated[lead.id];
      
      // Update global bubble notification badge if no other unread chats exist
      const remainingUnreads = Object.keys(updated).length;
      if (remainingUnreads === 0) {
        setHasNewUpdate(false);
      }
      
      return updated;
    });

    fetchConversation(lead.id);
  };

  const handleBackToList = () => {
    setActiveLeadId(null);
    setActiveLead(null);
    setMessages([]);
    fetchLeads(true);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !activeLeadId || !activeLead) return;

    setSendingMessage(true);
    const payload = {
      lead_id: activeLeadId,
      phone: activeLead.whatsapp || '',
      message: replyText
    };

    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/messages/send`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const newMsg = await res.json();
        setMessages(prev => [...prev, newMsg]);
        setReplyText('');
        
        // Instantly move this lead to the top of the list
        setLeads(prevLeads => {
          const updated = prevLeads.map(l => {
            if (String(l.id) === String(activeLeadId)) {
              return { ...l, last_interaction: new Date().toISOString() };
            }
            return l;
          });
          return sortLeadsByInteraction(updated);
        });

        // Silently update leads list in background
        fetchLeads(true);
      } else {
        throw new Error('Falha ao enviar mensagem');
      }
    } catch (err) {
      alert('Erro ao enviar mensagem pelo popup.');
    } finally {
      setSendingMessage(false);
    }
  };

  const filteredLeads = leads.filter(lead => 
    lead.status?.toLowerCase() !== 'prospectado' &&
    lead.company_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  // Check if token exists, hide widget if logged out
  const token = localStorage.getItem("admin_token");
  if (!token || token === "null" || token === "undefined") {
    return null;
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans flex flex-col items-end">
      {/* Expanded Chat Drawer */}
      {isOpen && (
        <div className="w-80 sm:w-96 h-[500px] bg-white/95 backdrop-blur-md border border-violet-100 shadow-2xl rounded-2xl flex flex-col mb-4 transition-all duration-300 animate-in fade-in slide-in-from-bottom-5">
          {/* Header */}
          <div className="p-4 border-b border-violet-100 bg-gradient-to-r from-purple-700 to-indigo-700 text-white rounded-t-2xl flex items-center justify-between shadow-sm">
            {activeLeadId ? (
              <div className="flex items-center gap-2">
                <button 
                  onClick={handleBackToList}
                  className="p-1.5 hover:bg-white/10 rounded-lg transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <div>
                  <h3 className="text-xs font-bold truncate max-w-[180px]">{activeLead?.company_name}</h3>
                  <p className="text-[9px] text-purple-200 mt-0.5 font-medium uppercase tracking-wide">{activeLead?.origin}</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <MessageCircle className="w-4 h-4 text-emerald-400" />
                <div>
                  <h3 className="text-xs font-bold">Conversas Dominuslabs</h3>
                  <p className="text-[9px] text-purple-200 mt-0.5">Central de Chats da Esteira</p>
                </div>
              </div>
            )}
            
            <button 
              onClick={() => setIsOpen(false)}
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 flex flex-col min-h-0 bg-slate-50/50">
            {activeLeadId ? (
              /* Screen 2: Conversation View */
              <div className="flex-1 flex flex-col min-h-0">
                {/* Messages list */}
                <div className="flex-grow overflow-y-auto p-4 space-y-3">
                  {loadingMessages ? (
                    <div className="h-full flex items-center justify-center">
                      <Loader2 className="w-5 h-5 text-purple-600 animate-spin" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400 text-[10px] font-semibold gap-1">
                      <MessageSquare className="w-6 h-6 opacity-30" />
                      <p>Nenhuma mensagem.</p>
                    </div>
                  ) : (
                    messages.map((msg, i) => {
                      const isUser = msg.sender === 'user';
                      return (
                        <div 
                          key={msg.id || i}
                          className={`max-w-[85%] rounded-xl p-2.5 text-[11px] leading-normal ${
                            isUser 
                              ? 'bg-purple-600 text-white self-end rounded-tr-none ml-auto' 
                              : 'bg-white text-slate-800 border border-slate-100 self-start mr-auto rounded-tl-none shadow-sm'
                          }`}
                        >
                          <p className="whitespace-pre-wrap break-words">{msg.message}</p>
                          <div className={`text-[8px] mt-1 text-right ${isUser ? 'text-purple-200' : 'text-slate-400'}`}>
                            {formatDate(msg.timestamp)}
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input form */}
                <form onSubmit={handleSendMessage} className="p-3 border-t border-violet-100 bg-white flex gap-1.5 items-center">
                  <input
                    type="text"
                    placeholder="Responda por aqui..."
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    disabled={sendingMessage}
                    className="flex-grow px-3 py-2 text-xs rounded-xl border border-violet-100 focus:border-purple-500 outline-none"
                  />
                  <button
                    type="submit"
                    disabled={sendingMessage || !replyText.trim()}
                    className="p-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-all cursor-pointer flex-shrink-0"
                  >
                    {sendingMessage ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                  </button>
                </form>
              </div>
            ) : (
              /* Screen 1: Leads/Contacts List */
              <div className="flex-1 flex flex-col min-h-0">
                {/* Search Bar */}
                <div className="p-3 bg-white border-b border-violet-100 flex items-center gap-2">
                  <Search className="w-3.5 h-3.5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Buscar empresa..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-transparent border-none outline-none text-xs font-semibold placeholder:text-slate-400"
                  />
                </div>

                {/* List */}
                <div className="flex-grow overflow-y-auto p-2 space-y-1">
                  {loadingLeads ? (
                    <div className="h-full flex items-center justify-center">
                      <Loader2 className="w-5 h-5 text-purple-600 animate-spin" />
                    </div>
                  ) : filteredLeads.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 text-xs font-bold">
                      Nenhum lead encontrado.
                    </div>
                  ) : (
                    filteredLeads.map((lead) => {
                      const isUnread = !!unreadLeads[lead.id];
                      return (
                        <div
                          key={lead.id}
                          onClick={() => handleOpenLeadChat(lead)}
                          className={`flex items-center justify-between p-2.5 rounded-xl transition-all cursor-pointer ${
                            isUnread 
                              ? 'bg-purple-50/70 border border-purple-100 hover:bg-purple-50' 
                              : 'bg-white hover:bg-violet-50/50 border border-slate-100/50'
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            {/* Channel Indicator icon */}
                            <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                              lead.origin === 'Instagram' ? 'bg-pink-500' : 'bg-emerald-500'
                            }`} title={lead.origin} />
                            
                            <div className="min-w-0">
                              <h4 className={`text-xs truncate max-w-[160px] ${isUnread ? 'font-extrabold text-slate-900' : 'font-semibold text-slate-700'}`}>
                                {lead.company_name}
                              </h4>
                              <p className="text-[9px] text-slate-400 font-medium truncate">
                                Status: {lead.status}
                              </p>
                            </div>
                          </div>

                          <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            <span className="text-[8px] text-slate-400 font-medium">
                              {formatDate(lead.last_interaction)}
                            </span>
                            {isUnread && (
                              <span className="w-2.5 h-2.5 bg-purple-600 rounded-full animate-pulse" />
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Toggle Bubble */}
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          // Refetch leads to have latest lists when opening
          if (!isOpen) {
            fetchLeads();
          }
        }}
        className="w-14 h-14 bg-gradient-to-tr from-purple-700 to-indigo-600 hover:from-purple-800 hover:to-indigo-700 text-white rounded-full flex items-center justify-center shadow-2xl hover:scale-105 active:scale-95 transition-all cursor-pointer relative"
      >
        <MessageSquare className="w-6 h-6" />
        {hasNewUpdate && (
          <span className="absolute top-0 right-0 w-3.5 h-3.5 bg-rose-500 border-2 border-white rounded-full animate-pulse" />
        )}
      </button>
    </div>
  );
}
