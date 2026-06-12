import { useState, useEffect } from 'react';
import { fetchTasks, createTask, updateTask } from '../services/api';
import { CheckCircle2, Circle, Plus, Loader2 } from 'lucide-react';

interface Task {
  id: number;
  name: string;
  description?: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'DONE';
  completed_by_github?: boolean;
}

interface TaskChecklistProps {
  projectId: string | number;
  admin: boolean;
  onTasksUpdated?: () => void;
}

export default function TaskChecklist({ projectId, admin, onTasksUpdated }: TaskChecklistProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newTaskName, setNewTaskName] = useState('');
  const [addingTask, setAddingTask] = useState(false);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const data = await fetchTasks(projectId);
      setTasks(data);
      setError('');
    } catch (err: any) {
      console.error(err);
      setError('Erro ao carregar tarefas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId && isNaN(Number(projectId)) === false) {
      loadTasks();
    } else {
      setLoading(false);
    }
  }, [projectId]);

  const toggleTask = async (task: Task) => {
    if (!admin || task.completed_by_github) return;
    const newStatus = task.status === 'DONE' ? 'PENDING' : 'DONE';
    try {
      // Optimistic UI update
      setTasks(tasks.map(t => t.id === task.id ? { ...t, status: newStatus } : t));

      await updateTask(task.id, { status: newStatus });
      if (onTasksUpdated) onTasksUpdated();
    } catch (err) {
      console.error(err);
      // Revert optimistic update
      setTasks(tasks.map(t => t.id === task.id ? { ...t, status: task.status } : t));
    }
  };

  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskName.trim() || !projectId) return;

    try {
      setAddingTask(true);
      const created = await createTask(projectId, {
        name: newTaskName.trim(),
        status: 'PENDING',
      });
      setTasks([...tasks, created]);
      setNewTaskName('');
      if (onTasksUpdated) onTasksUpdated();
    } catch (err) {
      console.error(err);
      setError('Erro ao criar tarefa.');
    } finally {
      setAddingTask(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-violet-600 text-sm py-4">
        <Loader2 className="w-4 h-4 animate-spin" />
        Carregando checklist...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-xs text-rose-500 font-medium">{error}</p>}

      {tasks.length === 0 ? (
        <p className="text-sm text-slate-400 italic">Nenhuma tarefa cadastrada.</p>
      ) : (
        <ul className="space-y-2.5">
          {tasks.map(task => {
            const isDone = task.status === 'DONE';
            const isGithubDone = !!task.completed_by_github;
            return (
              <li
                key={task.id}
                onClick={() => !isGithubDone && toggleTask(task)}
                className={`flex items-start gap-3 p-3 rounded-xl border transition-all duration-200 select-none ${
                  admin && !isGithubDone ? 'cursor-pointer hover:bg-violet-50/50' : 'cursor-not-allowed'
                } ${
                  isDone
                    ? 'bg-slate-50/80 border-slate-200/50 text-slate-400'
                    : 'bg-white border-violet-100/50 text-slate-700 shadow-sm'
                }`}
                title={isGithubDone ? "Esta tarefa foi concluída via commit no GitHub e não pode ser alterada." : ""}
              >
                <div className="mt-0.5">
                  {isDone ? (
                    <CheckCircle2 className={`w-5 h-5 ${isGithubDone ? 'text-violet-500 fill-violet-50' : 'text-emerald-500 fill-emerald-50'}`} />
                  ) : (
                    <Circle className={`w-5 h-5 ${admin ? 'text-violet-300 hover:text-violet-600' : 'text-slate-300'}`} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className={`text-sm font-medium break-words ${isDone ? 'line-through' : ''}`}>
                    {task.name}
                  </span>
                  {isGithubDone && (
                    <span className="block text-[10px] font-bold text-violet-600 mt-0.5 animate-pulse">
                      ✓ Concluído via GitHub
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {admin && (
        <form onSubmit={handleAddTask} className="flex gap-2 mt-2">
          <input
            type="text"
            placeholder="Nova tarefa..."
            value={newTaskName}
            onChange={e => setNewTaskName(e.target.value)}
            className="flex-1 text-sm bg-white/80 border border-violet-100/60 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
            disabled={addingTask}
          />
          <button
            type="submit"
            className="bg-violet-600 hover:bg-violet-700 text-white rounded-xl p-2 flex items-center justify-center transition-colors disabled:opacity-50"
            disabled={addingTask}
          >
            {addingTask ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
          </button>
        </form>
      )}
    </div>
  );
}