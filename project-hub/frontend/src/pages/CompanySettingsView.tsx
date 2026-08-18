import { useState, useEffect } from 'react';
import {
  Building2,
  Bot,
  ShieldAlert,
  UtensilsCrossed,
  CreditCard,
  Save,
  Plus,
  Trash2,
  CheckCircle2,
  Loader2,
  Sparkles,
  DollarSign,
  FileText,
  Clock,
  MapPin,
  Phone,
  Mail,
  Award
} from 'lucide-react';
import { toast } from 'sonner';
import { fetchCompanySettings, updateCompanySettings, type CompanySettings, type MenuItem } from '../services/api';

const TONE_OPTIONS = [
  { id: 'Formal', label: 'Formal e Profissional', desc: 'Comunicação séria, objetiva e alinhada a normas corporativas.' },
  { id: 'Amigável', label: 'Amigável e Receptivo', desc: 'Linguagem acolhedora, calorosa e focada no bom relacionamento.' },
  { id: 'Consultivo', label: 'Consultivo e Especialista', desc: 'Foco em entender a dor do cliente e oferecer soluções embasadas.' },
  { id: 'Descontraído', label: 'Descontraído e Jovem', desc: 'Uso leve de emojis, linguagem moderna e tom informal.' },
  { id: 'Vendedor', label: 'Vendedor e Persuasivo', desc: 'Foco alto em conversão, ofertas e senso de urgência.' },
];

const PAYMENT_METHODS = [
  'Pix',
  'Cartão de Crédito',
  'Cartão de Débito',
  'Dinheiro',
  'Boleto Bancário',
  'Faturamento / Link de Pagamento'
];

