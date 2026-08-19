import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

promo_ui = """
              <div className="grid grid-cols-2 gap-3">
                <div className={newPromo.discount_type === 'free_shipping' ? "col-span-2" : ""}>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Tipo de Desconto</label>
                  <select
                    value={newPromo.discount_type}
                    onChange={(e) => setNewPromo({ ...newPromo, discount_type: e.target.value as 'percentage' | 'fixed' | 'free_shipping' })}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500 bg-white"
                  >
                    <option value="percentage">Porcentagem (%)</option>
                    <option value="fixed">Valor Fixo (R$)</option>
                    <option value="free_shipping">Frete Grátis</option>
                  </select>
                </div>
                {newPromo.discount_type !== 'free_shipping' && (
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">Valor do Desconto</label>
                    <input
                      type="number"
                      step="0.01"
                      value={newPromo.discount_value || 0}
                      onChange={(e) => setNewPromo({ ...newPromo, discount_value: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                    />
                  </div>
                )}
              </div>
"""

old_promo_block = r'<div className="grid grid-cols-2 gap-3">\s*<div>\s*<label className="block text-xs font-bold text-slate-600 mb-1">Tipo de Desconto</label>\s*<select\s*value={newPromo\.discount_type}\s*onChange={\(e\) => setNewPromo\({ \.\.\.newPromo, discount_type: e\.target\.value as \'percentage\' \| \'fixed\' }\)}\s*className="w-full px-3\.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500 bg-white"\s*>\s*<option value="percentage">Porcentagem \(%\)</option>\s*<option value="fixed">Valor Fixo \(R\$\)</option>\s*</select>\s*</div>\s*<div>\s*<label className="block text-xs font-bold text-slate-600 mb-1">Valor do Desconto</label>\s*<input\s*type="number"\s*step="0\.01"\s*value={newPromo\.discount_value \|\| 0}\s*onChange={\(e\) => setNewPromo\({ \.\.\.newPromo, discount_value: parseFloat\(e\.target\.value\) \|\| 0 }\)}\s*className="w-full px-3\.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"\s*/>\s*</div>\s*</div>'

content = re.sub(old_promo_block, promo_ui.strip(), content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
print("Promo UI patched")
