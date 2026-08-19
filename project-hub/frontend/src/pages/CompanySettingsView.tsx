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
  { id: 'Formal', label: 'Corporativo & Institucional', desc: 'Comunicação executiva, altamente formal, fundamentada em diretrizes corporativas e conformidade.' },
  { id: 'Amigável', label: 'Relacional & Receptivo', desc: 'Abordagem humanizada, calorosa e focada na excelência da experiência do cliente (CX).' },
  { id: 'Consultivo', label: 'Consultivo & Especialista', desc: 'Atendimento direcionado à resolução estratégica de dores, com embasamento técnico e autoridade.' },
  { id: 'Descontraído', label: 'Dinâmico & Moderno', desc: 'Tom fluido, engajador e contemporâneo, adequado para audiências jovens e ecossistemas de inovação.' },
  { id: 'Vendedor', label: 'Comercial & Orientado a Resultados', desc: 'Foco incisivo em conversão de pipeline, proposta de valor e aceleração do ciclo de vendas.' },
];

const PAYMENT_METHODS = [
  'Pix Instantâneo (Bacen)',
  'Cartão de Crédito Corporate',
  'Cartão de Débito',
  'Transferência Bancária (TED/DOC)',
  'Boleto Bancário Registrado',
  'Faturamento Faturado / Link de Pagamento'
];

