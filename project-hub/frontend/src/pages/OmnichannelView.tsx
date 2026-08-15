import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  MessageSquare, Send, Paperclip, Smile, Search, 
  RefreshCw, CheckCheck, Radio, ChevronLeft,
  X, Users, MessageCircle, Maximize2, ExternalLink,
  Download, FileText, Image as ImageIcon, Video, Mic, Trash2,
  Play, Pause
} from 'lucide-react';
import { 
  fetchConversations, 
  fetchContacts, 
  fetchChatHistory, 
  sendOmnichannelMessage,
  sendOmnichannelMedia,
  fetchWhatsappSessions,
  API_BASE
} from '../services/api';

// ============================================================================
// KNOWN CONTACT DICTIONARY (FOR NAME RESOLUTION)
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
};

// Exact colors matching design theme
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

  if (name.includes('@g.us')) return 'GP';
  if (name.includes('@lid') || name.includes('@s.whatsapp.net')) {
    return 'CT';
  }

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

function getAvatarSrc(url?: string, session_id?: string, jid?: string): string | null {
  if (url && typeof url === 'string') {
    const trimmed = url.trim();
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('data:image')) {
      return trimmed;
    }
  }

  // Fallback to proxy if url is a relative path or if jid/session are supplied
  let targetSession = session_id || 'default';
  let targetJid = jid || '';

  if (url && typeof url === 'string') {
    const trimmed = url.trim();
    if (trimmed.includes('/avatar?') || trimmed.includes('/sessions/')) {
      try {
        const fullUrl = trimmed.startsWith('http') ? trimmed : `https://dummy.local${trimmed.startsWith('/') ? '' : '/'}${trimmed}`;
        const parsed = new URL(fullUrl);
        const qSession = parsed.searchParams.get('session') || parsed.searchParams.get('session_id');
        const qJid = parsed.searchParams.get('jid');
        
        if (qSession) targetSession = qSession;
        if (qJid) targetJid = qJid;
      } catch (e) {}
    }
  }

  if (targetJid) {
    return `/api/v1/crm/avatar?session=${encodeURIComponent(targetSession)}&jid=${encodeURIComponent(targetJid)}`;
  }

  return null;
}

function formatTimestamp(isoString?: string): string {
  if (!isoString) return '';
  try {
    let hours = '';
    let minutes = '';

    // Extract exact HH:mm directly from string if ISO format to avoid JS subtracting 3h timezone offset
    if (typeof isoString === 'string' && isoString.includes('T')) {
      const timePart = isoString.split('T')[1];
      if (timePart && timePart.includes(':')) {
        const timePieces = timePart.split(':');
        hours = timePieces[0].padStart(2, '0');
        minutes = timePieces[1].padStart(2, '0');
      }
    }

    const date = new Date(isoString);
    if (!hours || !minutes) {
      if (isNaN(date.getTime())) return '';
      hours = String(date.getHours()).padStart(2, '0');
      minutes = String(date.getMinutes()).padStart(2, '0');
    }

    const now = new Date();
    const isToday = !isNaN(date.getTime()) ? date.toDateString() === now.toDateString() : true;
    
    if (isToday) {
      return `${hours}:${minutes}`;
    }
    
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (!isNaN(date.getTime()) && date.toDateString() === yesterday.toDateString()) {
      return 'Ontem';
    }
    
    if (!isNaN(date.getTime())) {
      return `${date.getDate()}/${date.getMonth() + 1}`;
    }
    return `${hours}:${minutes}`;
  } catch {
    return '';
  }
}

function getSenderColor(name: string): string {
  if (!name) return 'text-purple-600 font-bold';
  const colors = [
    'text-emerald-600 font-bold',
    'text-indigo-600 font-bold',
    'text-purple-600 font-bold',
    'text-amber-600 font-bold',
    'text-teal-600 font-bold',
    'text-blue-600 font-bold',
    'text-rose-600 font-bold',
    'text-cyan-600 font-bold',
    'text-violet-600 font-bold'
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % colors.length;
  return colors[index];
}

function getMediaUrl(msg: any, defaultSessionId?: string): string | null {
  if (!msg) return null;
  const sessId = msg.session_id || defaultSessionId;
  const msgId = msg.message_id || msg.id;
  const rawUrl = msg.media_url || msg.image_url || msg.url || msg.file_url;

  if (rawUrl && typeof rawUrl === 'string' && rawUrl.trim()) {
    const trimmed = rawUrl.trim();
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('data:')) {
      return trimmed;
    }
    if (trimmed.startsWith('/api/sessions/')) {
      return trimmed;
    }
    if (sessId && msgId) {
      return `/api/sessions/${encodeURIComponent(sessId)}/media?messageId=${encodeURIComponent(msgId)}`;
    }
    return trimmed;
  }

  // Construct dynamic proxy route if session_id and message_id exist
  if (sessId && msgId) {
    const msgType = (msg.message_type || msg.type || '').toLowerCase();
    const contentText = (msg.content || msg.message || '').trim().toLowerCase();
    const isMediaMsg = msgType.includes('audio') || msgType.includes('image') || msgType.includes('video') || msgType.includes('document') || msgType.includes('ptt') || ['[audio]', '[imagem]', '[video]', '[documento]'].includes(contentText);
    
    if (isMediaMsg) {
      return `/api/sessions/${encodeURIComponent(sessId)}/media?messageId=${encodeURIComponent(msgId)}`;
    }
  }
  return null;
}

