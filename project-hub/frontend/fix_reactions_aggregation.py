with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_map = """  const reactionsMap = useMemo(() => {
    const map: Record<string, { emoji: string; count: number }[]> = {};
    for (const msg of chatMessages) {
      if (!msg) continue;
      const msgType = (msg.message_type || msg.type || msg.kind || '').toString().toLowerCase();
      const isReaction = !!msg.reaction_target_message_id || !!msg.reaction_text || msgType.includes('reaction') || !!msg.reactionMessage || !!msg.is_reaction;
      if (isReaction) {
        const emoji = (msg.reaction_text || msg.content || msg.message || msg.reactionMessage?.text || '').trim();
        const targetId = msg.reaction_target_message_id || msg.reaction_target_id || msg.target_message_id || msg.target_id || msg.quoted_message_id || msg.quoted_id || msg.reactionMessage?.key?.id;
        if (targetId && emoji && emoji !== 'null' && emoji !== 'undefined') {
          if (!map[targetId]) map[targetId] = [];
          const existing = map[targetId].find(r => r.emoji === emoji);
          if (existing) {
            existing.count += 1;
          } else {
            map[targetId].push({ emoji, count: 1 });
          }
        }
      }
    }
    return map;
  }, [chatMessages]);"""

new_map = """  const reactionsMap = useMemo(() => {
    // 1. Group latest reaction per sender per target message
    const latestReactions: Record<string, Record<string, string>> = {};

    for (const msg of chatMessages) {
      if (!msg) continue;
      const msgType = (msg.message_type || msg.type || msg.kind || '').toString().toLowerCase();
      const isReaction = !!msg.reaction_target_message_id || !!msg.reaction_text || msgType.includes('reaction') || !!msg.reactionMessage || !!msg.is_reaction;
      
      if (isReaction) {
        const emoji = (msg.reaction_text || msg.content || msg.message || msg.reactionMessage?.text || '').trim();
        const targetId = msg.reaction_target_message_id || msg.reaction_target_id || msg.target_message_id || msg.target_id || msg.quoted_message_id || msg.quoted_id || msg.reactionMessage?.key?.id;
        const sender = msg.reaction_target_sender_jid || msg.participant || msg.contact_jid || (msg.is_from_me ? 'me' : 'other');

        if (targetId) {
          if (!latestReactions[targetId]) latestReactions[targetId] = {};
          
          if (!emoji || emoji === 'null' || emoji === 'undefined') {
             // Removing reaction
             delete latestReactions[targetId][sender];
          } else {
             latestReactions[targetId][sender] = emoji;
          }
        }
      }
    }

    // 2. Aggregate counts per emoji
    const map: Record<string, { emoji: string; count: number }[]> = {};
    for (const [targetId, senders] of Object.entries(latestReactions)) {
      const emojiCounts: Record<string, number> = {};
      for (const emoji of Object.values(senders)) {
        emojiCounts[emoji] = (emojiCounts[emoji] || 0) + 1;
      }
      
      map[targetId] = Object.entries(emojiCounts).map(([emoji, count]) => ({ emoji, count }));
    }

    return map;
  }, [chatMessages]);"""

content = content.replace(old_map, new_map)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
