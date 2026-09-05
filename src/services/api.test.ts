import { describe, it, expect } from 'vitest';
import { decodeJwtExp } from './api';

describe('decodeJwtExp', () => {
  it('returns the expiration time for a valid token', () => {
    const payload = { exp: 1700000000, sub: 'user123' };
    const base64Payload = btoa(JSON.stringify(payload));
    const token = `header.${base64Payload}.signature`;

    expect(decodeJwtExp(token)).toBe(1700000000);
  });

  it('returns null for a valid token without exp', () => {
    const payload = { sub: 'user123' };
    const base64Payload = btoa(JSON.stringify(payload));
    const token = `header.${base64Payload}.signature`;

    expect(decodeJwtExp(token)).toBeNull();
  });

  it('returns null if the token does not have 3 parts', () => {
    expect(decodeJwtExp('invalid-token')).toBeNull();
    expect(decodeJwtExp('part1.part2')).toBeNull();
    expect(decodeJwtExp('part1.part2.part3.part4')).toBeNull();
    expect(decodeJwtExp('')).toBeNull();
  });

  it('returns null if the payload is not valid base64', () => {
    const token = `header.not-valid-base64!@#.signature`;
    expect(decodeJwtExp(token)).toBeNull();
  });

  it('returns null if the payload is valid base64 but not valid JSON', () => {
    const base64Payload = btoa('not valid json');
    const token = `header.${base64Payload}.signature`;
    expect(decodeJwtExp(token)).toBeNull();
  });

  it('handles base64url encoding correctly by replacing - and _', () => {
    // btoa('{"exp":1700000000,"k":"????"}') produces a base64 string with + or /
    // {"exp":1700000000,"k":"??>"} -> btoa is eyJleHAiOjE3MDAwMDAwMDAsImsiOiI/Pj8ifQ==
    // Let's directly craft a payload that needs replacement:
    const payload = { exp: 1700000000 };
    const base64Standard = btoa(JSON.stringify(payload));
    // Simulate base64url encoding where + is - and / is _
    // We'll add some dummy properties to ensure + and / appear in the standard base64
    // btoa('{"exp":1700000000,"foo":"~~~"}') -> eyJleHAiOjE3MDAwMDAwMDAsImZvbyI6In5+fiJ9
    // btoa('>>?') -> Pj4/ (contains /)
    const complexPayload = { exp: 1700000000, chars: '>>?' };
    const base64WithSlashAndPlus = btoa(JSON.stringify(complexPayload));

    // Convert to base64url format
    const base64Url = base64WithSlashAndPlus.replace(/\+/g, '-').replace(/\//g, '_');
    const token = `header.${base64Url}.signature`;

    expect(decodeJwtExp(token)).toBe(1700000000);
  });
});