export default function CompanySettingsView() {
  const [activeTab, setActiveTab] = useState<'general' | 'tone' | 'policies' | 'menu' | 'promotions' | 'payments' | 'delivery'>('general');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [settings, setSettings] = useState<CompanySettings>({
    company_name: '',
    cnpj_cpf: '',
    phone: '',
    email: '',
    address: '',
    business_hours: '',
    tone_of_voice: 'Consultivo',
    custom_instructions: '',
    exchange_policy: '',
    delivery_policy: '',
    terms_of_service: '',
    menu_catalog: [],
    accepted_payment_types: ['Pix Instantâneo (Bacen)', 'Cartão de Crédito Corporate'],
    payment_notes: '',
    values_mission: '',
    additional_notes: '',
    delivery_fee_type: 'Fixo',
    delivery_fee_value: 0,
    delivery_radius_km: 0,
    minimum_order_value: 0,
    preparation_time_minutes: 0,
    promotions: []
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
        accepted_payment_types: data.accepted_payment_types || ['Pix Instantâneo (Bacen)', 'Cartão de Crédito Corporate']
      });
    } catch (err: any) {
      toast.error(err.message || 'Erro ao sincronizar diretrizes corporativas.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateCompanySettings(settings, "default");
      setSettings(updated);
      toast.success('Diretrizes e parâmetros corporativos salvos com sucesso!');
    } catch (err: any) {
      toast.error(err.message || 'Erro ao atualizar parâmetros institucionais.');
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
      toast.error('Informe a denominação oficial do item/solução.');
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
    toast.success('Item homologado e incluído no catálogo corporativo!');
  };

  const handleDeleteMenuItem = (index: number) => {
    const currentCatalog = [...(settings.menu_catalog || [])];
    currentCatalog.splice(index, 1);
    setSettings({ ...settings, menu_catalog: currentCatalog });
    toast.info('Item descontinuado do catálogo.');
  };

  const openEditMenuItem = (index: number) => {
    const item = settings.menu_catalog![index];
    setNewItem(item);
    setEditingIndex(index);
    setIsMenuModalOpen(true);
  };

  // Promotion Modal State
  const [isPromoModalOpen, setIsPromoModalOpen] = useState(false);
  const [editingPromoIndex, setEditingPromoIndex] = useState<number | null>(null);
  const [newPromo, setNewPromo] = useState<any>({
    name: '',
    discount_type: 'percentage',
    discount_value: 0,
    valid_until: '',
    description: '',
    active: true
  });

  const handleSavePromo = () => {
    if (!newPromo.name.trim()) {
      toast.error('Informe o nome da promoção.');
      return;
    }
    const currentPromos = [...(settings.promotions || [])];
    if (editingPromoIndex !== null) {
      currentPromos[editingPromoIndex] = newPromo;
    } else {
      currentPromos.push({ ...newPromo, id: `promo-${Date.now()}` });
    }
    setSettings({ ...settings, promotions: currentPromos });
    setIsPromoModalOpen(false);
    setNewPromo({ name: '', discount_type: 'percentage', discount_value: 0, valid_until: '', description: '', active: true });
    setEditingPromoIndex(null);
    toast.success('Promoção salva com sucesso!');
  };

  const handleDeletePromo = (index: number) => {
    const currentPromos = [...(settings.promotions || [])];
    currentPromos.splice(index, 1);
    setSettings({ ...settings, promotions: currentPromos });
    toast.info('Promoção removida.');
  };

  const openEditPromo = (index: number) => {
    const item = settings.promotions![index];
    setNewPromo(item);
    setEditingPromoIndex(index);
    setIsPromoModalOpen(true);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
        <p className="text-sm font-semibold text-slate-600">Carregando governança e parâmetros organizacionais...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-2xl border border-violet-100 shadow-sm">
        <div>
          <h1 className="text-2xl font-display font-extrabold text-slate-900 flex items-center gap-2.5">
            <Building2 className="w-7 h-7 text-purple-600" />
            Governança & Parâmetros da Empresa
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Gestão centralizada de dados institucionais, persona & tom de voz para IA, SLAs comerciais, produtos e condições financeiras.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-purple-700 to-indigo-600 hover:from-purple-800 hover:to-indigo-700 text-white font-semibold text-sm px-6 py-2.5 rounded-xl shadow-md shadow-purple-600/20 transition-all cursor-pointer disabled:opacity-50 self-start sm:self-auto"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Aplicando Alterações...' : 'Salvar Alterações'}
        </button>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-violet-100 bg-white/60 p-1.5 rounded-xl overflow-x-auto gap-1">
        {[
          { id: 'general', label: 'Dados Institucionais & Cultura', icon: Building2 },
          { id: 'tone', label: 'Persona, Tom de Voz & IA', icon: Bot },
          { id: 'policies', label: 'Políticas, SLAs & Compliance', icon: ShieldAlert },
          { id: 'delivery', label: 'Logística & Operações', icon: MapPin },
          { id: 'menu', label: 'Portfólio & Catálogo', icon: UtensilsCrossed },
          { id: 'promotions', label: 'Promoções & Ofertas', icon: Award },
          { id: 'payments', label: 'Diretrizes Financeiras & Pagamento', icon: CreditCard },
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
              Identificação Corporativa e Canais Oficiais
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" /> Razão Social / Nome Fantasia
                </label>
                <input
                  type="text"
                  value={settings.company_name || ''}
                  onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
                  placeholder="Ex: Dominus Labs Tecnologia e Inovação S/A"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-400" /> Inscrição CNPJ / Documento Fiscal
                </label>
                <input
                  type="text"
                  value={settings.cnpj_cpf || ''}
                  onChange={(e) => setSettings({ ...settings, cnpj_cpf: e.target.value })}
                  placeholder="Ex: 12.345.678/0001-90"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-slate-400" /> Telefone / WhatsApp Corporativo
                </label>
                <input
                  type="text"
                  value={settings.phone || ''}
                  onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
                  placeholder="Ex: +55 (11) 4003-8800"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" /> E-mail Institucional de Atendimento
                </label>
                <input
                  type="email"
                  value={settings.email || ''}
                  onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                  placeholder="Ex: governanca@dominuslabs.com.br"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" /> Endereço da Sede Corporativa
                </label>
                <input
                  type="text"
                  value={settings.address || ''}
                  onChange={(e) => setSettings({ ...settings, address: e.target.value })}
                  placeholder="Ex: Av. das Nações Unidas, 12901 - Torre Leste, 18º andar - Brooklin, São Paulo/SP"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" /> Expediente / Janela Operacional
                </label>
                <input
                  type="text"
                  value={settings.business_hours || ''}
                  onChange={(e) => setSettings({ ...settings, business_hours: e.target.value })}
                  placeholder="Ex: Segunda a Sexta-feira: 08:00 às 18:00 (Horário de Brasília - UTC-3)"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5 text-slate-400" /> Missão, Visão e Diretrizes de Valor
                </label>
                <textarea
                  rows={4}
                  value={settings.values_mission || ''}
                  onChange={(e) => setSettings({ ...settings, values_mission: e.target.value })}
                  placeholder="Descreva a declaração de missão, tese de mercado e valores organizacionais que orientam o posicionamento estratégico..."
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
              Diretrizes de Persona & Engenharia de Prompt para IA
            </h2>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
                Estilo de Comunicação Predominante do Agente Virtual
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
                <Sparkles className="w-3.5 h-3.5 text-purple-600" /> Regras de Negócio e Restrições de Atendimento Automático
              </label>
              <p className="text-xs text-slate-500 mb-2">
                Instruções determinísticas aplicadas à camada de raciocínio da IA (System Instructions, limites de autoridade, diretrizes de transbordo humano).
              </p>
              <textarea
                rows={6}
                value={settings.custom_instructions || ''}
                onChange={(e) => setSettings({ ...settings, custom_instructions: e.target.value })}
                placeholder="Exemplo: Priorize a qualificação de BANT antes de agendar uma reunião. Não conceda descontos acima de 5% sem transbordo para um executivo de contas. Mantenha conformidade estrita com as normas da LGPD."
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
              Termos de Contrato, SLAs e Políticas Operacionais
            </h2>

            <div className="space-y-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Política de Garantia, Troca e Rescisão Contratual
                </label>
                <textarea
                  rows={4}
                  value={settings.exchange_policy || ''}
                  onChange={(e) => setSettings({ ...settings, exchange_policy: e.target.value })}
                  placeholder="Especifique os prazos normativos de garantia, SLA de substituição de componentes e cláusulas de rescisão..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Política de Logística, Entregas e Acordo de Nível de Serviço (SLA)
                </label>
                <textarea
                  rows={4}
                  value={settings.delivery_policy || ''}
                  onChange={(e) => setSettings({ ...settings, delivery_policy: e.target.value })}
                  placeholder="Detalhamento sobre prazos de implantação, despacho de insumos ou SLAs de disponibilização em nuvem..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Termos de Uso, Licenciamento e Conformidade LGPD
                </label>
                <textarea
                  rows={4}
                  value={settings.terms_of_service || ''}
                  onChange={(e) => setSettings({ ...settings, terms_of_service: e.target.value })}
                  placeholder="Resumo executivo dos termos de prestação de serviços, propriedade intelectual e governança de dados..."
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab Delivery */}
        {activeTab === 'delivery' && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-purple-600" />
                Regras de Logística e Delivery
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Configure os parâmetros de entrega, área de atuação e valores mínimos. Especialmente importante para restaurantes, lanchonetes e e-commerces locais.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Modelo de Cobrança de Entrega
                </label>
                <select
                  value={settings.delivery_fee_type || 'Fixo'}
                  onChange={(e) => setSettings({ ...settings, delivery_fee_type: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm bg-white"
                >
                  <option value="Fixo">Valor Fixo</option>
                  <option value="Por KM">Por KM (Distância)</option>
                  <option value="Por Raio">Por Raio</option>
                  <option value="Grátis">Entrega Grátis</option>
                  <option value="Não se aplica">Não se aplica (Retirada/Serviço)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Valor Base / Taxa (R$)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">R$</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={settings.delivery_fee_value || 0}
                    onChange={(e) => setSettings({ ...settings, delivery_fee_value: parseFloat(e.target.value) || 0 })}
                    placeholder="0.00"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Raio Máximo de Entrega (KM)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">Km</span>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={settings.delivery_radius_km || 0}
                    onChange={(e) => setSettings({ ...settings, delivery_radius_km: parseFloat(e.target.value) || 0 })}
                    placeholder="Ex: 5"
                    className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Valor Mínimo do Pedido (R$)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold">R$</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={settings.minimum_order_value || 0}
                    onChange={(e) => setSettings({ ...settings, minimum_order_value: parseFloat(e.target.value) || 0 })}
                    placeholder="Ex: 30.00"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 flex items-center gap-1.5">
                  Tempo Médio de Preparo / Envio (Minutos)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-semibold"><Clock className="w-4 h-4"/></span>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={settings.preparation_time_minutes || 0}
                    onChange={(e) => setSettings({ ...settings, preparation_time_minutes: parseInt(e.target.value) || 0 })}
                    placeholder="Ex: 45"
                    className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
        {activeTab === 'menu' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <UtensilsCrossed className="w-5 h-5 text-purple-600" />
                  Portfólio de Soluções & Catálogo de Produtos
                </h2>
                <p className="text-xs text-slate-500">
                  Gerenciamento da grade comercial para referência automática do agente de IA e equipe de vendas.
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
                Cadastrar Solução
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
                        <span className="font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200 text-xs whitespace-nowrap">
                          R$ {Number(item.price || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </span>
                      </div>

                      {item.category && (
                        <span className="inline-block text-[11px] font-semibold text-slate-600 bg-slate-200/60 px-2.5 py-0.5 rounded-full mb-2">
                          {item.category}
                        </span>
                      )}

                      {item.description && (
                        <p className="text-xs text-slate-600 line-clamp-2">{item.description}</p>
                      )}
                    </div>

                    <div className="flex items-center justify-between border-t border-slate-200/60 pt-2 text-xs">
                      <span className={`font-semibold ${item.available ? 'text-emerald-600' : 'text-rose-500'}`}>
                        {item.available ? '● Ativo para Oferta' : '○ Indisponível no Momento'}
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
                <p className="text-sm font-semibold text-slate-600">Nenhum item homologado no portfólio</p>
                <p className="text-xs text-slate-400 mt-1">Utilize o botão superior para cadastrar novas ofertas corporativas.</p>
              </div>
            )}
          </div>
        )}

        {/* Tab Promoções */}
        {activeTab === 'promotions' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <Award className="w-5 h-5 text-purple-600" />
                  Campanhas & Promoções Ativas
                </h2>
                <p className="text-xs text-slate-500">
                  Cadastre descontos e ofertas para o bot usar durante o atendimento.
                </p>
              </div>
              <button
                onClick={() => {
                  setNewPromo({ name: '', discount_type: 'percentage', discount_value: 0, valid_until: '', description: '', active: true });
                  setEditingPromoIndex(null);
                  setIsPromoModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 bg-purple-100 hover:bg-purple-200 text-purple-800 font-semibold text-xs px-3.5 py-2 rounded-xl transition-all cursor-pointer self-start sm:self-auto"
              >
                <Plus className="w-4 h-4" />
                Nova Promoção
              </button>
            </div>

            {settings.promotions && settings.promotions.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {settings.promotions.map((promo, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-xl border ${promo.active ? 'border-purple-200 bg-purple-50/30' : 'border-slate-200 bg-slate-50 opacity-60'} flex flex-col justify-between gap-3 transition-all`}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className="font-bold text-slate-900 text-base">{promo.name}</span>
                        <span className="font-bold text-purple-700 bg-purple-100 px-2.5 py-0.5 rounded-md border border-purple-200 text-xs whitespace-nowrap">
                          {promo.discount_type === 'percentage' ? `${promo.discount_value}% OFF` : `R$ ${promo.discount_value} OFF`}
                        </span>
                      </div>
                      {promo.valid_until && (
                        <p className="text-xs text-slate-500 mb-2 font-medium">Válido até: {promo.valid_until}</p>
                      )}
                      {promo.description && (
                        <p className="text-xs text-slate-600 line-clamp-2">{promo.description}</p>
                      )}
                    </div>
                    <div className="flex items-center justify-between mt-2 pt-3 border-t border-slate-200/60">
                      <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${promo.active ? 'bg-emerald-500' : 'bg-slate-400'}`}></div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          {promo.active ? 'Ativa' : 'Inativa'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditPromo(index)}
                          className="text-xs font-semibold text-purple-600 hover:text-purple-800 transition-colors cursor-pointer"
                        >
                          Editar
                        </button>
                        <span className="text-slate-300">|</span>
                        <button
                          onClick={() => handleDeletePromo(index)}
                          className="text-xs font-semibold text-rose-500 hover:text-rose-700 transition-colors cursor-pointer"
                        >
                          Excluir
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 px-4 border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
                <div className="bg-white w-12 h-12 rounded-full shadow-sm flex items-center justify-center mx-auto mb-3">
                  <Award className="w-5 h-5 text-slate-400" />
                </div>
                <h3 className="text-sm font-bold text-slate-700 mb-1">Nenhuma promoção ativa</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Crie promoções e cupons para que sua IA possa oferecer benefícios aos clientes e aumentar conversões.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Formas de Pagamento Aceitas */}
        {activeTab === 'payments' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <CreditCard className="w-5 h-5 text-purple-600" />
              Meios de Pagamento Homologados & Faturamento
            </h2>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
                Modalidades Financeiras Habilitadas
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
                <DollarSign className="w-3.5 h-3.5 text-slate-400" /> Chaves Pix, Condições Comerciais e Faturamento
              </label>
              <textarea
                rows={4}
                value={settings.payment_notes || ''}
                onChange={(e) => setSettings({ ...settings, payment_notes: e.target.value })}
                placeholder="Exemplo: Chave Pix CNPJ: 12.345.678/0001-90 (Dominus Labs). Faturamento disponível para PJ sob consulta de crédito (15/30 dias)."
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
              {editingIndex !== null ? 'Editar Item do Portfólio' : 'Cadastrar Nova Solução / Item'}
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Denominação do Item / Solução *</label>
                <input
                  type="text"
                  value={newItem.name}
                  onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                  placeholder="Ex: Licença Plataforma Agente IA Enterprise"
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Categoria Comercial</label>
                  <input
                    type="text"
                    value={newItem.category || ''}
                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                    placeholder="Ex: SaaS / Licenciamento"
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Valor Unitário (R$)</label>
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
                <label className="block text-xs font-bold text-slate-600 mb-1">Descrição / Escopo Técnico</label>
                <textarea
                  rows={3}
                  value={newItem.description || ''}
                  onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                  placeholder="Resumo executivo do escopo..."
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
                Solução homologada para comercialização imediata
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
                Homologar Solução
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Modal de Promoções */}
      {isPromoModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              {editingPromoIndex !== null ? 'Editar Promoção' : 'Nova Promoção'}
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Nome da Campanha / Cupom *</label>
                <input
                  type="text"
                  value={newPromo.name}
                  onChange={(e) => setNewPromo({ ...newPromo, name: e.target.value })}
                  placeholder="Ex: BLACKFRIDAY20"
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Tipo de Desconto</label>
                  <select
                    value={newPromo.discount_type}
                    onChange={(e) => setNewPromo({ ...newPromo, discount_type: e.target.value as 'percentage' | 'fixed' })}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500 bg-white"
                  >
                    <option value="percentage">Porcentagem (%)</option>
                    <option value="fixed">Valor Fixo (R$)</option>
                  </select>
                </div>
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
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Válido até (Opcional)</label>
                <input
                  type="date"
                  value={newPromo.valid_until || ''}
                  onChange={(e) => setNewPromo({ ...newPromo, valid_until: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Regras / Descrição</label>
                <textarea
                  rows={2}
                  value={newPromo.description || ''}
                  onChange={(e) => setNewPromo({ ...newPromo, description: e.target.value })}
                  placeholder="Ex: Válido apenas para primeira compra acima de R$50..."
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm outline-none focus:border-purple-500"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={newPromo.active}
                  onChange={(e) => setNewPromo({ ...newPromo, active: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Promoção Ativa
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setIsPromoModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:bg-slate-100 cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleSavePromo}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white shadow-sm cursor-pointer"
              >
                Salvar Promoção
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
