/**
 * Documentation-Driven Testing:
 * O comportamento esperado para CampaignsWizardView.tsx:
 * - Botões (Avançar/Voltar): Alternam os steps do wizard (estado numérico do step atual).
 * - Inputs (Nome da campanha): Devem ser validados antes de permitir o avanço.
 * - O botão final dispara o envio da campanha e exibe estado de loading/toast de sucesso.
 */

import { useState } from 'react';
import { toast } from 'sonner';
import {
  Megaphone,
  Users,
  Sparkles,
  Send,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  Bot
} from 'lucide-react';

export interface AudienceSegment {
  id: string;
  label: string;
  description: string;
  totalLeads: number;
}

interface CampaignsWizardProps {
  segments?: AudienceSegment[];
  loading?: boolean;
  onGenerateMessage?: (segmentId: string, prompt: string) => Promise<string>;
  onDispatchCampaign?: (segmentId: string, prompt: string, message: string) => Promise<void>;
}

export default function CampaignsWizardView({
  segments = [],
  onGenerateMessage,
  onDispatchCampaign
}: CampaignsWizardProps) {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);

  // Form states
  const [selectedSegmentId, setSelectedSegmentId] = useState<string>('');
  const [promptInput, setPromptInput] = useState<string>('');
  const [generatedMessage, setGeneratedMessage] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);

  // Step 1 -> Step 2
  const handleSelectSegment = (id: string) => {
    setSelectedSegmentId(id);
  };

  // Step 2 -> Step 3
  const handleGeneratePreview = async () => {
    if (!promptInput.trim()) return;
    setIsGenerating(true);
    try {
      if (onGenerateMessage) {
        // Conectar endpoint POST /api/v1/campaigns/generate
        const resultText = await onGenerateMessage(selectedSegmentId, promptInput);
        setGeneratedMessage(resultText);
      } else {
        // Placeholder até o mapeamento da API
        setGeneratedMessage(`Olá! 👋 Preparamos uma oferta exclusiva para você. Com base na sua última visita, liberamos um cupom especial de desconto. Responda SIM para resgatar!`);
      }
      setCurrentStep(3);
    } catch (err) {
      console.error("Erro ao gerar mensagem:", err); toast.error("Ocorreu um erro na operacao.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Final Dispatch
  const handleDispatch = async () => {
    setIsDispatching(true);
    try {
      if (onDispatchCampaign) {
        // Conectar endpoint POST /api/v1/campaigns/dispatch
        await onDispatchCampaign(selectedSegmentId, promptInput, generatedMessage);
      }
    } catch (err) {
      console.error("Erro ao disparar campanha:", err); toast.error("Ocorreu um erro na operacao.");
    } finally {
      setIsDispatching(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4   p-6 rounded-2xl border border-zinc-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-display font-extrabold text-zinc-900 flex items-center gap-2.5">
            <Megaphone className="w-7 h-7 text-purple-600" />
            Campanhas Inteligentes & CRM Ativo
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Assistente em 3 passos para criação e disparo segmentado de promoções personalizadas via IA.
          </p>
        </div>
      </div>

      {/* Progress Steps Header */}
      <div className="flex items-center justify-between   p-4 rounded-2xl border border-zinc-200 shadow-sm">
        {[
          { step: 1, label: '1. Público-Alvo', icon: Users },
          { step: 2, label: '2. Instrução IA', icon: Sparkles },
          { step: 3, label: '3. Prévia & Disparo', icon: Send },
        ].map((item) => {
          const isActive = currentStep === item.step;
          const isDone = currentStep > item.step;
          const Icon = item.icon;

          return (
            <div
              key={item.step}
              className={`flex items-center gap-2 font-bold text-xs transition-all ${
                isActive
                  ? 'text-purple-700 bg-purple-50 px-3 py-1.5 rounded-xl border border-purple-200'
                  : isDone
                  ? 'text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200'
                  : 'text-zinc-400 px-3 py-1.5'
              }`}
            >
              {isDone ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Icon className="w-4 h-4" />}
              <span>{item.label}</span>
            </div>
          );
        })}
      </div>

      {/* Step Content Container */}
      <div className="  rounded-2xl border border-zinc-200 shadow-sm p-6 sm:p-8">
        {/* Step 1: Seleção de Público */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="border-b border-zinc-100 pb-3">
              <h2 className="text-lg font-bold text-zinc-800 flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-600" />
                Passo 1: Seleção da Audiência e Segmento
              </h2>
              <p className="text-xs text-zinc-500">
                Escolha o perfil de clientes que receberá a campanha ativa.
              </p>
            </div>

            {segments.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {segments.map((seg) => {
                  const isSelected = selectedSegmentId === seg.id;
                  return (
                    <div
                      key={seg.id}
                      onClick={() => handleSelectSegment(seg.id)}
                      className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'border-purple-600 bg-purple-50/60 shadow-md ring-2 ring-purple-200'
                          : 'border-zinc-200 hover:border-purple-300 hover:bg-zinc-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-zinc-900 text-sm">{seg.label}</span>
                        <span className="text-xs font-bold text-purple-700 bg-purple-100 px-2.5 py-0.5 rounded-full">
                          {seg.totalLeads} contatos
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 leading-relaxed">{seg.description}</p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-12 text-center text-zinc-400 bg-zinc-50 rounded-2xl border border-dashed border-zinc-200">
                <Users className="w-8 h-8 text-zinc-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-zinc-500">Aguardando lista de segmentos da API...</p>
                {/* Conectar via GET /api/v1/campaigns/segments */}
              </div>
            )}

            <div className="flex justify-end pt-4">
              <button
                disabled={!selectedSegmentId}
                onClick={() => setCurrentStep(2)}
                className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs px-6 py-2.5 rounded-xl shadow-md transition-all disabled:opacity-50 cursor-pointer"
              >
                Avançar para Instrução IA
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Instrução para a IA */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="border-b border-zinc-100 pb-3">
              <h2 className="text-lg font-bold text-zinc-800 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-600" />
                Passo 2: Instrução e Objetivo da Campanha
              </h2>
              <p className="text-xs text-zinc-500">
                Escreva em linguagem natural o que a IA deve oferecer aos clientes selecionados.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-zinc-600 mb-2">
                Prompt / Instrução de Disparo
              </label>
              <textarea
                rows={6}
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                placeholder="Exemplo: Ofereça 15% de desconto para compras acima de R$ 50 válidos somente até este domingo. Use um tom entusiasmado e inclua um gancho para responderem a mensagem."
                className="w-full px-4 py-3 rounded-2xl border border-zinc-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none text-sm transition-all"
              />
            </div>

            <div className="flex items-center justify-between pt-4">
              <button
                onClick={() => setCurrentStep(1)}
                className="inline-flex items-center gap-2 text-zinc-600 hover:text-zinc-900 font-semibold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                Voltar
              </button>

              <button
                disabled={!promptInput.trim() || isGenerating}
                onClick={handleGeneratePreview}
                className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs px-6 py-2.5 rounded-xl shadow-md transition-all disabled:opacity-50 cursor-pointer"
              >
                {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                {isGenerating ? 'Sintetizando...' : 'Gerar Prévia com IA'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Prévia no Celular & Disparo */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div className="border-b border-zinc-100 pb-3">
              <h2 className="text-lg font-bold text-zinc-800 flex items-center gap-2">
                <Send className="w-5 h-5 text-purple-600" />
                Passo 3: Homologação da Prévia e Disparo
              </h2>
              <p className="text-xs text-zinc-500">
                Verifique a mensagem simulada no ambiente mobile antes da execução da campanha.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              {/* Smartphone Mockup UI */}
              <div className="mx-auto w-full max-w-[280px] bg-zinc-900 p-4 rounded-[40px] shadow-2xl border-4 border-zinc-800 space-y-3">
                <div className="w-20 h-4 bg-zinc-800 rounded-full mx-auto mb-2" />

                <div className="bg-emerald-950/40 p-3 rounded-2xl min-h-[320px] flex flex-col justify-end space-y-2 border border-emerald-900/30">
                  <div className="bg-emerald-800/80 text-white p-3.5 rounded-2xl text-xs leading-relaxed rounded-tr-none shadow-md">
                    {generatedMessage || 'Aguardando síntese da IA...'}
                  </div>
                  <span className="text-[9px] text-emerald-400/80 text-right block">
                    Agora • WhatsApp Business
                  </span>
                </div>
              </div>

              {/* Action Sidebar Panel */}
              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-purple-50/60 border border-zinc-200 text-xs text-purple-900 space-y-1">
                  <span className="font-bold">Resumo do Lançamento:</span>
                  <p className="text-zinc-600">Segmento Selecionado: ID {selectedSegmentId || 'Geral'}</p>
                </div>

                <div className="space-y-2">
                  <label className="block text-xs font-bold text-zinc-700">Ajustar Redação Gerada (Opcional):</label>
                  <textarea
                    rows={4}
                    value={generatedMessage}
                    onChange={(e) => setGeneratedMessage(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 text-xs outline-none focus:border-purple-500"
                  />
                </div>

                <button
                  disabled={isDispatching || !generatedMessage.trim()}
                  onClick={handleDispatch}
                  className="w-full inline-flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-sm py-3 rounded-xl shadow-lg shadow-emerald-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isDispatching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {isDispatching ? 'Disparando Lote...' : 'Aprovar e Disparar Campanha'}
                </button>
              </div>
            </div>

            <div className="flex justify-start pt-4 border-t border-zinc-100">
              <button
                onClick={() => setCurrentStep(2)}
                className="inline-flex items-center gap-2 text-zinc-600 hover:text-zinc-900 font-semibold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                Refazer Prompt
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
