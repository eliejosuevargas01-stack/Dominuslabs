import re

file_path = "/home/eliezer/Vídeos/api whatsapp/server.js"
with open(file_path, "r") as f:
    content = f.read()

target = """  const myJid = sock?.user?.id ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : null;
  const participantJid = message?.key?.participant ? message.key.participant.split(':')[0] + '@s.whatsapp.net' : null;"""

replacement = """  const myJid = sock?.user?.id ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : null;
  const myLid = sock?.user?.lid ? sock.user.lid.split(':')[0] + '@lid' : null;
  const participantRaw = message?.key?.participant;
  
  let participantJid = null;
  let participantLid = null;
  if (participantRaw) {
    if (participantRaw.includes('@lid')) {
      participantLid = participantRaw.split(':')[0] + '@lid';
    } else {
      participantJid = participantRaw.split(':')[0] + '@s.whatsapp.net';
    }
  }"""

if target in content:
    content = content.replace(target, replacement)
    
target2 = """  if (!isFromMe && myJid) {
    if (participantJid && myJid === participantJid) {
      isFromMe = true;
    } else if (remoteCleanJid && myJid === remoteCleanJid && message?.key?.participant === undefined) {
      // Se enviou mensagem pra si mesmo a partir de outro dispositivo
      isFromMe = true;
    }
  }"""

replacement2 = """  if (!isFromMe) {
    if (myJid && participantJid && myJid === participantJid) {
      isFromMe = true;
    } else if (myLid && participantLid && myLid === participantLid) {
      isFromMe = true;
    } else if (myJid && remoteCleanJid && myJid === remoteCleanJid && message?.key?.participant === undefined) {
      // Se enviou mensagem pra si mesmo a partir de outro dispositivo
      isFromMe = true;
    }
  }"""

if target2 in content:
    content = content.replace(target2, replacement2)

with open(file_path, "w") as f:
    f.write(content)

print("server.js patched successfully.")
