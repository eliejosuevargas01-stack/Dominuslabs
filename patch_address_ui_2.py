import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

address_ui = """
              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" /> Endereço Principal (Rua / Avenida)
                </label>
                <input
                  type="text"
                  value={settings.address || ''}
                  onChange={(e) => setSettings({ ...settings, address: e.target.value })}
                  placeholder="Ex: Av. das Nações Unidas"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Número
                </label>
                <input
                  type="text"
                  value={settings.address_number || ''}
                  onChange={(e) => setSettings({ ...settings, address_number: e.target.value })}
                  placeholder="Ex: 12901"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Bairro
                </label>
                <input
                  type="text"
                  value={settings.address_neighborhood || ''}
                  onChange={(e) => setSettings({ ...settings, address_neighborhood: e.target.value })}
                  placeholder="Ex: Brooklin"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Cidade
                </label>
                <input
                  type="text"
                  value={settings.address_city || ''}
                  onChange={(e) => setSettings({ ...settings, address_city: e.target.value })}
                  placeholder="Ex: São Paulo"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Estado (UF)
                </label>
                <input
                  type="text"
                  value={settings.address_state || ''}
                  onChange={(e) => setSettings({ ...settings, address_state: e.target.value })}
                  placeholder="Ex: SP"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  CEP
                </label>
                <input
                  type="text"
                  value={settings.address_zip || ''}
                  onChange={(e) => setSettings({ ...settings, address_zip: e.target.value })}
                  placeholder="Ex: 04578-000"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>
"""

old_address_block = r'<div className="md:col-span-2">\s*<label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1\.5 flex items-center gap-1\.5">\s*<MapPin className="w-3\.5 h-3\.5 text-slate-400" /> Endereço da Sede Corporativa\s*</label>\s*<input\s*type="text"\s*value={settings\.address \|\| \'\'}\s*onChange={\(e\) => setSettings\({ \.\.\.settings, address: e\.target\.value }\)}\s*placeholder="Ex: Av\. das Nações Unidas, 12901 - Torre Leste, 18º andar - Brooklin, São Paulo/SP"\s*className="w-full px-4 py-2\.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"\s*/>\s*</div>'

content = re.sub(old_address_block, address_ui.strip(), content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
print("Address UI patched")
