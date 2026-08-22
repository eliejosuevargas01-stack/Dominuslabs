with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

# 1. Add playOutgoingSound function below playIncomingSound
old_func = """function playIncomingSound() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;

    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();

    osc1.type = 'sine';
    osc2.type = 'sine';

    osc1.frequency.setValueAtTime(587.33, now); // D5
    osc2.frequency.setValueAtTime(880.00, now + 0.08); // A5

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.1);
    osc2.start(now + 0.08);
    osc2.stop(now + 0.35);
  } catch (e) {}
}"""

new_func = old_func + """

function playOutgoingSound() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;
    
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(300, now);
    osc.frequency.exponentialRampToValueAtTime(600, now + 0.1);
    
    gain.gain.setValueAtTime(0.05, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.start(now);
    osc.stop(now + 0.15);
  } catch (e) {}
}"""
content = content.replace(old_func, new_func)

# 2. Modify the event sound trigger
old_trigger = """          // 1. Play chime ONLY if message is NOT from me
          if (!isFromMe) {
            playIncomingSound();
          }"""

new_trigger = """          // 1. Check if there is actual media/text (ignore empty ACKs for sounds)
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

content = content.replace(old_trigger, new_trigger)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
