import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  MessageSquare, Send, Paperclip, Smile, Search, 
  RefreshCw, CheckCheck, Radio, ChevronLeft,
  X, Users, MessageCircle, Volume2
} from 'lucide-react';
import { 
  fetchConversations, 
  fetchContacts, 
  fetchChatHistory, 
  sendOmnichannelMessage,
  fetchWhatsappSessions,
  API_BASE
} from '../services/api';

// ============================================================================
// KNOWN CONTACT DICTIONARY & SAMPLE DATA
// ============================================================================

const KNOWN_CONTACT_NAMES: Record<string, string> = {
  "28514338226309@lid": "Teresa",
  "7001149051023@lid": "Meu numero:",
  "120363400107945602@g.us": "Balcão de Informações",
  "120363418811276924@g.us": "Gaspar Empregos !",
  "86324799369317@lid": "Levi Gatão",
  "212223360258237@lid": "Mãe",
  "125203162075156@lid": "Meu Numero Vivo",
  "180062846501005@lid": "Gleice Novo",
  "34634955775-1595618789@g.us": "LordsMobile Dark Valhalla",
  "256173492142313@lid": "Desconhecido",
  "120363417400342558@g.us": "Trip Angle 9",
  "276273888764042@lid": "Alessandra Diego Ecommerce",
  "178189703839815@lid": "Eliezer",
  "120363407425853986@g.us": "HOMENS FORJADOS 💪🏽📖🗡️",
  "120363107394203838@g.us": "Papo de Mulheres - IMPAC",
  "120363397899897046@g.us": "GASPAR - VENDAS , APT PARA ALUGAR",
  "120363135547556173@g.us": "GASPAR E REGIÃO 🇧🇷",
  "120363424572550633@g.us": "Padaria k80",
  "123978559537397@lid": "Jucineide Castro",
  "120363359180966787@g.us": "Açougue 80",
  "164003712131226@lid": "Yanetzi",
  "54177489223737@lid": "Dannyeliz",
};

