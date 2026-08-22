with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# 1. Add knownMessageIds ref
old_refs = """  const selectedChatRef = useRef<any>(null);
  useEffect(() => {
    selectedChatRef.current = selectedChat;
  }, [selectedChat]);"""

new_refs = """  const selectedChatRef = useRef<any>(null);
  const knownMessageIds = useRef<Set<string>>(new Set());
  useEffect(() => {
    selectedChatRef.current = selectedChat;
  }, [selectedChat]);"""
content = content.replace(old_refs, new_refs)

# 2. Modify sound trigger logic to check knownMessageIds
old_trigger = """          // 1. Check if there is actual media/text (ignore empty ACKs for sounds)
          const hasContent = newMsgs.some(m => {
            if (m._encrypted) return false;
            const c = (m.content || m.message || m.text || m.body || '').trim();
            return c.length > 0 || m.image_url || m.video_url || m.audio_url || m.document_url;
          });

          // Play chime ONLY if it is an actual message (not just an ACK)
          if (hasContent) {
            if (!isFromMe) {
              playIncomingSound();
            } else {
              playOutgoingSound();
            }
          }"""

new_trigger = """          // 1. Check if it's a NEW message and has content (ignore duplicate status updates for sounds)
          let isNewMessageWithContent = false;
          
          for (const m of newMsgs) {
            if (m._encrypted) continue;
            
            const msgId = String(m.message_id || m.id || m.key?.id || '');
            const c = (m.content || m.message || m.text || m.body || '').trim();
            const hasMediaOrText = c.length > 0 || m.image_url || m.video_url || m.audio_url || m.document_url;
            
            if (hasMediaOrText && msgId) {
              if (!knownMessageIds.current.has(msgId)) {
                knownMessageIds.current.add(msgId);
                isNewMessageWithContent = true;
              }
            } else if (hasMediaOrText && !msgId) {
              isNewMessageWithContent = true;
            }
          }

          // Play chime ONLY if it is an entirely new message
          if (isNewMessageWithContent) {
            if (!isFromMe) {
              playIncomingSound();
            } else {
              playOutgoingSound();
            }
          }"""
content = content.replace(old_trigger, new_trigger)

# 3. Add existing history IDs to knownMessageIds on load
old_history = """          setChatMessages(msgsList);
        })
        .catch((err) => {"""

new_history = """          setChatMessages(msgsList);
          msgsList.forEach((m: any) => {
             const id = String(m.message_id || m.id || m.key?.id || '');
             if (id) knownMessageIds.current.add(id);
          });
        })
        .catch((err) => {"""
content = content.replace(old_history, new_history)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
