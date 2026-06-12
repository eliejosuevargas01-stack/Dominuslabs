export default function ProgressBar({ progress }: { progress: number }) {
  const clampedProgress = Math.min(100, Math.max(0, Math.round(progress)));

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1.5 text-xs font-semibold text-slate-500">
        <span>Progresso Geral</span>
        <span className="font-display text-violet-800 bg-violet-100/80 px-2 py-0.5 rounded-full">{clampedProgress}% Concluído</span>
      </div>
      <div className="w-full bg-slate-100/80 border border-slate-200/50 rounded-full h-3.5 overflow-hidden p-[2px]">
        <div
          className="bg-gradient-to-r from-violet-600 via-indigo-500 to-emerald-500 h-full rounded-full transition-all duration-700 cubic-bezier(0.4, 0, 0.2, 1) relative shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]"
          style={{ width: `${clampedProgress}%` }}
        >
          <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)] bg-[length:1rem_1rem] animate-[move-stripes_1s_linear_infinite]"></div>
        </div>
      </div>

      <style>{`
        @keyframes move-stripes {
          from { background-position: 0 0; }
          to { background-position: 1rem 0; }
        }
      `}</style>
    </div>
  );
}