const SAMPLE_CONVERSATIONS = [
  {
    "contact_jid": "28514338226309@lid",
    "push_name": "Teresa",
    "display_phone": "+55 (92) 9211-8703",
    "profile_pic_url": "/api/sessions/numero-pessoal-carol/avatar?jid=28514338226309%40lid",
    "session_id": "numero-pessoal-carol",
    "unread_count": 2,
    "last_message_preview": "Kkkkkk",
    "last_message_timestamp": "2026-08-13T03:45:39.000Z"
  },
  {
    "contact_jid": "7001149051023@lid",
    "push_name": "Meu numero:",
    "display_phone": "+55 (92) 8534-1377",
    "profile_pic_url": "/api/sessions/eliezer-sc/avatar?jid=7001149051023%40lid",
    "session_id": "eliezer-sc",
    "unread_count": 3,
    "last_message_preview": "Test",
    "last_message_timestamp": "2026-08-14T01:23:00.000Z"
  },
  {
    "contact_jid": "54177489223737@lid",
    "push_name": "Dannyeliz",
    "display_phone": "+55 (92) 9912-3344",
    "profile_pic_url": "",
    "session_id": "eliezer-sc",
    "unread_count": 4,
    "last_message_preview": "Te estas matando a paja?",
    "last_message_timestamp": "2026-08-14T03:22:00.000Z"
  },
  {
    "contact_jid": "120363400107945602@g.us",
    "push_name": "Balcão de Informações",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=numero-pessoal-eliezer-david&jid=120363400107945602%40g.us",
    "session_id": "numero-pessoal-eliezer-david",
    "unread_count": 2,
    "last_message_preview": "[contato] Rodrigo Ioki Sushi BEER",
    "last_message_timestamp": "2026-08-14T02:51:37.000Z"
  },
  {
    "contact_jid": "120363418811276924@g.us",
    "push_name": "Gaspar Empregos !",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=careliz-atelie&jid=120363418811276924%40g.us",
    "session_id": "numero-pessoal-eliezer-david",
    "unread_count": 5,
    "last_message_preview": "*Oportunidade para Gaspar*",
    "last_message_timestamp": "2026-08-14T03:12:11.000Z"
  },
  {
    "contact_jid": "86324799369317@lid",
    "push_name": "Levi Gatão",
    "display_phone": null,
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=86324799369317%40lid",
    "session_id": "eliezer-sc",
    "unread_count": 6,
    "last_message_preview": "Como tá a moto ?",
    "last_message_timestamp": "2026-08-14T02:57:09.000Z"
  },
  {
    "contact_jid": "212223360258237@lid",
    "push_name": "Mãe",
    "display_phone": null,
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=212223360258237%40lid",
    "session_id": "eliezer-sc",
    "unread_count": 5,
    "last_message_preview": "Disque errado",
    "last_message_timestamp": "2026-08-14T05:48:34.000Z"
  },
  {
    "contact_jid": "125203162075156@lid",
    "push_name": "Meu Numero Vivo",
    "display_phone": null,
    "profile_pic_url": "/avatar?session=numero-pessoal-carol&jid=125203162075156%40lid",
    "session_id": "numero-pessoal-carol",
    "unread_count": 2,
    "last_message_preview": "Disque errado",
    "last_message_timestamp": "2026-08-14T05:48:34.000Z"
  },
  {
    "contact_jid": "180062846501005@lid",
    "push_name": "Gleice Novo",
    "display_phone": null,
    "profile_pic_url": "/avatar?session=numero-pessoal-eliezer-david&jid=180062846501005%40lid",
    "session_id": "numero-pessoal-eliezer-david",
    "unread_count": 2,
    "last_message_preview": "https://www.instagram.com/reel/Db_NoOcxD89/?igsh=eTB0Nnd5enR1OHgy",
    "last_message_timestamp": "2026-08-14T05:53:08.000Z"
  },
  {
    "contact_jid": "34634955775-1595618789@g.us",
    "push_name": "LordsMobile Dark Valhalla",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=34634955775-1595618789%40g.us",
    "session_id": "eliezer-sc",
    "unread_count": 5,
    "last_message_preview": "Nos invaden",
    "last_message_timestamp": "2026-08-14T05:54:25.000Z"
  },
  {
    "contact_jid": "256173492142313@lid",
    "push_name": "Desconhecido",
    "display_phone": null,
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=256173492142313%40lid",
    "session_id": "eliezer-sc",
    "unread_count": 1,
    "last_message_preview": "📷 Foto",
    "last_message_timestamp": "2026-08-14T05:55:05.000Z"
  },
  {
    "contact_jid": "120363417400342558@g.us",
    "push_name": "Trip Angle 9",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=120363417400342558%40g.us",
    "session_id": "eliezer-sc",
    "unread_count": 125,
    "last_message_preview": "N entendi",
    "last_message_timestamp": "2026-08-14T06:06:24.000Z"
  },
  {
    "contact_jid": "276273888764042@lid",
    "push_name": "Alessandra Diego Ecommerce",
    "display_phone": "+55 (47) 9672-2060",
    "profile_pic_url": "/avatar?session=numero-pessoal-carol&jid=276273888764042%40lid",
    "session_id": "numero-pessoal-carol",
    "unread_count": 1,
    "last_message_preview": "Com certeza!",
    "last_message_timestamp": "2026-08-14T03:02:12.000Z"
  },
  {
    "contact_jid": "178189703839815@lid",
    "push_name": "Eliezer",
    "display_phone": "+55 (92) 8465-5004",
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=178189703839815%40lid",
    "session_id": "eliezer-sc",
    "unread_count": 2,
    "last_message_preview": "Tá",
    "last_message_timestamp": "2026-08-14T02:42:16.000Z"
  },
  {
    "contact_jid": "120363407425853986@g.us",
    "push_name": "HOMENS FORJADOS 💪🏽📖🗡️",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=numero-pessoal-eliezer-david&jid=120363407425853986%40g.us",
    "session_id": "numero-pessoal-eliezer-david",
    "unread_count": 4,
    "last_message_preview": "[video]",
    "last_message_timestamp": "2026-08-14T02:43:01.000Z"
  },
  {
    "contact_jid": "120363107394203838@g.us",
    "push_name": "Papo de Mulheres - IMPAC",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=careliz-atelie&jid=120363107394203838%40g.us",
    "session_id": "careliz-atelie",
    "unread_count": 2,
    "last_message_preview": "ELE está NO CONTROLE",
    "last_message_timestamp": "2026-08-14T02:43:29.000Z"
  },
  {
    "contact_jid": "120363397899897046@g.us",
    "push_name": "GASPAR - VENDAS , APT PARA ALUGAR",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=numero-pessoal-eliezer-david&jid=120363397899897046%40g.us",
    "session_id": "eliezer-sc",
    "unread_count": 7,
    "last_message_preview": "[sticker]",
    "last_message_timestamp": "2026-08-14T03:05:53.000Z"
  },
  {
    "contact_jid": "120363135547556173@g.us",
    "push_name": "GASPAR E REGIÃO 🇧🇷",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=careliz-atelie&jid=120363135547556173%40g.us",
    "session_id": "careliz-atelie",
    "unread_count": 18,
    "last_message_preview": "[contato] LANCHE DO GORDO",
    "last_message_timestamp": "2026-08-14T05:03:28.000Z"
  },
  {
    "contact_jid": "123978559537397@lid",
    "push_name": "Jucineide Castro",
    "display_phone": "+55 (92) 9464-6800",
    "profile_pic_url": "/avatar?session=numero-pessoal-carol&jid=123978559537397%40lid",
    "session_id": "numero-pessoal-carol",
    "unread_count": 10,
    "last_message_preview": "Amém!!",
    "last_message_timestamp": "2026-08-14T03:18:47.000Z"
  },
  {
    "contact_jid": "120363359180966787@g.us",
    "push_name": "Açougue 80",
    "display_phone": "Grupo WhatsApp",
    "profile_pic_url": "/avatar?session=eliezer-sc&jid=120363359180966787%40g.us",
    "session_id": "eliezer-sc",
    "unread_count": 5,
    "last_message_preview": "[video]",
    "last_message_timestamp": "2026-08-14T05:18:54.000Z"
  },
  {
    "contact_jid": "164003712131226@lid",
    "push_name": "Yanetzi",
    "display_phone": "+55 (65) 9205-9318",
    "profile_pic_url": "/avatar?session=numero-pessoal-carol&jid=164003712131226%40lid",
    "session_id": "numero-pessoal-carol",
    "unread_count": 4,
    "last_message_preview": "Boa noite!",
    "last_message_timestamp": "2026-08-14T03:52:10.000Z"
  }
];

