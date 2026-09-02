/**
 * Documentation-Driven Testing:
 * O comportamento esperado para AutomationsView.tsx:
 * - Botão 'Nova Automação': Inicia o fluxo de construção.
 * - Toggles: Ativam e desativam os fluxos imediatamente via API.
 * - Toasts notificam o sucesso/erro da operação.
 */

import { useState } from 'react';
import {
  Workflow,
  Power,
  ShieldCheck,
  Loader2
} from 'lucide-react';

export interface BusinessRule {
  id: string;
  key: string;
  titulo: string;
  descricao: string;
  ativo: boolean;
  categoria?: 'ATENDIMENTO' | 'VENDAS' | 'EXPEDICAO' | 'NOTIFICACAO';
}

interface AutomationsViewProps {
  rules?: BusinessRule[];
  loading?: boolean;
  onToggleRule?: (ruleId: string, novoStatus: boolean) => Promise<void>;
}

export default function AutomationsView({
  rules = [],
  loading = false,
  onToggleRule
}: AutomationsViewProps) {
  const [localRules, setLocalRules] = useState<BusinessRule[]>(rules);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const handleToggle = async (rule: BusinessRule) => {
    const nextStatus = !rule.ativo;
    setUpdatingId(rule.id);

    // Optimistic Update
    setLocalRules((prev) =>
      prev.map((r) => (r.id === rule.id ? { ...r, ativo: nextStatus } : r))
    );

    try {
      if (onToggleRule) {
        // Conectar endpoint PUT /api/v1/automations/rules/:id
        await onToggleRule(rule.id, nextStatus);
      }
    } catch (err) {
      // Revert in case of failure
      setLocalRules((prev) =>
        prev.map((r) => (r.id === rule.id ? { ...r, ativo: rule.ativo } : r))
      );
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 surface-card p-6">
        <div>
          <h1 className="text-2xl font-display font-extrabold text-zinc-900 flex items-center gap-2.5">
            <Workflow className="w-7 h-7 text-purple-600" />
            Automações & Regras de Negócio
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Gatilhos inteligentes e motor de decisão autônomo para operar o atendimento sem intervenção manual.
          </p>
        </div>
      </div>

      {/* Rules List Container */}
      <div className="  rounded-2xl border border-zinc-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-zinc-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-purple-600" />
              Gatilhos e Políticas de Operação
            </h2>
            <p className="text-xs text-zinc-500">
              Ative ou desative cada regra individualmente. As alterações surtem efeito imediato no robô.
            </p>
          </div>
        </div>

        <div className="divide-y divide-zinc-100">
          {localRules.length > 0 ? (
            localRules.map((rule) => {
              const isBusy = updatingId === rule.id;
              return (
                <div
                  key={rule.id}
                  className="p-6 flex items-center justify-between gap-4 hover: transition-colors"
                >
                  <div className="space-y-1 max-w-3xl">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-zinc-900 text-sm">{rule.titulo}</span>
                      {rule.categoria && (
                        <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                          {rule.categoria}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-500 leading-relaxed">{rule.descricao}</p>
                  </div>

                  {/* Switch Toggle UI */}
                  <button
                    onClick={() => handleToggle(rule)}
                    disabled={isBusy || loading}
                    className={`relative inline-flex h-7 w-12 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none disabled:opacity-50 ${
                      rule.ativo ? 'bg-purple-600' : 'bg-zinc-300'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out flex items-center justify-center ${
                        rule.ativo ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    >
                      {isBusy ? (
                        <Loader2 className="w-3 h-3 animate-spin text-purple-600" />
                      ) : (
                        <Power className={`w-3 h-3 ${rule.ativo ? 'text-purple-600' : 'text-zinc-400'}`} />
                      )}
                    </span>
                  </button>
                </div>
              );
            })
          ) : (
            <div className="py-16 text-center text-zinc-400">
              <Workflow className="w-10 h-10 text-zinc-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-zinc-600">Nenhuma regra de automação mapeada.</p>
              <p className="text-xs text-zinc-400 mt-1">Conecte o array de regras vindo do back-end (GET /api/v1/automations/rules).</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
