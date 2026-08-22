import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_reaction_render = """                    if (isReaction) {
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
                    }"""

new_reaction_render = """                    if (isReaction) {
                      return null; // Reactions are now handled via reactionsMap attached to the parent bubble!
                    }"""

content = content.replace(old_reaction_render, new_reaction_render)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