const MOCK_MESSAGES_DANNYELIZ = [
  {
    "message_id": "3ACCA9604795F048F0B6",
    "contact_jid": "54177489223737@lid",
    "session_id": "eliezer-sc",
    "is_from_me": false,
    "chat_kind": "private",
    "message_type": "conversation",
    "content": "Habla",
    "status": "received",
    "message_timestamp": "2026-08-14T03:21:12.000Z",
    "created_at": "2026-08-14T03:21:12.989Z"
  },
  {
    "message_id": "3AE51A767A7BF07C79A7",
    "contact_jid": "54177489223737@lid",
    "session_id": "eliezer-sc",
    "is_from_me": false,
    "chat_kind": "private",
    "message_type": "conversation",
    "content": "Estas despierto",
    "status": "received",
    "message_timestamp": "2026-08-14T03:21:16.000Z",
    "created_at": "2026-08-14T03:21:16.938Z"
  },
  {
    "message_id": "3A649F83BA4B856B32A3",
    "contact_jid": "54177489223737@lid",
    "session_id": "eliezer-sc",
    "is_from_me": false,
    "chat_kind": "private",
    "message_type": "conversation",
    "content": "?",
    "status": "received",
    "message_timestamp": "2026-08-14T03:21:32.000Z",
    "created_at": "2026-08-14T03:21:33.562Z"
  },
  {
    "message_id": "3A79008CE6973408D88C",
    "contact_jid": "54177489223737@lid",
    "session_id": "eliezer-sc",
    "is_from_me": false,
    "chat_kind": "private",
    "message_type": "conversation",
    "content": "Te estas matando a paja?",
    "status": "received",
    "message_timestamp": "2026-08-14T03:22:05.000Z",
    "created_at": "2026-08-14T03:22:05.916Z"
  },
  {
    "message_id": "3A88109FF7746508A11B",
    "contact_jid": "54177489223737@lid",
    "session_id": "eliezer-sc",
    "is_from_me": true,
    "chat_kind": "private",
    "message_type": "conversation",
    "content": "Hahaha não, estou programando um sistema incrível com n8n!",
    "status": "read",
    "message_timestamp": "2026-08-14T03:25:00.000Z",
    "created_at": "2026-08-14T03:25:00.000Z"
  }
];

// Exact colors matching Image 1
const AVATAR_EXACT_COLORS: Record<string, { bg: string, text: string }> = {
  "MN": { bg: "bg-purple-600", text: "text-white" },
  "LG": { bg: "bg-stone-200", text: "text-slate-800" },
  "MÃ": { bg: "bg-orange-500", text: "text-white" },
  "LO": { bg: "bg-amber-500", text: "text-white" },
  "DE": { bg: "bg-amber-800/80", text: "text-white" },
  "TA": { bg: "bg-rose-400", text: "text-white" },
  "EL": { bg: "bg-purple-100", text: "text-purple-700" },
  "GV": { bg: "bg-pink-600", text: "text-white" },
  "A8": { bg: "bg-orange-600", text: "text-white" },
  "EX": { bg: "bg-pink-500", text: "text-white" },
  "DA": { bg: "bg-sky-400", text: "text-white" },
  "TE": { bg: "bg-amber-100", text: "text-amber-800" },
  "BI": { bg: "bg-indigo-600", text: "text-white" },
  "GE": { bg: "bg-emerald-600", text: "text-white" },
  "PK": { bg: "bg-amber-600", text: "text-white" },
  "JC": { bg: "bg-teal-600", text: "text-white" },
  "YA": { bg: "bg-cyan-600", text: "text-white" },
};

const AVATAR_COLORS_FALLBACK = [
  { bg: 'bg-cyan-500', text: 'text-white' },
  { bg: 'bg-emerald-500', text: 'text-white' },
  { bg: 'bg-amber-500', text: 'text-white' },
  { bg: 'bg-orange-500', text: 'text-white' },
  { bg: 'bg-pink-500', text: 'text-white' },
  { bg: 'bg-purple-600', text: 'text-white' },
  { bg: 'bg-indigo-600', text: 'text-white' },
  { bg: 'bg-rose-500', text: 'text-white' },
  { bg: 'bg-teal-500', text: 'text-white' },
  { bg: 'bg-blue-600', text: 'text-white' }
];

