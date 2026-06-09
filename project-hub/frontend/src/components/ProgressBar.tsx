export default function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-4 dark:bg-gray-700 overflow-hidden">
      <div
        className="bg-blue-600 h-4 rounded-full transition-all duration-500 ease-in-out"
        style={{ width: `${progress}%` }}
      ></div>
      <div className="text-xs text-center mt-1 font-bold">{progress}%</div>
    </div>
  );
}