function CustomAudioPlayer({ src, isOutgoing }: { src: string; isOutgoing?: boolean }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration || 0);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const toggleSpeed = () => {
    const speeds = [1, 1.5, 2];
    const nextIdx = (speeds.indexOf(playbackRate) + 1) % speeds.length;
    const newSpeed = speeds[nextIdx];
    setPlaybackRate(newSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = newSpeed;
    }
  };

  const formatTime = (secs: number) => {
    if (isNaN(secs) || secs < 0) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const waveformHeights = [
    30, 45, 60, 40, 80, 55, 90, 70, 40, 65, 85, 50, 75, 95, 60, 40, 70, 85, 50, 65, 40, 80, 60, 35, 50
  ];

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className={`media-container mb-2 p-3 rounded-2xl shadow-sm border max-w-xs sm:max-w-sm flex items-center gap-3 transition-all ${
      isOutgoing 
        ? 'bg-emerald-50/90 border-emerald-200/70 text-slate-800'
        : 'bg-slate-50/90 border-slate-200/80 text-slate-800'
    }`}>
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
      />

      {/* Play / Pause Button */}
      <button
        type="button"
        onClick={togglePlay}
        className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold transition-all shadow-md shrink-0 cursor-pointer ${
          isOutgoing
            ? 'bg-emerald-600 hover:bg-emerald-700 hover:scale-105 active:scale-95'
            : 'bg-purple-600 hover:bg-purple-700 hover:scale-105 active:scale-95'
        }`}
      >
        {isPlaying ? (
          <Pause className="w-5 h-5 fill-current" />
        ) : (
          <Play className="w-5 h-5 fill-current ml-0.5" />
        )}
      </button>

      {/* Center Waveform & Progress Slider */}
      <div className="flex-1 flex flex-col gap-1.5 min-w-0">
        {/* Waveform Visualization */}
        <div className="relative h-6 flex items-center gap-0.5 cursor-pointer overflow-hidden group">
          {waveformHeights.map((h, i) => {
            const barPercent = (i / waveformHeights.length) * 100;
            const isPassed = barPercent <= progressPercent;
            return (
              <div
                key={i}
                style={{ height: `${h}%` }}
                className={`w-1 rounded-full transition-colors ${
                  isPassed
                    ? isOutgoing ? 'bg-emerald-600' : 'bg-purple-600'
                    : 'bg-slate-300 group-hover:bg-slate-400'
                }`}
              />
            );
          })}

          <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            onChange={handleSeek}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>

        {/* Timestamp & Speed Controls */}
        <div className="flex items-center justify-between text-[10px] font-semibold text-slate-500">
          <span>{formatTime(currentTime)} / {formatTime(duration)}</span>
          
          <button
            type="button"
            onClick={toggleSpeed}
            className="px-1.5 py-0.5 rounded bg-slate-200/80 hover:bg-slate-300 text-slate-700 transition-colors text-[9px] font-bold cursor-pointer"
            title="Velocidade de reprodução"
          >
            {playbackRate}x
          </button>
        </div>
      </div>
    </div>
  );
}

function renderMessageMedia(msg: any, defaultSessionId?: string, onOpenLightbox?: (url: string) => void, isFromMe?: boolean) {
  const mediaSrc = getMediaUrl(msg, defaultSessionId);
  const msgType = (msg.message_type || msg.type || '').toLowerCase();
  const contentText = (msg.content || msg.message || '').trim().toLowerCase();

  const isImage = msgType.includes('image') || contentText === '[imagem]' || (mediaSrc && /\.(jpg|jpeg|png|gif|webp|bmp|svg)(\?.*)?$/i.test(mediaSrc));
  const isVideo = msgType.includes('video') || contentText === '[video]' || (mediaSrc && /\.(mp4|webm|mkv|mov|avi)(\?.*)?$/i.test(mediaSrc));
  const isAudio = msgType.includes('audio') || msgType.includes('ptt') || msgType.includes('voice') || contentText === '[audio]' || (mediaSrc && /\.(mp3|ogg|wav|m4a|aac|opus)(\?.*)?$/i.test(mediaSrc));
  const isDocument = msgType.includes('document') || msgType.includes('file') || contentText === '[documento]' || (mediaSrc && /\.(pdf|doc|docx|xls|xlsx|zip|rar)(\?.*)?$/i.test(mediaSrc));

  if (isImage && mediaSrc) {
    return (
      <div 
        className="media-container mb-2 overflow-hidden rounded-2xl border border-slate-200/80 shadow-md max-w-xs sm:max-w-sm bg-slate-900/5 group relative cursor-pointer"
        onClick={() => onOpenLightbox && onOpenLightbox(mediaSrc)}
      >
        <img
          src={mediaSrc}
          alt="Imagem"
          className="w-full max-h-72 object-cover rounded-2xl transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLElement).style.display = 'none';
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-3 rounded-2xl">
          <span className="text-white text-xs font-semibold flex items-center gap-1.5 backdrop-blur-md bg-black/40 px-3 py-1 rounded-full border border-white/20 shadow-sm">
            <Maximize2 className="w-3.5 h-3.5" /> Ampliar Imagem
          </span>
        </div>
      </div>
    );
  }

  if (isVideo && mediaSrc) {
    return (
      <div className="media-container mb-2 overflow-hidden rounded-2xl border border-slate-800 shadow-md max-w-xs sm:max-w-sm bg-black">
        <video
          controls
          preload="metadata"
          className="w-full max-h-72 rounded-2xl"
          src={mediaSrc}
        >
          Seu navegador não suporta a reprodução de vídeo.
        </video>
      </div>
    );
  }

  if (isAudio && mediaSrc) {
    return <CustomAudioPlayer src={mediaSrc} isOutgoing={isFromMe} />;
  }

  if (isDocument && mediaSrc) {
    return (
      <div className="media-container mb-2">
        <a
          href={mediaSrc}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 p-3 rounded-2xl bg-purple-50 hover:bg-purple-100/90 border border-purple-200/80 text-purple-950 transition-all shadow-sm max-w-xs group"
        >
          <div className="p-2.5 rounded-xl bg-purple-600 text-white shrink-0 shadow-sm group-hover:scale-105 transition-transform">
            <FileText className="w-5 h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold truncate">Documento / Anexo</p>
            <p className="text-[10px] text-purple-700 flex items-center gap-1 font-medium mt-0.5">
              <Download className="w-3 h-3" /> Clique para abrir/baixar
            </p>
          </div>
        </a>
      </div>
    );
  }

  if (mediaSrc) {
    return (
      <div 
        className="media-container mb-2 overflow-hidden rounded-2xl border border-slate-200/80 shadow-md max-w-xs sm:max-w-sm bg-slate-900/5 group relative cursor-pointer"
        onClick={() => onOpenLightbox && onOpenLightbox(mediaSrc)}
      >
        <img
          src={mediaSrc}
          alt="Arquivo de Mídia"
          className="w-full max-h-72 object-cover rounded-2xl group-hover:scale-105 transition-transform duration-300"
          onError={(e) => {
            (e.target as HTMLElement).style.display = 'none';
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-3 rounded-2xl">
          <span className="text-white text-xs font-semibold flex items-center gap-1.5 backdrop-blur-md bg-black/40 px-3 py-1 rounded-full border border-white/20 shadow-sm">
            <Maximize2 className="w-3.5 h-3.5" /> Ampliar Mídia
          </span>
        </div>
      </div>
    );
  }

  return null;
}

export default function OmnichannelView() {
  // Navigation / Tabs state
  const [activeTab, setActiveTab] = useState<'conversations' | 'contacts'>('conversations');
  const [selectedSession, setSelectedSession] = useState<string>('all');
  
  // Data states - 100% Dynamic from Backend/n8n
  const [conversations, setConversations] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [availableSessions, setAvailableSessions] = useState<any[]>([]);
  const [selectedChat, setSelectedChat] = useState<any | null>(null);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  
  // UI states
  const [loadingList, setLoadingList] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [messageInput, setMessageInput] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [mobileChatOpen, setMobileChatOpen] = useState(false);

  // Lightbox & Attachment Upload states
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const [uploadingMedia, setUploadingMedia] = useState<boolean>(false);
  const [showAttachMenu, setShowAttachMenu] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedMediaType, setSelectedMediaType] = useState<'image' | 'video' | 'audio' | 'document'>('image');

  // Real-time Voice Audio Recorder states
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [recordingTime, setRecordingTime] = useState<number>(0);
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [micVolumeBars, setMicVolumeBars] = useState<number[]>([20, 35, 50, 30, 65, 45, 80, 55, 35, 60, 40, 25]);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const startMicAnalyser = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const drawWave = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        const bars: number[] = [];
        const step = Math.floor(dataArray.length / 12);
        for (let i = 0; i < 12; i++) {
          const val = dataArray[i * step] || 0;
          const height = Math.max(15, Math.min(100, Math.round((val / 255) * 100)));
          bars.push(height);
        }
        setMicVolumeBars(bars);
        animFrameRef.current = requestAnimationFrame(drawWave);
      };

      drawWave();
    } catch (e) {}
  };

  const stopMicAnalyser = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch (e) {}
      audioContextRef.current = null;
    }
    analyserRef.current = null;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setIsPaused(false);
      setPreviewAudioUrl(null);
      setRecordingTime(0);

      startMicAnalyser(stream);

      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      alert('Não foi possível acessar o microfone. Permita o uso do microfone no seu navegador.');
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      stopMicAnalyser();

      if (audioChunksRef.current.length > 0) {
        const previewBlob = new Blob(audioChunksRef.current, { type: 'audio/ogg; codecs=opus' });
        if (previewBlob.size > 0) {
          const url = URL.createObjectURL(previewBlob);
          setPreviewAudioUrl(url);
        }
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      setPreviewAudioUrl(null);

      if (mediaRecorderRef.current.stream) {
        startMicAnalyser(mediaRecorderRef.current.stream);
      }

      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    }
  };

  const cancelRecording = () => {
    stopMicAnalyser();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      const stream = mediaRecorderRef.current.stream;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    }
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
    }
    setIsRecording(false);
    setIsPaused(false);
    setRecordingTime(0);
    setPreviewAudioUrl(null);
    audioChunksRef.current = [];
  };

  const blobToBase64 = (blob: Blob | File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(blob);
    });
  };

  const stopAndSendRecording = async () => {
    if (!mediaRecorderRef.current || !selectedChat) return;

    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
    }
    stopMicAnalyser();

    const recorder = mediaRecorderRef.current;

    const processAndSend = async () => {
      const stream = recorder.stream;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }

      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/ogg; codecs=opus' });
      if (audioBlob.size === 0) {
        cancelRecording();
        return;
      }

      setUploadingMedia(true);
      try {
        const base64Data = await blobToBase64(audioBlob);

        await sendOmnichannelMedia({
          contact_jid: selectedChat.contact_jid,
          session_id: selectedChat.session_id,
          media: {
            kind: 'audio',
            mimeType: 'audio/ogg; codecs=opus',
            fileName: `voice_${Date.now()}.ogg`,
            data: base64Data
          }
        });

        const res: any = await fetchChatHistory(selectedChat.contact_jid, selectedChat.session_id);
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
        setChatMessages(msgsList);
      } catch (err: any) {
        alert(err.message || 'Falha ao enviar mensagem de voz.');
      } finally {
        setUploadingMedia(false);
        setIsRecording(false);
        setIsPaused(false);
        setRecordingTime(0);
        setPreviewAudioUrl(null);
      }
    };

    if (recorder.state === 'inactive') {
      await processAndSend();
    } else {
      recorder.onstop = processAndSend;
      recorder.stop();
    }
  };

  const formatRecordingTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Keyboard shortcut listener for Esc key to close lightbox/menus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isRecording) {
          cancelRecording();
        }
        setLightboxUrl(null);
        setShowAttachMenu(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isRecording]);

  const handleFileSelect = (type: 'image' | 'video' | 'audio' | 'document') => {
    setSelectedMediaType(type);
    setShowAttachMenu(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      if (type === 'image') fileInputRef.current.accept = 'image/*';
      else if (type === 'video') fileInputRef.current.accept = 'video/*';
      else if (type === 'audio') fileInputRef.current.accept = 'audio/*';
      else fileInputRef.current.accept = '*/*';
      fileInputRef.current.click();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedChat) return;

    setUploadingMedia(true);
    try {
      const base64Data = await blobToBase64(file);

      await sendOmnichannelMedia({
        contact_jid: selectedChat.contact_jid,
        session_id: selectedChat.session_id,
        text: messageInput.trim() || undefined,
        media: {
          kind: selectedMediaType,
          mimeType: file.type || undefined,
          fileName: file.name,
          data: base64Data
        }
      });

      setMessageInput('');

      // Instantly refresh history for active chat
      const res: any = await fetchChatHistory(selectedChat.contact_jid, selectedChat.session_id);
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
      setChatMessages(msgsList);
    } catch (err: any) {
      alert(err.message || 'Falha ao enviar arquivo de mídia.');
    } finally {
      setUploadingMedia(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

function playIncomingSound() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;

    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();

    osc1.type = 'sine';
    osc2.type = 'sine';

    osc1.frequency.setValueAtTime(587.33, now); // D5
    osc2.frequency.setValueAtTime(880.00, now + 0.08); // A5

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.1);
    osc2.start(now + 0.08);
    osc2.stop(now + 0.35);
  } catch (e) {}
}

  const selectedChatRef = useRef<any>(null);
  useEffect(() => {
    selectedChatRef.current = selectedChat;
  }, [selectedChat]);

  // Real-time EventSource (SSE) listener for instant n8n webhook notifications
  useEffect(() => {
    const token = localStorage.getItem('token') || '';
    const sseUrl = `${API_BASE}/webhooks/events/crm-chats${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        if (!event.data || event.data.startsWith(':')) return;
        try {
          let notifiedJid = '';
          let isFromMe = false;

          if (event.data.startsWith('{')) {
            const parsed = JSON.parse(event.data);
            notifiedJid = parsed.lead_id || parsed.contact_jid || parsed.jid || '';
            if (parsed.is_from_me === true || parsed.from_me === true || parsed.sender === 'user' || parsed.sender === 'me') {
              isFromMe = true;
            }
          }

          // 1. Immediately reload conversation list to sort latest on top & update badges
          loadConversations();

          // 2. Play chime ONLY if message is NOT from me (incoming from contact)
          if (!isFromMe) {
            playIncomingSound();
          }

          // 3. If active chat is the one receiving the message, reload history in real time
          if (selectedChatRef.current && selectedChatRef.current.contact_jid) {
            const currentJid = selectedChatRef.current.contact_jid;
            if (!notifiedJid || currentJid === notifiedJid || notifiedJid.includes(currentJid) || currentJid.includes(notifiedJid)) {
              fetchChatHistory(selectedChatRef.current.contact_jid, selectedChatRef.current.session_id)
                .then((res: any) => {
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
                  setChatMessages(msgsList);
                })
                .catch(() => {});
            }
          }
        } catch (err) {
          loadConversations();
        }
      };

      eventSource.onerror = () => {
        // Suppress browser console noise on automatic reconnect
      };
    } catch (e) {}

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

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
      if (Array.isArray(data)) {
        const mappedContacts = data.map((c: any) => ({
          ...c,
          push_name: resolveContactName(c)
        }));
        setContacts(mappedContacts);
      }
    } catch (err) {
      console.warn("Error fetching contacts from backend/n8n", err);
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
        const enrichedData = data.map((item: any) => {
          const jid = item.contact_jid || item.jid || item.id || '';
          const resolvedName = resolveContactName(item) || 'Contato';
          return {
            ...item,
            contact_jid: jid,
            push_name: resolvedName,
            display_phone: item.display_phone || null,
            profile_pic_url: item.profile_pic_url || '',
            last_message_preview: item.last_message_preview || '',
            last_message_timestamp: item.last_message_timestamp || new Date().toISOString()
          };
        });

        setConversations(enrichedData);

        // Auto-select the first conversation if none selected
        if (!selectedChat && enrichedData.length > 0) {
          setSelectedChat(enrichedData[0]);
        }
      } else {
        setConversations([]);
      }
    } catch (err) {
      console.warn("Error fetching conversations from backend/n8n", err);
      setConversations([]);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadConversations();
    loadContacts();
  }, []);

  // Fetch Action 3: get_chat_history whenever selectedChat changes
  useEffect(() => {
    if (selectedChat && selectedChat.contact_jid) {
      setLoadingHistory(true);
      fetchChatHistory(selectedChat.contact_jid, selectedChat.session_id)
        .then((res: any) => {
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
          setChatMessages(msgsList);
        })
        .catch((err) => {
          console.warn("Error fetching chat history from backend/n8n", err);
          setChatMessages([]);
        })
        .finally(() => setLoadingHistory(false));
    }
  }, [selectedChat?.contact_jid, selectedChat?.session_id]);

  // Fetch Action 3: get_chat_history when chat selected
  const handleSelectChat = (chat: any) => {
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
      console.warn("Send message error", err);
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

  // Filter and sort conversations (Newest last_message_timestamp at the top of the list)
  const filteredConversations = useMemo(() => {
    const list = conversations.filter(item => {
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

    return list.sort((a, b) => {
      const timeA = new Date(a.last_message_timestamp || a.updated_at || a.created_at || 0).getTime();
      const timeB = new Date(b.last_message_timestamp || b.updated_at || b.created_at || 0).getTime();
      return timeB - timeA;
    });
  }, [conversations, selectedSession, searchTerm]);

  // Messages in active chat window: FIFO (First In, First Out / Chronological: oldest top, newest bottom)
  const sortedMessages = useMemo(() => {
    return [...chatMessages].sort((a, b) => {
      const timeA = new Date(a.message_timestamp || a.timestamp || a.created_at || 0).getTime();
      const timeB = new Date(b.message_timestamp || b.timestamp || b.created_at || 0).getTime();
      return timeA - timeB;
    });
  }, [chatMessages]);

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
    <div className="h-[calc(100vh-3.5rem)] sm:h-[calc(100vh-4.5rem)] lg:h-[calc(100vh-6.5rem)] flex flex-col glass-card bg-white/80 border border-violet-100/50 rounded-2xl overflow-hidden shadow-xl w-full">
      {/* Top Header / Omnichannel Controls */}
      <div className="px-4 py-3 sm:px-6 sm:py-3.5 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-indigo-800/40 shrink-0">
        <div className="flex items-center gap-3 pl-8 lg:pl-0">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 shrink-0">
            <Radio className="w-4 h-4 sm:w-5 sm:h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-display font-black tracking-tight">Dominus Omnichannel</h2>
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                Whats API Sync
              </span>
            </div>
            <p className="text-[11px] sm:text-xs text-indigo-200/80">Centralização multi-sessão em tempo real</p>
          </div>
        </div>

        {/* Action Controls & Session Filter */}
        <div className="flex items-center gap-2.5 self-end sm:self-auto w-full sm:w-auto justify-between sm:justify-end">
          {/* Session Selector */}
          <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-xs flex-1 sm:flex-none justify-between">
            <span className="text-indigo-200 font-bold text-[10px] sm:text-[11px] uppercase tracking-wider">Sessão:</span>
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
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white border border-white/10 transition-all cursor-pointer flex items-center justify-center shrink-0"
          >
            <RefreshCw className={`w-4 h-4 ${loadingList ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Omnichannel Layout Container */}
      <div className="flex-1 flex min-h-0 relative w-full overflow-hidden">
        {/* ================================================================= */}
        {/* LEFT SIDEBAR: Conversations / Contacts List                      */}
        {/* ================================================================= */}
        <div className={`w-full lg:w-80 xl:w-96 border-r border-slate-200/80 bg-slate-50/70 flex flex-col transition-all duration-300 ${
          mobileChatOpen ? 'hidden lg:flex' : 'flex'
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
              loadingList && conversations.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs font-medium space-y-2">
                  <RefreshCw className="w-6 h-6 mx-auto animate-spin text-purple-600" />
                  <p>Carregando conversas do n8n...</p>
                </div>
              ) : filteredConversations.length === 0 ? (
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
                            {(item.participant_pushname || item.participant) && (item.contact_jid?.includes('@g.us') || item.chat_kind === 'group') ? (
                              <span className="font-semibold text-slate-700">
                                {(item.participant_pushname || item.participant)}: {' '}
                              </span>
                            ) : null}
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
        <div className={`w-full lg:flex-1 flex flex-col bg-[#efeae2] relative ${
          !mobileChatOpen ? 'hidden lg:flex' : 'flex'
        }`}>
          {selectedChat ? (
            <>
              {/* Chat Header Bar */}
              <div className="p-3 sm:p-3.5 bg-white border-b border-slate-200/80 flex items-center justify-between shadow-sm z-10">
                <div className="flex items-center gap-2.5">
                  {/* Mobile/Tablet Back Button */}
                  <button
                    onClick={() => setMobileChatOpen(false)}
                    className="lg:hidden px-2.5 py-1.5 rounded-xl text-purple-700 font-bold bg-purple-50 hover:bg-purple-100 transition-all flex items-center gap-1 border border-purple-200 cursor-pointer shadow-sm shrink-0"
                    title="Voltar para a lista de conversas"
                  >
                    <ChevronLeft className="w-5 h-5" />
                    <span className="text-xs">Voltar</span>
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
                    Sessão: {selectedChat.session_id || 'default'}
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
                ) : sortedMessages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400 text-xs font-medium">
                    Nenhuma mensagem registrada nesta conversa.
                  </div>
                ) : (
                  sortedMessages.map((msg, index) => {
                    const isMe = msg.is_from_me === true || msg.sender === 'user';
                    const timeStr = formatTimestamp(msg.message_timestamp || msg.created_at) || '';
                    const rawContent = (msg.content || msg.message || '').trim();
                    const msgType = (msg.message_type || msg.type || '').toLowerCase();
                    const isReaction = msgType === 'reactionmessage' || msgType === 'reaction';

                    if (isReaction) {
                      const emoji = rawContent || '👍';
                      // Find the target message being reacted to
                      let targetMsg = null;
                      const targetId = msg.target_message_id || msg.reaction_target_id || msg.target_id || msg.quoted_id;
                      if (targetId) {
                        targetMsg = sortedMessages.find(m => m.message_id === targetId);
                      }
                      if (!targetMsg && index > 0) {
                        for (let i = index - 1; i >= 0; i--) {
                          const p = sortedMessages[i];
                          const pType = (p.message_type || p.type || '').toLowerCase();
                          if (pType !== 'reactionmessage' && pType !== 'reaction') {
                            targetMsg = p;
                            break;
                          }
                        }
                      }

                      // Position reaction according to the message being reacted to (Left vs Right)
                      const targetIsMe = targetMsg ? (targetMsg.is_from_me === true || targetMsg.sender === 'user') : isMe;

                      return (
                        <div
                          key={msg.message_id || index}
                          className={`flex flex-col ${targetIsMe ? 'items-end pr-4' : 'items-start pl-4'} -mt-4 mb-2 z-20 select-none`}
                        >
                          <div className="bg-white/95 backdrop-blur-md px-2.5 py-1 rounded-full shadow-md border border-slate-200/90 text-xs font-bold flex items-center gap-1 hover:scale-110 transition-transform cursor-pointer group">
                            <span className="text-sm leading-none group-hover:scale-125 transition-transform">{emoji}</span>
                          </div>
                        </div>
                      );
                    }

                    const isGroup = (selectedChat?.contact_jid && selectedChat.contact_jid.includes('@g.us')) || msg.chat_kind === 'group' || selectedChat?.chat_kind === 'group';
                    const senderName = !isMe && isGroup ? (msg.participant_pushname || msg.participant_name || msg.participant_push_name || msg.push_name || msg.participant || selectedChat?.participant_pushname || selectedChat?.participant) : null;

                    const isPlaceholderText = ['[imagem]', '[video]', '[audio]', '[documento]', '[mídia]'].includes(rawContent.toLowerCase());
                    const mediaElement = renderMessageMedia(msg, selectedChat?.session_id, (url) => setLightboxUrl(url), isMe);

                    let quotedText = msg.quoted_text || msg.quoted_content || msg.quotedMessage?.text || msg.context_info?.quotedMessage?.conversation || null;
                    const quotedId = msg.quoted_message_id || msg.quoted_id || null;
                    let quotedSender = msg.quoted_participant || msg.quoted_sender || null;

                    // Fallback: If quotedText is null/empty but quotedId exists, resolve from chatMessages
                    if (!quotedText && quotedId) {
                      const targetMsg = chatMessages.find((m: any) => m.message_id === quotedId);
                      if (targetMsg) {
                        quotedText = (targetMsg.content || targetMsg.message || targetMsg.text || '').trim();
                        if (!quotedSender) {
                          quotedSender = targetMsg.is_from_me ? 'Você' : (targetMsg.participant_pushname || targetMsg.push_name || resolveContactName(selectedChat));
                        }
                      }
                    }

                    if (quotedSender) {
                      if (quotedSender === selectedChat?.contact_jid || quotedSender === selectedChat?.phone || quotedSender === selectedChat?.contact_phone) {
                        quotedSender = resolveContactName(selectedChat);
                      } else if (msg.participant_pushname && (quotedSender === msg.contact_jid || quotedSender === msg.participant)) {
                        quotedSender = msg.participant_pushname;
                      } else if (quotedSender.includes('@')) {
                        const matchedContact = contacts.find(c => c.contact_jid === quotedSender || c.phone === quotedSender.split('@')[0]);
                        if (matchedContact) {
                          quotedSender = resolveContactName(matchedContact);
                        } else {
                          quotedSender = quotedSender.split('@')[0];
                        }
                      }
                    }

                    return (
                      <div
                        key={msg.message_id || index}
                        id={`msg-${msg.message_id || index}`}
                        className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} mb-2 transition-all duration-300 rounded-2xl`}
                      >
                        <div
                          className={`max-w-[85%] md:max-w-[70%] p-3 rounded-2xl shadow-sm relative text-xs leading-relaxed ${
                            isMe
                              ? 'bg-[#d9fdd3] text-slate-900 rounded-tr-none border border-emerald-200/50'
                              : 'bg-white text-slate-900 rounded-tl-none border border-slate-200/60'
                          }`}
                        >
                          {/* Group Participant Header */}
                          {senderName && (
                            <div className={`text-[11px] mb-1 truncate select-none ${getSenderColor(senderName)}`}>
                              ~ {senderName}
                            </div>
                          )}

                          {/* Quoted Message Reference Box */}
                          {quotedText && (
                            <div
                              onClick={() => {
                                if (quotedId) {
                                  const el = document.getElementById(`msg-${quotedId}`);
                                  if (el) {
                                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    el.classList.add('ring-2', 'ring-purple-500', 'scale-[1.02]');
                                    setTimeout(() => {
                                      el.classList.remove('ring-2', 'ring-purple-500', 'scale-[1.02]');
                                    }, 2000);
                                  }
                                }
                              }}
                              className={`mb-2 p-2 rounded-xl text-[11px] border-l-4 overflow-hidden select-none transition-all cursor-pointer ${
                                isMe
                                  ? 'bg-emerald-600/10 border-emerald-600 text-emerald-950 hover:bg-emerald-600/20'
                                  : 'bg-purple-50 border-purple-600 text-purple-950 hover:bg-purple-100'
                              }`}
                              title={quotedId ? "Clique para ir até a mensagem original" : undefined}
                            >
                              <div className="font-bold text-[10px] text-purple-700 truncate mb-0.5 flex items-center justify-between">
                                <span>{quotedSender || 'Mensagem respondida'}</span>
                              </div>
                              <div className="line-clamp-2 text-slate-700 font-medium italic opacity-90">
                                "{quotedText}"
                              </div>
                            </div>
                          )}

                          {/* Render Media (Images, Videos, Audio, Files) */}
                          {mediaElement}

                          {/* Message Content / Caption */}
                          {(!isPlaceholderText || !mediaElement) && rawContent && (
                            <div className="whitespace-pre-wrap break-words pr-12">
                              {rawContent}
                            </div>
                          )}

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

              {/* Hidden File Input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                className="hidden"
              />

              {/* Attachment Popup Menu */}
              {showAttachMenu && (
                <div className="mx-4 mb-2 p-2 bg-white border border-slate-200 rounded-2xl shadow-xl flex items-center justify-around gap-2 animate-fadeIn z-20">
                  <button
                    type="button"
                    onClick={() => handleFileSelect('image')}
                    className="flex flex-col items-center gap-1 p-2.5 rounded-xl hover:bg-purple-50 text-purple-700 transition-colors cursor-pointer"
                  >
                    <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center">
                      <ImageIcon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-bold">Imagem</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleFileSelect('video')}
                    className="flex flex-col items-center gap-1 p-2.5 rounded-xl hover:bg-blue-50 text-blue-700 transition-colors cursor-pointer"
                  >
                    <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center">
                      <Video className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-bold">Vídeo</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleFileSelect('audio')}
                    className="flex flex-col items-center gap-1 p-2.5 rounded-xl hover:bg-emerald-50 text-emerald-700 transition-colors cursor-pointer"
                  >
                    <div className="w-9 h-9 rounded-full bg-emerald-100 flex items-center justify-center">
                      <Mic className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-bold">Áudio</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleFileSelect('document')}
                    className="flex flex-col items-center gap-1 p-2.5 rounded-xl hover:bg-amber-50 text-amber-700 transition-colors cursor-pointer"
                  >
                    <div className="w-9 h-9 rounded-full bg-amber-100 flex items-center justify-center">
                      <FileText className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-bold">Documento</span>
                  </button>
                </div>
              )}

              {/* Bottom Message Input Bar */}
              {isRecording ? (
                <div className="p-3 bg-white border-t border-slate-200 flex items-center justify-between gap-3 shadow-lg z-10 animate-fadeIn min-h-[64px]">
                  {/* Left: Delete Trash Button */}
                  <button
                    type="button"
                    onClick={cancelRecording}
                    className="p-2.5 rounded-xl text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer shrink-0"
                    title="Descartar gravação (Esc)"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>

                  {/* Center Content: Preview Player OR Live Recording Waveform */}
                  {isPaused && previewAudioUrl ? (
                    <div className="flex-1 max-w-md my-0">
                      <CustomAudioPlayer src={previewAudioUrl} isOutgoing={true} />
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center gap-3 bg-slate-50 px-3 py-2 rounded-2xl border border-slate-200/80">
                      <span className="relative flex h-3 w-3 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                      </span>

                      {/* Real-time Dynamic Waveform Spectrum */}
                      <div className="flex-1 h-6 flex items-center gap-1 overflow-hidden">
                        {micVolumeBars.map((h, i) => (
                          <div
                            key={i}
                            style={{ height: `${h}%` }}
                            className="w-1.5 bg-red-500/80 rounded-full transition-all duration-75"
                          />
                        ))}
                      </div>

                      <span className="font-mono text-xs font-bold text-red-600 bg-red-100/80 px-2.5 py-1 rounded-full border border-red-200/60 shrink-0 shadow-xs">
                        {formatRecordingTime(recordingTime)}
                      </span>
                    </div>
                  )}

                  {/* Right Actions: Pause / Resume & Send */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isPaused ? (
                      <button
                        type="button"
                        onClick={resumeRecording}
                        className="p-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold transition-all shadow-md flex items-center justify-center cursor-pointer hover:scale-105 active:scale-95"
                        title="Continuar gravando"
                      >
                        <Mic className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={pauseRecording}
                        className="p-2.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold transition-all shadow-sm flex items-center justify-center cursor-pointer hover:scale-105 active:scale-95"
                        title="Pausar gravação e ouvir"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={stopAndSendRecording}
                      disabled={uploadingMedia}
                      className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition-all shadow-md flex items-center justify-center cursor-pointer hover:scale-105 active:scale-95"
                      title="Enviar mensagem de voz"
                    >
                      {uploadingMedia ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              ) : (
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
                    onClick={() => setShowAttachMenu(!showAttachMenu)}
                    className={`p-2 rounded-xl transition-colors cursor-pointer ${
                      showAttachMenu ? 'bg-purple-100 text-purple-700' : 'text-slate-500 hover:text-purple-600 hover:bg-slate-100'
                    }`}
                    title="Anexar arquivo"
                  >
                    <Paperclip className="w-5 h-5" />
                  </button>

                  {/* Input Text Field */}
                  <input
                    type="text"
                    placeholder={uploadingMedia ? "Enviando arquivo..." : "Digite uma mensagem"}
                    disabled={uploadingMedia}
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-slate-100 text-xs font-semibold text-slate-800 placeholder-slate-400 outline-none focus:ring-2 focus:ring-purple-500/20 focus:bg-white transition-all border border-slate-200/60"
                  />

                  {/* Send Text OR Start Voice Recording Button */}
                  {messageInput.trim() ? (
                    <button
                      type="submit"
                      disabled={sending || uploadingMedia}
                      className="p-2.5 rounded-xl text-white font-bold transition-all shadow-md flex items-center justify-center cursor-pointer bg-gradient-to-r from-purple-700 to-indigo-600 hover:scale-105 active:scale-95"
                      title="Enviar mensagem"
                    >
                      {uploadingMedia ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={startRecording}
                      disabled={uploadingMedia}
                      className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition-all shadow-md flex items-center justify-center cursor-pointer hover:scale-105 active:scale-95"
                      title="Gravar áudio"
                    >
                      {uploadingMedia ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                    </button>
                  )}
                </form>
              )}
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

      {/* Modern Lightbox Modal for Image & Media Preview */}
      {lightboxUrl && (
        <div 
          className="fixed inset-0 z-[9999] bg-black/90 backdrop-blur-md flex items-center justify-center p-4 transition-all duration-300 animate-fadeIn"
          onClick={() => setLightboxUrl(null)}
        >
          <div className="relative max-w-5xl max-h-[90vh] flex flex-col items-center" onClick={(e) => e.stopPropagation()}>
            {/* Action Bar */}
            <div className="absolute -top-12 right-0 flex items-center gap-3 z-10">
              <a
                href={lightboxUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors border border-white/20 shadow-lg"
                title="Abrir em nova aba"
              >
                <ExternalLink className="w-5 h-5" />
              </a>
              <a
                href={lightboxUrl}
                download
                className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors border border-white/20 shadow-lg"
                title="Baixar mídia"
              >
                <Download className="w-5 h-5" />
              </a>
              <button
                onClick={() => setLightboxUrl(null)}
                className="p-2.5 rounded-full bg-white/20 hover:bg-red-500 text-white transition-colors border border-white/30 shadow-lg cursor-pointer"
                title="Fechar (Esc)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Media Image Content */}
            <img
              src={lightboxUrl}
              alt="Mídia Ampliada"
              className="max-h-[85vh] max-w-[90vw] object-contain rounded-2xl shadow-2xl border border-white/10"
            />
          </div>
        </div>
      )}
    </div>
  );
}