export default function CompanySettingsView() {
  const [activeTab, setActiveTab] = useState<'general' | 'tone' | 'policies' | 'menu' | 'payments'>('general');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [settings, setSettings] = useState<CompanySettings>({
    company_name: '',
    cnpj_cpf: '',
    phone: '',
    email: '',
    address: '',
    business_hours: '',
    tone_of_voice: 'Amigável',
    custom_instructions: '',
    exchange_policy: '',
    delivery_policy: '',
    terms_of_service: '',
    menu_catalog: [],
    accepted_payment_types: ['Pix', 'Cartão de Crédito'],
    payment_notes: '',
    values_mission: '',
    additional_notes: ''
  });

  // Modal State for Adding/Editing Menu/Catalog Item
  const [isMenuModalOpen, setIsMenuModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [newItem, setNewItem] = useState<MenuItem>({
    name: '',
    category: '',
    price: 0,
    description: '',
    available: true
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await fetchCompanySettings("default");
      setSettings({
        ...data,
        menu_catalog: data.menu_catalog || [],
        accepted_payment_types: data.accepted_payment_types || ['Pix', 'Cartão de Crédito']
      });
    } catch (err: any) {
      toast.error(err.message || 'Erro ao carregar configurações.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateCompanySettings(settings, "default");
      setSettings(updated);
      toast.success('Configurações salvas com sucesso!');
    } catch (err: any) {
      toast.error(err.message || 'Erro ao salvar configurações.');
    } finally {
      setSaving(false);
    }
  };

  const togglePaymentType = (type: string) => {
    const current = settings.accepted_payment_types || [];
    const updated = current.includes(type)
      ? current.filter(t => t !== type)
      : [...current, type];
    setSettings({ ...settings, accepted_payment_types: updated });
  };

  const handleSaveMenuItem = () => {
    if (!newItem.name.trim()) {
      toast.error('Informe o nome do item.');
      return;
    }

    const currentCatalog = [...(settings.menu_catalog || [])];
    if (editingIndex !== null) {
      currentCatalog[editingIndex] = newItem;
    } else {
      currentCatalog.push({ ...newItem, id: `item-${Date.now()}` });
    }

    setSettings({ ...settings, menu_catalog: currentCatalog });
    setIsMenuModalOpen(false);
    setNewItem({ name: '', category: '', price: 0, description: '', available: true });
    setEditingIndex(null);
    toast.success('Item adicionado ao catálogo com sucesso!');
  };

  const handleDeleteMenuItem = (index: number) => {
    const currentCatalog = [...(settings.menu_catalog || [])];
    currentCatalog.splice(index, 1);
    setSettings({ ...settings, menu_catalog: currentCatalog });
    toast.info('Item removido.');
  };

  const openEditMenuItem = (index: number) => {
    const item = settings.menu_catalog![index];
    setNewItem(item);
    setEditingIndex(index);
    setIsMenuModalOpen(true);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
        <p className="text-sm font-medium text-slate-500">Carregando configurações da empresa...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-2xl border border-violet-100 shadow-sm">
        <div>
          <h1 className="text-2xl font-display font-extrabold text-slate-900 flex items-center gap-2">
            <Building2 className="w-7 h-7 text-purple-600" />
            Configurações Gerais da Empresa
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Gerencie perfil, tom de voz para a IA, políticas institucionais, cardápio/catálogo e formas de pagamento.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-purple-700 to-indigo-600 hover:from-purple-800 hover:to-indigo-700 text-white font-semibold text-sm px-6 py-2.5 rounded-xl shadow-md shadow-purple-600/20 transition-all cursor-pointer disabled:opacity-50 self-start sm:self-auto"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Salvando...' : 'Salvar Alterações'}
        </button>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-violet-100 bg-white/60 p-1.5 rounded-xl overflow-x-auto gap-1">
        {[
          { id: 'general', label: 'Dados da Empresa & Missão', icon: Building2 },
          { id: 'tone', label: 'Tom de Voz & IA', icon: Bot },
          { id: 'policies', label: 'Políticas & Termos', icon: ShieldAlert },
          { id: 'menu', label: 'Cardápio / Catálogo', icon: UtensilsCrossed },
          { id: 'payments', label: 'Formas de Pagamento', icon: CreditCard },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all whitespace-nowrap cursor-pointer ${
                active
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-purple-700 hover:bg-violet-50/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Contents */}
      <div className="bg-white/90 backdrop-blur-md rounded-2xl border border-violet-100 shadow-sm p-6 sm:p-8">
        {/* Tab 1: Dados Gerais */}
        {activeTab === 'general' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Building2 className="w-5 h-5 text-purple-600" />
              Informações Institucionais e Contato
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" /> Nome da Empresa
                </label>
                <input
                  type="text"
                  value={settings.company_name || ''}
                  onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
                  placeholder="Ex: Dominus Labs Agência Digital"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-400" /> CNPJ / CPF
                </label>
                <input
                  type="text"
                  value={settings.cnpj_cpf || ''}
                  onChange={(e) => setSettings({ ...settings, cnpj_cpf: e.target.value })}
                  placeholder="Ex: 00.000.000/0001-00"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-slate-400" /> Telefone / WhatsApp Comercial
                </label>
                <input
                  type="text"
                  value={settings.phone || ''}
                  onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
                  placeholder="Ex: +55 (11) 99999-9999"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" /> E-mail Oficial de Suporte
                </label>
                <input
                  type="email"
                  value={settings.email || ''}
                  onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                  placeholder="Ex: contato@suaempresa.com.br"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" /> Endereço Físico / Sede
                </label>
                <input
                  type="text"
                  value={settings.address || ''}
                  onChange={(e) => setSettings({ ...settings, address: e.target.value })}
                  placeholder="Ex: Av. Paulista, 1000, Cj. 42 - Bela Vista, São Paulo/SP"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" /> Horário de Funcionamento
                </label>
                <input
                  type="text"
                  value={settings.business_hours || ''}
                  onChange={(e) => setSettings({ ...settings, business_hours: e.target.value })}
                  placeholder="Ex: Segunda a Sexta das 08h às 18h | Sábados das 09h às 13h"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5 text-slate-400" /> Missão, Visão e Valores
                </label>
                <textarea
                  rows={4}
                  value={settings.values_mission || ''}
                  onChange={(e) => setSettings({ ...settings, values_mission: e.target.value })}
                  placeholder="Descreva aqui o propósito da empresa e seus valores fundamentais que devem orientar o atendimento..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Tom de Voz & Atendimento */}
        {activeTab === 'tone' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Bot className="w-5 h-5 text-purple-600" />
              Tom de Voz do Atendimento e Instruções da IA
            </h2>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
                Selecione o Estilo de Comunicação Predominante
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {TONE_OPTIONS.map((tone) => {
                  const isSelected = settings.tone_of_voice === tone.id;
                  return (
                    <div
                      key={tone.id}
                      onClick={() => setSettings({ ...settings, tone_of_voice: tone.id })}
                      className={`p-4 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'border-purple-600 bg-purple-50/60 shadow-sm'
                          : 'border-slate-200 hover:border-purple-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-sm text-slate-900">{tone.label}</span>
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-purple-600" />}
                      </div>
                      <p className="text-xs text-slate-500 leading-relaxed">{tone.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-purple-600" /> Instruções Específicas e Comportamento para Chatbots
              </label>
              <p className="text-xs text-slate-500 mb-2">
                Insira regras estritas, saudações padrão, restrições ou termos que a IA deve utilizar no atendimento automático.
              </p>
              <textarea
                rows={6}
                value={settings.custom_instructions || ''}
                onChange={(e) => setSettings({ ...settings, custom_instructions: e.target.value })}
                placeholder="Exemplo: Sempre cumprimente pelo primeiro nome. Nunca ofereça descontos superiores a 10% sem autorização prévia. Se o cliente perguntar sobre prazos, informe que o tempo de resposta do suporte é de até 15 minutos."
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all font-mono text-slate-700"
              />
            </div>
          </div>
        )}

        {/* Tab 3: Políticas da Empresa */}
        {activeTab === 'policies' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <ShieldAlert className="w-5 h-5 text-purple-600" />
              Políticas Comerciais e Termos
            </h2>

            <div className="space-y-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Política de Troca, Devolução e Garantia
                </label>
                <textarea
                  rows={4}
                  value={settings.exchange_policy || ''}
                  onChange={(e) => setSettings({ ...settings, exchange_policy: e.target.value })}
                  placeholder="Explique os critérios para trocas, reembolsos, garantia do produto ou cancelamento..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Política de Frete, Entrega e Prazos
                </label>
                <textarea
                  rows={4}
                  value={settings.delivery_policy || ''}
                  onChange={(e) => setSettings({ ...settings, delivery_policy: e.target.value })}
                  placeholder="Detalhamento sobre taxas de entrega, prazos médios por região e transportadoras parceiras..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Termos de Serviço e Privacidade (LGPD)
                </label>
                <textarea
                  rows={4}
                  value={settings.terms_of_service || ''}
                  onChange={(e) => setSettings({ ...settings, terms_of_service: e.target.value })}
                  placeholder="Resumo dos termos contratuais e diretrizes sobre o uso de dados e privacidade..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Cardápio / Catálogo */}
        {activeTab === 'menu' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <UtensilsCrossed className="w-5 h-5 text-purple-600" />
                  Catálogo de Produtos / Cardápio
                </h2>
                <p className="text-xs text-slate-500">
                  Cadastre itens para consulta rápida e recomendação automática pelo robô comercial.
                </p>
              </div>

              <button
                onClick={() => {
                  setNewItem({ name: '', category: '', price: 0, description: '', available: true });
                  setEditingIndex(null);
                  setIsMenuModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 bg-purple-100 hover:bg-purple-200 text-purple-800 font-semibold text-xs px-3.5 py-2 rounded-xl transition-all cursor-pointer self-start sm:self-auto"
              >
                <Plus className="w-4 h-4" />
                Adicionar Item
              </button>
            </div>

            {settings.menu_catalog && settings.menu_catalog.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {settings.menu_catalog.map((item, index) => (
                  <div
                    key={index}
                    className="p-4 rounded-xl border border-slate-200 hover:border-purple-200 bg-slate-50/50 flex flex-col justify-between gap-3 transition-all"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className="font-bold text-slate-900 text-base">{item.name}</span>
                        <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200 text-xs whitespace-nowrap">
                          R$ {Number(item.price || 0).toFixed(2)}
                        </span>
                      </div>

                      {item.category && (
                        <span className="inline-block text-[11px] font-semibold text-slate-500 bg-slate-200/60 px-2 py-0.5 rounded-full mb-2">
                          {item.category}
                        </span>
                      )}

                      {item.description && (
                        <p className="text-xs text-slate-600 line-clamp-2">{item.description}</p>
                      )}
                    </div>

                    <div className="flex items-center justify-between border-t border-slate-200/60 pt-2 text-xs">
                      <span className={`font-semibold ${item.available ? 'text-emerald-600' : 'text-rose-500'}`}>
                        {item.available ? '● Disponível' : '○ Indisponível'}
                      </span>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditMenuItem(index)}
                          className="text-purple-600 hover:text-purple-800 font-medium cursor-pointer"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleDeleteMenuItem(index)}
                          className="text-rose-500 hover:text-rose-700 p-1 cursor-pointer"
                          title="Remover"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                <UtensilsCrossed className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-600">Nenhum item cadastrado no catálogo</p>
                <p className="text-xs text-slate-400 mt-1">Clique no botão acima para incluir produtos ou ofertas.</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Formas de Pagamento Aceitas */}
        {activeTab === 'payments' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <CreditCard className="w-5 h-5 text-purple-600" />
              Métodos e Condições de Pagamento
            </h2>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
                Selecione as Formas de Pagamento Aceitas pela Empresa
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {PAYMENT_METHODS.map((method) => {
                  const isChecked = (settings.accepted_payment_types || []).includes(method);
                  return (
                    <label
                      key={method}
                      onClick={() => togglePaymentType(method)}
                      className={`flex items-center gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                        isChecked
                          ? 'border-purple-600 bg-purple-50/50 text-purple-950 font-bold'
                          : 'border-slate-200 hover:border-purple-200 text-slate-600'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                        isChecked ? 'bg-purple-600 border-purple-600 text-white' : 'border-slate-300 bg-white'
                      }`}>
                        {isChecked && <CheckCircle2 className="w-3.5 h-3.5" />}
                      </div>
                      <span className="text-sm">{method}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-slate-400" /> Instruções, Chaves Pix e Descontos
              </label>
              <textarea
                rows={4}
                value={settings.payment_notes || ''}
                onChange={(e) => setSettings({ ...settings, payment_notes: e.target.value })}
                placeholder="Exemplo: Chave Pix CNPJ: 00.000.000/0001-00 (Dominus Labs). Oferecemos 5% de desconto para pagamentos à vista via Pix."
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
              />
            </div>
          </div>
        )}
      </div>

      {/* Modal for Item Catalog */}
      {isMenuModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              {editingIndex !== null ? 'Editar Item do Catálogo' : 'Novo Item do Catálogo'}
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Nome do Item/Produto *</label>
                <input
                  type="text"
                  value={newItem.name}
                  onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                  placeholder="Ex: Consultoria de Agente IA"
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Categoria</label>
                  <input
                    type="text"
                    value={newItem.category || ''}
                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                    placeholder="Ex: Serviços"
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Preço (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newItem.price || 0}
                    onChange={(e) => setNewItem({ ...newItem, price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Descrição</label>
                <textarea
                  rows={3}
                  value={newItem.description || ''}
                  onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                  placeholder="Resumo das características..."
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={newItem.available}
                  onChange={(e) => setNewItem({ ...newItem, available: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Item disponível para comercialização
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setIsMenuModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:bg-slate-100 cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveMenuItem}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white shadow-sm cursor-pointer"
              >
                Salvar Item
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
