import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# Replace the initial state
content = content.replace("const [selectedSession, setSelectedSession] = useState<string>('all');", "const [selectedSession, setSelectedSession] = useState<string>('');")

# Update the sessionsList logic to also effect the selectedSession
old_sessions_list = """  // Sessions list options
  const sessionsList = useMemo(() => {
    const setOfSessions = new Set<string>();
    conversations.forEach(c => {
      if (c.session_id) setOfSessions.add(c.session_id);
    });
    availableSessions.forEach(s => setOfSessions.add(s.id));
    return Array.from(setOfSessions).sort();
  }, [conversations, availableSessions]);"""

new_sessions_list = """  // Sessions list options
  const sessionsList = useMemo(() => {
    const setOfSessions = new Set<string>();
    conversations.forEach(c => {
      if (c.session_id) setOfSessions.add(c.session_id);
    });
    availableSessions.forEach(s => setOfSessions.add(s.id));
    return Array.from(setOfSessions).sort();
  }, [conversations, availableSessions]);

  // Default to first session if none selected
  useEffect(() => {
    if ((!selectedSession || selectedSession === 'all') && sessionsList.length > 0) {
      setSelectedSession(sessionsList[0]);
    }
  }, [sessionsList, selectedSession]);"""

content = content.replace(old_sessions_list, new_sessions_list)

# Remove 'all' logic in filteredConversations
old_filter = """const matchSession = selectedSession === 'all' || item.session_id === selectedSession;"""
new_filter = """const matchSession = item.session_id === selectedSession;"""
content = content.replace(old_filter, new_filter)

# Remove the 'all' option in the selector
old_option = """<option value="all" className="bg-slate-800 text-white">Todas as Sessões</option>"""
content = content.replace(old_option, "")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
