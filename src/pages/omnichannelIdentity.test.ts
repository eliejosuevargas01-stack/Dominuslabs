import { describe, expect, it } from 'vitest';

import {
  MAX_KNOWN_MESSAGE_IDS,
  messageBelongsToConversation,
  rememberKnownMessageId,
  scopedHistoryMessages,
  sessionsMatch,
} from './omnichannelIdentity';

describe('omnichannel conversation identity', () => {
  it('requires the WhatsApp session as well as the contact JID', () => {
    const conversation = {
      contact_jid: '5511999999999@s.whatsapp.net',
      session_id: 'sessao-a',
    };

    expect(messageBelongsToConversation({
      contact_jid: '5511999999999@s.whatsapp.net',
      session_id: 'sessao-b',
    }, conversation)).toBe(false);

    expect(messageBelongsToConversation({
      contact_jid: '5511999999999@s.whatsapp.net',
      session_id: 'sessao-a',
    }, conversation)).toBe(true);
  });

  it('does not attach legacy events without a session to a session-specific chat', () => {
    expect(messageBelongsToConversation({
      contact_jid: '5511999999999@s.whatsapp.net',
    }, {
      contact_jid: '5511999999999@s.whatsapp.net',
      session_id: 'sessao-a',
    })).toBe(false);
  });

  it('normalizes equivalent session identifiers without confusing different sessions', () => {
    expect(sessionsMatch('Sessao_A', 'sessao-a')).toBe(true);
    expect(sessionsMatch('sessao-a', 'sessao-b')).toBe(false);
  });

  it('filters a mixed history to the selected session and inherits a wrapper session', () => {
    const selectedConversation = {
      contact_jid: '5511999999999@s.whatsapp.net',
      session_id: 'sessao-a',
    };
    const messages = scopedHistoryMessages([
      {
        contact_jid: '5511999999999@s.whatsapp.net',
        session_id: 'sessao-a',
        messages: [{ id: 'a-1', content: 'Mensagem A' }],
      },
      {
        contact_jid: '5511999999999@s.whatsapp.net',
        session_id: 'sessao-b',
        messages: [{ id: 'b-1', content: 'Mensagem B' }],
      },
    ], selectedConversation);

    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({ id: 'a-1', session_id: 'sessao-a' });
  });

  it('keeps the real-time message deduplication cache bounded', () => {
    const ids = new Set<string>();
    const limit = 3;

    expect(rememberKnownMessageId(ids, 'first', limit)).toBe(true);
    expect(rememberKnownMessageId(ids, 'second', limit)).toBe(true);
    expect(rememberKnownMessageId(ids, 'third', limit)).toBe(true);
    expect(rememberKnownMessageId(ids, 'first', limit)).toBe(false);
    expect(rememberKnownMessageId(ids, 'fourth', limit)).toBe(true);

    expect(ids).toEqual(new Set(['second', 'third', 'fourth']));
    expect(MAX_KNOWN_MESSAGE_IDS).toBeGreaterThan(limit);
  });
});
