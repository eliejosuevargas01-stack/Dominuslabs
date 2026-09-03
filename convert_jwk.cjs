const crypto = require('crypto');
const fs = require('fs');
const jwk = {"kty":"RSA","alg":"RS256","use":"sig","kid":"kid_2026_01","n":"04Wsvbb-rKGKGWYQi0fCg3sVY8tozqRG3LiPcgDfNCbYPNBSPj2cqa5UWd0NkIz8-tn6_xSYzFLMDBjOXSv9UcvEHuurbMs5zxBRn8ij8xRYQAkt1f-bL3uEg0is78JpgqbmqwuI5QGMqL2zq0_VOE7JFcJ63EP1iJAd5Q3XeSu44yqcEHKQni12xlFLsjD50KsiW65mHbpVkfENmTCw9Jo5OI2sub3yjkNHH31MrfK-EQF7fuOEJF3_imPOOpE-1-aoKeIqMzCa52UXrUTdQjfqRvv6diKIdERKa6VuAajQcyO1zhYiL_cY94KG6KmKT7N-xYWWn3X8DbpWdKWxiw","e":"AQAB"};

const publicKey = crypto.createPublicKey({
  key: jwk,
  format: 'jwk'
});

const pem = publicKey.export({ type: 'spki', format: 'pem' });
fs.writeFileSync('/home/eliezer/Vídeos/api whatsapp/keys/worker_public.key', pem);
console.log("Key written successfully!");