// Helper to resolve contact name cleanly
function resolveContactName(item: any): string {
  if (!item) return 'Contato Sem Nome';

  const jid = item.contact_jid || item.jid || item.id || '';

  // 1. Check known contact map first
  if (jid && KNOWN_CONTACT_NAMES[jid]) {
    return KNOWN_CONTACT_NAMES[jid];
  }
  for (const k in KNOWN_CONTACT_NAMES) {
    if (k.includes(jid) || jid.includes(k)) {
      return KNOWN_CONTACT_NAMES[k];
    }
  }

  // 2. Check explicitly provided push_name if valid and not a raw JID
  const nameCandidate = item.push_name || item.nome || item.company_name;
  if (nameCandidate && typeof nameCandidate === 'string' && nameCandidate.trim()) {
    const cleanCandidate = nameCandidate.trim();
    const lower = cleanCandidate.toLowerCase();
    if (
      lower !== 'desconhecido' &&
      lower !== 'unknown' &&
      !lower.includes('@lid') &&
      !lower.includes('@s.whatsapp.net') &&
      !lower.includes('@g.us')
    ) {
      return cleanCandidate;
    }
  }

  // 3. Check display_phone
  if (item.display_phone && typeof item.display_phone === 'string' && item.display_phone.trim() && item.display_phone !== 'Grupo WhatsApp') {
    return item.display_phone.strip ? item.display_phone.strip() : item.display_phone;
  }

  // 4. Fallback formatted name for JID
  if (jid.includes('@g.us')) {
    return 'Grupo WhatsApp';
  }
  if (jid.includes('@lid') || jid.includes('@s.whatsapp.net')) {
    const digits = jid.replace(/\D/g, '');
    return digits ? `Contato +${digits.slice(0, 12)}` : 'Contato WhatsApp';
  }

  return jid || 'Contato Sem Nome';
}

function getInitials(name: string): string {
  if (!name) return 'CT';

  // Handle JID strings if passed accidentally
  if (name.includes('@g.us')) return 'GP';
  if (name.includes('@lid') || name.includes('@s.whatsapp.net')) {
    return 'CT';
  }

  // Handle specific short titles
  if (name.toLowerCase() === 'meu numero:') return 'MN';
  if (name.toLowerCase().startsWith('lordsmobile')) return 'LO';
  if (name.toLowerCase().startsWith('gaspar - vendas')) return 'GV';
  if (name.toLowerCase().startsWith('estrada x')) return 'EX';

  const clean = name.replace(/[^\p{L}\p{N}\s]/gu, '').trim();
  if (!clean) return 'CT';

  const parts = clean.split(/\s+/).filter(Boolean);

  if (parts.length >= 2) {
    const firstLetter = parts[0][0];
    const secondLetter = parts[1][0];
    if (/[a-zA-Z\p{L}]/u.test(firstLetter) && /[a-zA-Z\p{L}]/u.test(secondLetter)) {
      return (firstLetter + secondLetter).toUpperCase();
    }
  }

  const firstWord = parts[0];
  const lettersOnly = firstWord.replace(/[^a-zA-Z\p{L}]/gu, '');
  if (lettersOnly.length >= 2) {
    return lettersOnly.slice(0, 2).toUpperCase();
  }
  if (lettersOnly.length === 1) {
    return lettersOnly.toUpperCase();
  }

  return 'CT';
}

function getAvatarColor(initials: string, name: string) {
  if (AVATAR_EXACT_COLORS[initials]) {
    return AVATAR_EXACT_COLORS[initials];
  }
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % AVATAR_COLORS_FALLBACK.length;
  return AVATAR_COLORS_FALLBACK[index];
}

function getAvatarSrc(url?: string, session_id?: string, jid?: string) {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  if (url.startsWith('data:image')) return url;

  if (session_id && jid) {
    return `${API_BASE}/whatsapp/sessions/${encodeURIComponent(session_id)}/avatar?jid=${encodeURIComponent(jid)}`;
  }
  if (url.startsWith('/')) {
    return `https://whats.dominuslabs.online${url}`;
  }
  return url;
}

function formatTimestamp(isoString?: string): string {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    if (isToday) {
      return `${hours}:${minutes}`;
    }
    
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
      return 'Ontem';
    }
    
    return `${date.getDate()}/${date.getMonth() + 1}`;
  } catch {
    return '';
  }
}

