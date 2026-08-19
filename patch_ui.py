import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

# 1. Update initial state to include delivery_tiers
content = content.replace("delivery_max_coverage_km: 20.0,", "delivery_tiers: [],")

# 2. Update the UI block.
# I need to find the block for "Raio Coberto / Distância Máx." and replace it with a UI for building the tiers.
import textwrap

tier_ui = """
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Taxas por Raio de Distância
                </label>
                {settings.delivery_fee_type === 'Por Raio' ? (
                  <div className="space-y-3">
                    {(settings.delivery_tiers || []).map((tier, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <span className="text-sm text-slate-600">Até</span>
                        <input
                          type="number" min="0" step="0.1"
                          value={tier.up_to_km}
                          onChange={(e) => {
                            const newTiers = [...(settings.delivery_tiers || [])];
                            newTiers[idx].up_to_km = parseFloat(e.target.value) || 0;
                            setSettings({...settings, delivery_tiers: newTiers});
                          }}
                          className="w-20 px-2 py-1.5 rounded-lg border border-slate-200 outline-none text-sm"
                        />
                        <span className="text-sm text-slate-600">km: R$</span>
                        <input
                          type="number" min="0" step="0.01"
                          value={tier.price}
                          onChange={(e) => {
                            const newTiers = [...(settings.delivery_tiers || [])];
                            newTiers[idx].price = parseFloat(e.target.value) || 0;
                            setSettings({...settings, delivery_tiers: newTiers});
                          }}
                          className="w-24 px-2 py-1.5 rounded-lg border border-slate-200 outline-none text-sm"
                        />
                        <button type="button" onClick={() => {
                          const newTiers = [...(settings.delivery_tiers || [])];
                          newTiers.splice(idx, 1);
                          setSettings({...settings, delivery_tiers: newTiers});
                        }} className="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg">
                          ✕
                        </button>
                      </div>
                    ))}
                    <button type="button" onClick={() => {
                       const newTiers = [...(settings.delivery_tiers || []), { up_to_km: 0, price: 0 }];
                       setSettings({...settings, delivery_tiers: newTiers});
                    }} className="text-sm text-purple-600 font-medium flex items-center gap-1 hover:text-purple-700">
                      + Adicionar Faixa de Distância
                    </button>
                  </div>
                ) : (
                  <div className="text-sm text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-100">
                    Selecione "Por Raio" no modelo acima para configurar.
                  </div>
                )}
              </div>
"""

# Let's find the max_coverage field block
import re
pattern = r'<div>\s*<label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1\.5 flex items-center gap-1\.5">\s*Raio Coberto / Distância Máx\. p/ Cálculo \(KM\)\s*</label>.*?</div>\s*</div>'
content = re.sub(pattern, tier_ui.strip(), content, flags=re.DOTALL)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
print("UI patched")
