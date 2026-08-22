import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'r') as f:
    content = f.read()

old_sidebar_preview = """                            {item.last_message_is_from_me && (
                              <span className="inline-flex mr-1 align-middle">
                                {(item.last_message_status === 'read' || item.last_message_status === 'played') ? (
                                  <CheckCheck className="w-3.5 h-3.5 text-sky-500" />
                                ) : (item.last_message_status === 'received' || item.last_message_status === 'delivered' || item.last_message_status === 'delivery_ack') ? (
                                  <CheckCheck className="w-3.5 h-3.5 text-slate-400" />
                                ) : (item.last_message_status === 'sending') ? (
                                  <Clock className="w-3 h-3 text-slate-400 animate-pulse" />
                                ) : (
                                  <Check className="w-3.5 h-3.5 text-slate-400" />
                                )}
                              </span>
                            )}"""

new_sidebar_preview = """                            {item.last_message_is_from_me && (() => {
                              const st = (item.last_message_status || '').toString().toLowerCase().trim();
                              return (
                                <span className="inline-flex mr-1 align-middle">
                                  {(st === 'read' || st === 'played') ? (
                                    <CheckCheck className="w-3.5 h-3.5 text-sky-500" />
                                  ) : (st === 'received' || st === 'delivered' || st === 'delivery_ack') ? (
                                    <CheckCheck className="w-3.5 h-3.5 text-slate-400" />
                                  ) : (st === 'sending') ? (
                                    <Clock className="w-3 h-3 text-slate-400 animate-pulse" />
                                  ) : (
                                    <Check className="w-3.5 h-3.5 text-slate-400" />
                                  )}
                                </span>
                              );
                            })()}"""

content = content.replace(old_sidebar_preview, new_sidebar_preview)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/OmnichannelView.tsx', 'w') as f:
    f.write(content)
