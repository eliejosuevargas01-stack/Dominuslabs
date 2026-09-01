type SessionScopedRecord = {
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
};

export const MAX_KNOWN_MESSAGE_IDS = 500;

/** Stores each real-time ID once without retaining an unbounded history. */
export function rememberKnownMessageId(
  knownMessageIds: Set<string>,
  messageId: unknown,
  limit = MAX_KNOWN_MESSAGE_IDS,
): boolean {
  const normalizedId = String(messageId ?? '').trim();
  if (!normalizedId || knownMessageIds.has(normalizedId)) return false;

  knownMessageIds.add(normalizedId);
  while (knownMessageIds.size > limit) {
    const oldestId = knownMessageIds.values().next().value as string | undefined;
    if (!oldestId) break;
    knownMessageIds.delete(oldestId);
  }
  return true;
}

function sessionValue(record: SessionScopedRecord): unknown {
  const session = record.session;
  return record.session_id
    ?? record.whatsapp_instance
    ?? (typeof session === 'object' && session !== null ? (session as { id?: unknown }).id : session);
}

export function normalizeSessionId(sessionId: unknown): string {
  return String(sessionId ?? '')
    .trim()
    .toLocaleLowerCase()
    .replace(/[-_\s]/g, '');
}

export function sessionsMatch(first: unknown, second: unknown): boolean {
  const normalizedFirst = normalizeSessionId(first);
  const normalizedSecond = normalizeSessionId(second);
  return Boolean(normalizedFirst && normalizedSecond && normalizedFirst === normalizedSecond);
}

function normalizeJid(jid: unknown): string {
  return String(jid ?? '')
    .split('@')[0]
    .split(':')[0]
    .trim()
    .toLocaleLowerCase();
}

export function jidsMatch(first: unknown, second: unknown): boolean {
  const normalizedFirst = normalizeJid(first);
  const normalizedSecond = normalizeJid(second);
  if (!normalizedFirst || !normalizedSecond) return false;
  if (normalizedFirst === normalizedSecond) return true;

  return /^\d+$/.test(normalizedFirst)
    && /^\d+$/.test(normalizedSecond)
    && normalizedFirst.length >= 8
    && normalizedSecond.length >= 8
    && (normalizedFirst.endsWith(normalizedSecond) || normalizedSecond.endsWith(normalizedFirst));
}

function contactJids(record: SessionScopedRecord): unknown[] {
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
}

/**
 * A conversation is scoped by both the WhatsApp session and contact identity.
 * Events without a session are deliberately not attached to a session-specific
 * conversation; this prevents legacy, shared-inbox events from leaking across
 * sessions.
 */
export function messageBelongsToConversation(
  message: SessionScopedRecord,
  conversation: SessionScopedRecord,
): boolean {
  if (!sessionsMatch(sessionValue(message), sessionValue(conversation))) return false;

  return contactJids(message).some(messageJid =>
    contactJids(conversation).some(conversationJid => jidsMatch(messageJid, conversationJid)),
  );
}

/** Extracts only messages that belong to the exact session/contact conversation. */
export function scopedHistoryMessages(
  response: unknown,
  conversation: SessionScopedRecord,
): SessionScopedRecord[] {
  const responseItems = Array.isArray(response)
    ? response
    : (response && typeof response === 'object' ? [response] : []);
  const messages: SessionScopedRecord[] = [];

  for (const item of responseItems) {
    if (!item || typeof item !== 'object') continue;
    const container = item as SessionScopedRecord;
    const nested = Array.isArray(container.messages)
      ? container.messages
      : (Array.isArray(container.mensagens) ? container.mensagens : [container]);

    for (const rawMessage of nested) {
      if (!rawMessage || typeof rawMessage !== 'object') continue;
      const message = { ...(rawMessage as SessionScopedRecord) };
      if (!sessionValue(message)) message.session_id = sessionValue(container);
      if (contactJids(message).length === 0) {
        message.contact_jid = container.contact_jid ?? container.jid ?? container.chat_jid;
      }
      if (messageBelongsToConversation(message, conversation)) {
        messages.push(message);
      }
    }
  }

  return messages;
}
