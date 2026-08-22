with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# find the Action Controls & Session Filter section
old_html = """        {/* Action Controls & Session Filter */}
        <div className="flex items-center gap-2.5 self-end sm:self-auto w-full sm:w-auto justify-between sm:justify-end">
          {/* Session Selector */}
          <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-xs flex-1 sm:flex-none justify-between">
            <span className="text-indigo-200 font-bold text-[10px] sm:text-[11px] uppercase tracking-wider">Sessão:</span>
            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              className="bg-transparent text-white font-semibold outline-none cursor-pointer text-xs pr-1"
            >
              
              {sessionsList.map(s => (
                <option key={s} value={s} className="bg-slate-800 text-white">
                  📱 {s}
                </option>
              ))}
            </select>
          </div>

          <button"""

new_html = """        {/* Action Controls & Session Filter */}
        <div className="flex items-center gap-2.5 self-end sm:self-auto w-full sm:w-auto justify-between sm:justify-end">
          {/* Sessões em Abas (Caixinhas) Expansíveis */}
          <div className="flex items-center bg-white/10 backdrop-blur-md rounded-xl border border-white/10 text-xs flex-1 sm:flex-none justify-between overflow-hidden shadow-inner">
            <span className="text-indigo-200/60 font-black text-[9px] uppercase tracking-widest pl-3 pr-1 py-2 select-none">
              Sessões
            </span>
            
            <div 
              className={`flex flex-nowrap overflow-x-auto no-scrollbar items-center py-1 gap-1 pl-1 transition-all duration-500 ease-in-out scroll-smooth snap-x ${sessionsExpanded ? 'max-w-[400px]' : 'max-w-[140px]'}`}
            >
              {/* O item selecionado é renderizado primeiro, ou destacamos ele na lista */}
              {sessionsList.map(s => (
                <button
                  key={s}
                  onClick={() => setSelectedSession(s)}
                  className={`shrink-0 snap-start px-2.5 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-300 flex items-center gap-1.5 border ${
                    selectedSession === s 
                      ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md border-indigo-400/30' 
                      : 'bg-white/5 text-indigo-100/70 border-white/5 hover:bg-white/10 hover:text-white'
                  }`}
                  title={s}
                >
                  <span className="text-sm">📱</span>
                  <span className="max-w-[80px] truncate">{s}</span>
                </button>
              ))}
            </div>

            {sessionsList.length > 1 && (
              <button 
                onClick={() => setSessionsExpanded(!sessionsExpanded)}
                title={sessionsExpanded ? "Encolher sessões" : "Expandir sessões"}
                className="px-2 h-full flex items-center justify-center border-l border-white/5 text-indigo-200/50 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              >
                <ChevronLeft className={`w-4 h-4 transition-transform duration-500 ${sessionsExpanded ? 'rotate-180' : ''}`} />
              </button>
            )}
          </div>

          <button"""

content = content.replace(old_html, new_html)

# Add sessionsExpanded state
old_state = "  const [mobileChatOpen, setMobileChatOpen] = useState(false);"
new_state = "  const [mobileChatOpen, setMobileChatOpen] = useState(false);\n  const [sessionsExpanded, setSessionsExpanded] = useState(false);"
content = content.replace(old_state, new_state)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
