with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

old_price_block = """                <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Valor Unitário (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={newItem.price || 0}
                  onChange={(e) => setNewItem({ ...newItem, price: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>
            </div>"""

new_price_block = """                <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Valor Unitário (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={newItem.price || 0}
                  onChange={(e) => setNewItem({ ...newItem, price: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Estoque (Qtd)</label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={newItem.stock || 0}
                  onChange={(e) => setNewItem({ ...newItem, stock: parseInt(e.target.value) || 0 })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>
            </div>"""

content = content.replace(old_price_block, new_price_block)
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
