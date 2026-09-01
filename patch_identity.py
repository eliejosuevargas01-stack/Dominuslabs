import re

with open("src/pages/omnichannelIdentity.ts", "r") as f:
    content = f.read()

search_block_1 = """type SessionScopedRecord = {
  [key: string]: unknown;
  session_id?: unknown;
  session?: unknown;
  whatsapp_instance?: unknown;
  contact_jid?: unknown;
  chat_jid?: unknown;
  group_jid?: unknown;
  jid?: unknown;
  phone?: unknown;
  remoteJid?: unknown;
  to?: unknown;
  recipient?: unknown;
  key?: { remoteJid?: unknown };
  messages?: unknown;
  mensagens?: unknown;
};"""

replace_block_1 = """type SessionScopedRecord = {
  [key: string]: unknown;
  session_id?: unknown;
  session?: unknown;
  whatsapp_instance?: unknown;
  contact_jid?: unknown;
  chat_jid?: unknown;
  group_jid?: unknown;
  jid?: unknown;
  phone?: unknown;
  remoteJid?: unknown;
  to?: unknown;
  recipient?: unknown;
  participant?: unknown;
  is_from_me?: unknown;
  from_me?: unknown;
  fromMe?: unknown;
  key?: { remoteJid?: unknown };
  messages?: unknown;
  mensagens?: unknown;
};"""

search_block_2 = """function contactJids(record: SessionScopedRecord): unknown[] {
  return [
    record.contact_jid,
    record.chat_jid,
    record.group_jid,
    record.jid,
    record.phone,
    record.remoteJid,
    record.key?.remoteJid,
    record.to,
    record.recipient,
  ].filter(Boolean);
}"""

replace_block_2 = """function contactJids(record: SessionScopedRecord): unknown[] {
  const isFromMe = record.is_from_me || record.from_me || record.fromMe;

  if (isFromMe) {
    // For outbound messages, the local JID might be in 'jid' or 'contact_jid' depending on backend payload
    // We must prioritize the remote recipient to avoid matching our own session JID
    return [
      record.key?.remoteJid,
      record.participant,
      record.to,
      record.recipient,
      record.contact_jid,
      record.remoteJid,
      record.jid,
      record.chat_jid,
      record.group_jid,
      record.phone,
    ].filter(Boolean);
  }

  return [
    record.contact_jid,
    record.chat_jid,
    record.group_jid,
    record.jid,
    record.phone,
    record.remoteJid,
    record.key?.remoteJid,
    record.participant,
    record.to,
    record.recipient,
  ].filter(Boolean);
}"""


content = content.replace(search_block_1, replace_block_1)
content = content.replace(search_block_2, replace_block_2)

with open("src/pages/omnichannelIdentity.ts", "w") as f:
    f.write(content)