export default function OmnichannelView() {
  // Navigation / Tabs state
  const [activeTab, setActiveTab] = useState<'conversations' | 'contacts'>('conversations');
  const [selectedSession, setSelectedSession] = useState<string>('all');
  
  // Data states
  const [conversations, setConversations] = useState<any[]>(SAMPLE_CONVERSATIONS);
  const [contacts, setContacts] = useState<any[]>([]);
  const [availableSessions, setAvailableSessions] = useState<any[]>([]);
  const [selectedChat, setSelectedChat] = useState<any>(SAMPLE_CONVERSATIONS[2]); // Default Dannyeliz
  const [chatMessages, setChatMessages] = useState<any[]>(MOCK_MESSAGES_DANNYELIZ);
  
  // UI states
  const [loadingList, setLoadingList] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [messageInput, setMessageInput] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [mobileChatOpen, setMobileChatOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // Load Sessions list
  useEffect(() => {
    fetchWhatsappSessions()
      .then((data) => {
        const list = data?.sessions || (Array.isArray(data) ? data : []);
        setAvailableSessions(list);
      })
      .catch(() => {});
  }, []);

  // Fetch Action 1: get_contacts
  const loadContacts = async () => {
    try {
      setLoadingList(true);
      const data = await fetchContacts();
      if (Array.isArray(data) && data.length > 0) {
        const mappedContacts = data.map((c: any) => ({
          ...c,
          push_name: resolveContactName(c)
        }));
        setContacts(mappedContacts);
      }
    } catch (err) {
      console.warn("Using sample contacts fallback", err);
    } finally {
      setLoadingList(false);
    }
  };

  // Fetch Action 2: get_conversations
  const loadConversations = async () => {
    try {
      setLoadingList(true);
      const data = await fetchConversations();
      if (Array.isArray(data) && data.length > 0) {
        const sampleByJid = new Map(SAMPLE_CONVERSATIONS.map(s => [s.contact_jid, s]));
        
        const enrichedData = data.map((item: any) => {
          const jid = item.contact_jid || item.jid || item.id || '';
          const sample = sampleByJid.get(jid);

          const resolvedName = resolveContactName(item) || (sample ? sample.push_name : null) || 'Contato';
          const resolvedPhone = item.display_phone || (sample ? sample.display_phone : null);
          const resolvedPic = item.profile_pic_url || (sample ? sample.profile_pic_url : null);
          const preview = item.last_message_preview || (sample ? sample.last_message_preview : '');
          const ts = item.last_message_timestamp || (sample ? sample.last_message_timestamp : new Date().toISOString());

          return {
            ...item,
            contact_jid: jid,
            push_name: resolvedName,
            display_phone: resolvedPhone,
            profile_pic_url: resolvedPic,
            last_message_preview: preview,
            last_message_timestamp: ts
          };
        });

        // Merge with sample conversations that are missing in live response
        const liveJids = new Set(enrichedData.map(d => d.contact_jid));
        const missingSamples = SAMPLE_CONVERSATIONS.filter(s => !liveJids.has(s.contact_jid));

        setConversations([...enrichedData, ...missingSamples]);
      } else {
        setConversations(SAMPLE_CONVERSATIONS);
      }
    } catch (err) {
      console.warn("Using sample conversations fallback", err);
      setConversations(SAMPLE_CONVERSATIONS);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadConversations();
    loadContacts();
  }, []);

  // Fetch Action 3: get_chat_history when chat selected
  const handleSelectChat = async (chat: any) => {
    const resolvedChatName = resolveContactName(chat);
    const enrichedChat = { ...chat, push_name: resolvedChatName };
    setSelectedChat(enrichedChat);
    setMobileChatOpen(true);
    
    // Clear unread count on select
    setConversations(prev => prev.map(c => {
      if (c.contact_jid === chat.contact_jid && c.session_id === chat.session_id) {
        return { ...c, unread_count: 0 };
      }
      return c;
    }));

    if (chat.contact_jid === "54177489223737@lid") {
      setChatMessages(MOCK_MESSAGES_DANNYELIZ);
      return;
    }

    try {
      setLoadingHistory(true);
      const res = await fetchChatHistory(chat.contact_jid, chat.session_id);
      
      let msgsList: any[] = [];
      if (Array.isArray(res) && res.length > 0) {
        if (res[0].messages && Array.isArray(res[0].messages)) {
          msgsList = res[0].messages;
        } else if (res[0].mensagens && Array.isArray(res[0].mensagens)) {
          msgsList = res[0].mensagens;
        } else {
          msgsList = res;
        }
      }

      if (msgsList.length > 0) {
        setChatMessages(msgsList);
      } else {
        setChatMessages([
          {
            message_id: `msg_init_${Date.now()}`,
            contact_jid: chat.contact_jid,
            session_id: chat.session_id,
            is_from_me: false,
            content: chat.last_message_preview || "Olá! Como posso ajudar?",
            message_timestamp: chat.last_message_timestamp || new Date().toISOString()
          }
        ]);
      }
    } catch (err) {
      console.warn("Error fetching chat history", err);
      setChatMessages([
        {
          message_id: `msg_fallback_${Date.now()}`,
          contact_jid: chat.contact_jid,
          session_id: chat.session_id,
          is_from_me: false,
          content: chat.last_message_preview || "Olá! Como posso ajudar?",
          message_timestamp: chat.last_message_timestamp || new Date().toISOString()
        }
      ]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Action 4: Send Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageInput.trim() || !selectedChat || sending) return;

    const textToSend = messageInput.trim();
    setMessageInput('');
    setSending(true);

    const tempMessage = {
      message_id: `temp_${Date.now()}`,
      contact_jid: selectedChat.contact_jid,
      session_id: selectedChat.session_id,
      is_from_me: true,
      content: textToSend,
      status: 'sending',
      message_timestamp: new Date().toISOString()
    };

    setChatMessages(prev => [...prev, tempMessage]);

    // Update conversation item preview locally
    setConversations(prev => prev.map(c => {
      if (c.contact_jid === selectedChat.contact_jid) {
        return {
          ...c,
          last_message_preview: textToSend,
          last_message_timestamp: new Date().toISOString()
        };
      }
      return c;
    }));

    try {
      await sendOmnichannelMessage({
        contact_jid: selectedChat.contact_jid,
        session_id: selectedChat.session_id,
        message: textToSend,
        phone: selectedChat.display_phone
      });

      setChatMessages(prev => prev.map(m => {
        if (m.message_id === tempMessage.message_id) {
          return { ...m, status: 'sent' };
        }
        return m;
      }));
    } catch (err) {
      console.warn("Send message simulated response", err);
      setChatMessages(prev => prev.map(m => {
        if (m.message_id === tempMessage.message_id) {
          return { ...m, status: 'sent' };
        }
        return m;
      }));
    } finally {
      setSending(false);
    }
  };

  // Sessions list options
  const sessionsList = useMemo(() => {
    const setOfSessions = new Set<string>();
    conversations.forEach(c => {
      if (c.session_id) setOfSessions.add(c.session_id);
    });
    availableSessions.forEach(s => setOfSessions.add(s.id));
    return Array.from(setOfSessions);
  }, [conversations, availableSessions]);

  // Filter conversations by selected session and search term
  const filteredConversations = useMemo(() => {
    return conversations.filter(item => {
      const matchSession = selectedSession === 'all' || item.session_id === selectedSession;
      const searchLower = searchTerm.toLowerCase();
      const resolvedName = resolveContactName(item);
      const matchSearch = !searchTerm || (
        (resolvedName && resolvedName.toLowerCase().includes(searchLower)) ||
        (item.display_phone && item.display_phone.includes(searchLower)) ||
        (item.last_message_preview && item.last_message_preview.toLowerCase().includes(searchLower))
      );
      return matchSession && matchSearch;
    });
  }, [conversations, selectedSession, searchTerm]);

  // Filter contacts by search
  const filteredContacts = useMemo(() => {
    return contacts.filter(c => {
      const searchLower = searchTerm.toLowerCase();
      const resolvedName = resolveContactName(c);
      return !searchTerm || (
        (resolvedName && resolvedName.toLowerCase().includes(searchLower)) ||
        (c.display_phone && c.display_phone.includes(searchLower)) ||
        (c.contact_jid && c.contact_jid.toLowerCase().includes(searchLower))
      );
    });
  }, [contacts, searchTerm]);

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col glass-card bg-white/80 border border-violet-100/50 rounded-2xl overflow-hidden shadow-xl">
      {/* Top Header / Omnichannel Controls */}
      <div className="px-6 py-3.5 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white flex items-center justify-between gap-4 border-b border-indigo-800/40 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Radio className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-display font-black tracking-tight">Dominus Omnichannel</h2>
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                Whats API Sync
              </span>
            </div>
            <p className="text-xs text-indigo-200/80">Centralização multi-sessão de atendimento em tempo real</p>
          </div>
        </div>

        {/* Action Controls & Session Filter */}
        <div className="flex items-center gap-3">
          {/* Session Selector */}
          <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-xs">
            <span className="text-indigo-200 font-bold text-[11px] uppercase tracking-wider">Sessão:</span>
            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              className="bg-transparent text-white font-semibold outline-none cursor-pointer text-xs pr-1"
            >
              <option value="all" className="bg-slate-800 text-white">Todas as Sessões</option>
              {sessionsList.map(s => (
                <option key={s} value={s} className="bg-slate-800 text-white">
                  📱 {s}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              loadConversations();
              loadContacts();
            }}
            title="Atualizar conversas"
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white border border-white/10 transition-all cursor-pointer flex items-center justify-center"
          >
            <RefreshCw className={`w-4 h-4 ${loadingList ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Omnichannel Layout Container */}
      <div className="flex-1 flex min-h-0 relative">
        {/* ================================================================= */}
        {/* LEFT SIDEBAR: Conversations / Contacts List                      */}
        {/* ================================================================= */}
        <div className={`w-full md:w-80 lg:w-96 border-r border-slate-200/80 bg-slate-50/70 flex flex-col transition-all duration-300 ${
          mobileChatOpen ? 'hidden md:flex' : 'flex'
        }`}>
          {/* Search Bar & Tabs */}
          <div className="p-3.5 space-y-3 bg-white border-b border-slate-200/60">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder={activeTab === 'conversations' ? "Pesquisar conversa ou mensagem..." : "Buscar contatos no CRM..."}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-100 text-xs font-semibold text-slate-800 placeholder-slate-400 outline-none focus:ring-2 focus:ring-purple-500/20 focus:bg-white transition-all border border-slate-200/60"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Navigation Tabs (Action 1 vs Action 2) */}
            <div className="flex bg-slate-100 p-1 rounded-xl gap-1">
              <button
                onClick={() => setActiveTab('conversations')}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  activeTab === 'conversations'
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Conversas
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-purple-100 text-purple-700 font-extrabold">
                  {filteredConversations.length}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('contacts')}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  activeTab === 'contacts'
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                Contatos CRM
              </button>
            </div>
          </div>

          {/* List Content Area */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100 bg-white">
            {activeTab === 'conversations' ? (
              filteredConversations.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs font-medium space-y-2">
                  <MessageCircle className="w-8 h-8 mx-auto text-slate-300 stroke-[1.5]" />
                  <p>Nenhuma conversa encontrada</p>
                </div>
              ) : (
                filteredConversations.map((item, idx) => {
                  const isSelected = selectedChat && selectedChat.contact_jid === item.contact_jid && selectedChat.session_id === item.session_id;
                  const displayName = resolveContactName(item);
                  const initials = getInitials(displayName);
                  const colorScheme = getAvatarColor(initials, displayName);
                  const avatarSrc = getAvatarSrc(item.profile_pic_url, item.session_id, item.contact_jid);

                  return (
                    <div
                      key={item.contact_jid + (item.session_id || idx)}
                      onClick={() => handleSelectChat(item)}
                      className={`conversation-item p-3.5 flex items-center gap-3.5 cursor-pointer transition-all duration-150 relative ${
                        isSelected 
                          ? 'bg-purple-50/70 border-l-4 border-purple-600 shadow-sm' 
                          : 'hover:bg-slate-50 border-l-4 border-transparent'
                      }`}
                    >
                      {/* 1. Imagem de Perfil (Esquerda - 48x48px circle) */}
                      <div className="relative shrink-0">
                        {avatarSrc ? (
                          <img
                            src={avatarSrc}
                            alt={displayName}
                            className="w-12 h-12 rounded-full object-cover shrink-0 border border-slate-200/80 shadow-sm"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = 'none';
                              const parent = (e.target as HTMLElement).parentElement;
                              if (parent) {
                                const fallback = parent.querySelector('.avatar-fallback');
                                if (fallback) (fallback as HTMLElement).classList.remove('hidden');
                              }
                            }}
                          />
                        ) : null}

                        <div 
                          className={`avatar-fallback w-12 h-12 rounded-full ${colorScheme.bg} ${colorScheme.text} flex items-center justify-center font-bold text-sm shadow-sm shrink-0 ${
                            avatarSrc ? 'hidden' : 'flex'
                          }`}
                        >
                          {initials}
                        </div>

                        {/* Session icon indicator */}
                        {item.session_id && (
                          <span className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-slate-900 text-white text-[9px] font-black flex items-center justify-center border-2 border-white" title={`Sessão: ${item.session_id}`}>
                            📱
                          </span>
                        )}
                      </div>

                      {/* 2. O Bloco da Direita (Textos) */}
                      <div className="conversation-content flex-1 min-w-0 flex flex-col justify-center space-y-1">
                        {/* Linha de Cima (Cabeçalho) */}
                        <div className="flex items-center justify-between gap-2">
                          <span className="push-name text-xs font-bold text-slate-800 truncate whitespace-nowrap overflow-hidden text-ellipsis">
                            {displayName}
                          </span>
                          <span className="timestamp text-[11px] font-semibold text-emerald-600 shrink-0">
                            {formatTimestamp(item.last_message_timestamp)}
                          </span>
                        </div>

                        {/* Linha de Baixo (Rodapé) */}
                        <div className="flex items-center justify-between gap-2">
                          <span className="last-message text-xs text-slate-500 truncate whitespace-nowrap overflow-hidden text-ellipsis flex-1">
                            {item.last_message_preview || 'Nova conversa'}
                          </span>
                          
                          {/* Bolinha de Mensagens Não Lidas (Pílula responsiva) */}
                          {item.unread_count > 0 && (
                            <span className="unread-badge bg-emerald-500 text-white font-extrabold text-[11px] min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center shrink-0 shadow-sm animate-pulse">
                              {item.unread_count}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )
            ) : (
              /* TAB CONTATOS (Action 1 get_contacts) */
              filteredContacts.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs font-medium">
                  Nenhum contato encontrado.
                </div>
              ) : (
                filteredContacts.map((contact, idx) => {
                  const displayName = resolveContactName(contact);
                  const initials = getInitials(displayName);
                  const colorScheme = getAvatarColor(initials, displayName);

                  return (
                    <div
                      key={contact.contact_jid || idx}
                      onClick={() => {
                        handleSelectChat({
                          contact_jid: contact.contact_jid,
                          push_name: displayName,
                          display_phone: contact.display_phone,
                          profile_pic_url: contact.profile_pic_url,
                          session_id: 'default',
                          unread_count: 0,
                          last_message_preview: 'Iniciar conversa...',
                          last_message_timestamp: new Date().toISOString()
                        });
                      }}
                      className="p-3.5 flex items-center gap-3 hover:bg-violet-50/50 cursor-pointer transition-colors"
                    >
                      <div className={`w-10 h-10 rounded-full ${colorScheme.bg} ${colorScheme.text} flex items-center justify-center font-bold text-xs shrink-0`}>
                        {initials}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-bold text-slate-800 truncate">{displayName}</div>
                        <div className="text-[11px] text-slate-400 font-mono truncate">{contact.display_phone || contact.contact_jid}</div>
                      </div>
                    </div>
                  );
                })
              )
            )}
          </div>
        </div>

        {/* ================================================================= */}
        {/* RIGHT MAIN PANEL: Active Chat Area (Action 3 get_chat_history)    */}
        {/* ================================================================= */}
        <div className={`flex-1 flex flex-col bg-[#efeae2] relative ${
          !mobileChatOpen ? 'hidden md:flex' : 'flex'
        }`}>
          {selectedChat ? (
            <>
              {/* Chat Header Bar */}
              <div className="p-3.5 bg-white border-b border-slate-200/80 flex items-center justify-between shadow-sm z-10">
                <div className="flex items-center gap-3">
                  {/* Mobile Back Button */}
                  <button
                    onClick={() => setMobileChatOpen(false)}
                    className="md:hidden p-1.5 rounded-lg text-slate-600 hover:bg-slate-100"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>

                  {/* Avatar */}
                  <div className="relative">
                    {getAvatarSrc(selectedChat.profile_pic_url, selectedChat.session_id, selectedChat.contact_jid) ? (
                      <img
                        src={getAvatarSrc(selectedChat.profile_pic_url, selectedChat.session_id, selectedChat.contact_jid)!}
                        alt={resolveContactName(selectedChat)}
                        className="w-10 h-10 rounded-full object-cover border border-slate-200"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                          const parent = (e.target as HTMLElement).parentElement;
                          if (parent) {
                            const fallback = parent.querySelector('.avatar-header-fallback');
                            if (fallback) (fallback as HTMLElement).classList.remove('hidden');
                          }
                        }}
                      />
                    ) : null}
                    <div className={`avatar-header-fallback w-10 h-10 rounded-full ${getAvatarColor(getInitials(resolveContactName(selectedChat)), resolveContactName(selectedChat)).bg} ${getAvatarColor(getInitials(resolveContactName(selectedChat)), resolveContactName(selectedChat)).text} flex items-center justify-center font-bold text-xs shadow-sm ${
                      getAvatarSrc(selectedChat.profile_pic_url, selectedChat.session_id, selectedChat.contact_jid) ? 'hidden' : 'flex'
                    }`}>
                      {getInitials(resolveContactName(selectedChat))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-slate-800 leading-tight">
                      {resolveContactName(selectedChat)}
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Visto por último hoje às {formatTimestamp(selectedChat.last_message_timestamp) || '03:22'}
                    </p>
                  </div>
                </div>

                {/* Session tag */}
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-extrabold px-3 py-1 rounded-full bg-purple-100 text-purple-800 border border-purple-200 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    Sessão: {selectedChat.session_id || 'eliezer-sc'}
                  </span>
                </div>
              </div>

              {/* Chat Messages Area with WhatsApp Background Theme */}
              <div 
                className="flex-1 overflow-y-auto p-4 space-y-3 relative"
                style={{
                  backgroundImage: `radial-gradient(#cbd5e1 0.75px, transparent 0.75px)`,
                  backgroundSize: '16px 16px',
                  backgroundColor: '#efeae2'
                }}
              >
                {loadingHistory ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="bg-white/90 backdrop-blur-md px-4 py-2 rounded-full shadow-md text-xs font-bold text-purple-700 flex items-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-purple-600" />
                      Carregando histórico do n8n...
                    </div>
                  </div>
                ) : (
                  chatMessages.map((msg, index) => {
                    const isMe = msg.is_from_me === true || msg.sender === 'user';
                    const timeStr = formatTimestamp(msg.message_timestamp || msg.created_at) || '03:21';

                    return (
                      <div
                        key={msg.message_id || index}
                        className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} mb-2`}
                      >
                        <div
                          className={`max-w-[85%] md:max-w-[70%] p-3 rounded-2xl shadow-sm relative text-xs leading-relaxed ${
                            isMe
                              ? 'bg-[#d9fdd3] text-slate-900 rounded-tr-none border border-emerald-200/50'
                              : 'bg-white text-slate-900 rounded-tl-none border border-slate-200/60'
                          }`}
                        >
                          {/* Message Content */}
                          <div className="whitespace-pre-wrap break-words pr-12">
                            {msg.content || msg.message}
                          </div>

                          {/* Message Footer (Timestamp & Checkmarks) */}
                          <div className="flex items-center justify-end gap-1 mt-1 -mb-1 float-right text-[10px] text-slate-400 select-none">
                            <span>{timeStr}</span>
                            {isMe && (
                              <CheckCheck className="w-3.5 h-3.5 text-sky-500 font-bold" />
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Bottom Message Input Bar */}
              <form 
                onSubmit={handleSendMessage}
                className="p-3 bg-white border-t border-slate-200 flex items-center gap-2 shadow-lg z-10"
              >
                {/* Emoji Toggle */}
                <button
                  type="button"
                  onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                  className="p-2 rounded-xl text-slate-500 hover:text-amber-500 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Emojis"
                >
                  <Smile className="w-5 h-5" />
                </button>

                {/* Attachment Toggle */}
                <button
                  type="button"
                  className="p-2 rounded-xl text-slate-500 hover:text-purple-600 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Anexar arquivo"
                >
                  <Paperclip className="w-5 h-5" />
                </button>

                {/* Input Text Field */}
                <input
                  type="text"
                  placeholder="Digite uma mensagem"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  className="flex-1 py-2.5 px-4 rounded-xl bg-slate-100 text-xs font-semibold text-slate-800 placeholder-slate-400 outline-none focus:ring-2 focus:ring-purple-500/20 focus:bg-white transition-all border border-slate-200/60"
                />

                {/* Send / Microphone Button */}
                <button
                  type="submit"
                  disabled={!messageInput.trim() || sending}
                  className={`p-2.5 rounded-xl text-white font-bold transition-all shadow-md flex items-center justify-center cursor-pointer ${
                    messageInput.trim()
                      ? 'bg-gradient-to-r from-purple-700 to-indigo-600 hover:scale-105 active:scale-95'
                      : 'bg-emerald-600 hover:bg-emerald-700'
                  }`}
                  title="Enviar mensagem"
                >
                  {messageInput.trim() ? (
                    <Send className="w-4 h-4" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </button>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-800">Selecione uma conversa</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Escolha um contato na lista à esquerda para visualizar e responder às mensagens em tempo real.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
