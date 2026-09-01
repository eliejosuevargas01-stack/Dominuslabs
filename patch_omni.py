import re

with open("src/pages/OmnichannelView.tsx", "r") as f:
    content = f.read()

search_block = """              const normalized = {
                ...rawMsg,
                id: rawMsg.id || rawMsg.message_id || rawMsg.key?.id || generatedId,
                message_id: rawMsg.message_id || rawMsg.id || rawMsg.key?.id || generatedId,
                content: rawMsg.content || rawMsg.text || (typeof rawMsg.message === 'string' ? rawMsg.message : '') || rawMsg.body || rawMsg.output || '',
                text: rawMsg.text || rawMsg.content || (typeof rawMsg.message === 'string' ? rawMsg.message : '') || rawMsg.body || rawMsg.output || '',
                is_from_me: msgIsFromMe,
                from_me: msgIsFromMe,
                fromMe: msgIsFromMe,
                contact_jid: msgIsFromMe
                  ? (rawMsg.to || rawMsg.recipient || rawMsg.key?.remoteJid || parsed.to || parsed.recipient || rawMsg.contact_jid || rawMsg.jid || rawMsg.resolvedJid || rawMsg.lid || parsed.conversation?.jid || parsed.contact_jid)
                  : (rawMsg.contact_jid || rawMsg.jid || rawMsg.resolvedJid || rawMsg.lid || rawMsg.key?.remoteJid || parsed.conversation?.jid || parsed.contact_jid),
                session_id: rawMsg.session_id || parsed.session_id || parsed.session?.id,
                message_timestamp: msgTs,
                status: rawMsg.status || 'sent',
                media_url: rawMsg.media_url || rawMsg.url || rawMsg.file_url || (rawMsg.media?.url),
                participant_pushname: rawMsg.pushName || rawMsg.participant_pushname || parsed.conversation?.title
              };
              newMsgs.push(normalized);
            }

            if (
              parsed.is_from_me === true ||
              parsed.from_me === true ||
              parsed.fromMe === true ||
              parsed.sender === 'user' ||
              parsed.sender === 'me'
            ) {
              isFromMe = true;
            }"""

replace_block = """              const resolvedSessionId = rawMsg.session_id || parsed.session_id || parsed.session?.id;
              let resolvedContactJid = msgIsFromMe
                ? (rawMsg.key?.remoteJid || rawMsg.participant || rawMsg.to || rawMsg.recipient || parsed.to || parsed.recipient || rawMsg.contact_jid || rawMsg.jid || rawMsg.resolvedJid || rawMsg.lid || parsed.conversation?.jid || parsed.contact_jid)
                : (rawMsg.contact_jid || rawMsg.jid || rawMsg.resolvedJid || rawMsg.lid || rawMsg.key?.remoteJid || parsed.conversation?.jid || parsed.contact_jid);

              if (!resolvedSessionId || !resolvedContactJid) {
                // Drop events without a reliable scope to prevent shared inbox leakage
                continue;
              }

              const normalized = {
                ...rawMsg,
                id: rawMsg.id || rawMsg.message_id || rawMsg.key?.id || generatedId,
                message_id: rawMsg.message_id || rawMsg.id || rawMsg.key?.id || generatedId,
                content: rawMsg.content || rawMsg.text || (typeof rawMsg.message === 'string' ? rawMsg.message : '') || rawMsg.body || rawMsg.output || '',
                text: rawMsg.text || rawMsg.content || (typeof rawMsg.message === 'string' ? rawMsg.message : '') || rawMsg.body || rawMsg.output || '',
                is_from_me: msgIsFromMe,
                from_me: msgIsFromMe,
                fromMe: msgIsFromMe,
                contact_jid: resolvedContactJid,
                session_id: resolvedSessionId,
                message_timestamp: msgTs,
                status: rawMsg.status || 'sent',
                media_url: rawMsg.media_url || rawMsg.url || rawMsg.file_url || (rawMsg.media?.url),
                participant_pushname: rawMsg.pushName || rawMsg.participant_pushname || parsed.conversation?.title
              };
              newMsgs.push(normalized);
            }

            if (
              parsed.is_from_me === true ||
              parsed.from_me === true ||
              parsed.fromMe === true ||
              parsed.sender === 'user' ||
              parsed.sender === 'me'
            ) {
              isFromMe = true;
            }"""

if search_block in content:
    content = content.replace(search_block, replace_block)
else:
    print("Failed to replace in OmnichannelView.tsx")

with open("src/pages/OmnichannelView.tsx", "w") as f:
    f.write(content)
