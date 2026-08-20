import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

old_badge = """                      <span className={`font-semibold ${item.available ? 'text-emerald-600' : 'text-rose-500'}`}>
                        {item.available ? '● Ativo para Oferta' : '○ Indisponível no Momento'}
                      </span>"""

new_badge = """                      <div className="flex items-center gap-3">
                        <span className={`font-semibold ${item.available ? 'text-emerald-600' : 'text-rose-500'}`}>
                          {item.available ? '● Ativo' : '○ Indisponível'}
                        </span>
                        <span className="text-slate-500 font-medium border-l border-slate-200 pl-3">
                          Estoque: {item.stock || 0}
                        </span>
                      </div>"""
content = content.replace(old_badge, new_badge)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
