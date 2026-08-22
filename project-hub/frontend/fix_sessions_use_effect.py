import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_sessions_list = """  // Sessions list options
  const sessionsList = useMemo(() => {
    const setOfSessions = new Set<string>();
    conversations.forEach(c => {
      if (c.session_id) setOfSessions.add(c.session_id);
    });
    availableSessions.forEach(s => setOfSessions.add(s.id));
    return Array.from(setOfSessions);
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

  useEffect(() => {
    if ((!selectedSession || selectedSession === 'all') && sessionsList.length > 0) {
      setSelectedSession(sessionsList[0]);
    }
  }, [sessionsList, selectedSession]);"""

content = content.replace(old_sessions_list, new_sessions_list)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
