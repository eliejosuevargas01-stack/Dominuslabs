import { useState } from 'react';

export default function TaskChecklist({ projectId: _projectId, admin }: { projectId: string | number, admin: boolean }) {
  // Stub
  const [tasks, setTasks] = useState([
    { id: 1, name: "Design no Figma", status: "DONE" },
    { id: 2, name: "Desenvolvimento Frontend", status: "IN_PROGRESS" },
    { id: 3, name: "Deploy", status: "PENDING" }
  ]);

  const toggleTask = (id: number) => {
    if (!admin) return;
    setTasks(tasks.map(t => {
      if (t.id === id) {
        return { ...t, status: t.status === "DONE" ? "PENDING" : "DONE" };
      }
      return t;
    }));
  };

  return (
    <ul className="space-y-2">
      {tasks.map(task => (
        <li key={task.id} className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={task.status === "DONE"}
            onChange={() => toggleTask(task.id)}
            disabled={!admin}
            className="w-4 h-4"
          />
          <span className={task.status === "DONE" ? "line-through text-gray-500" : ""}>
            {task.name}
          </span>
        </li>
      ))}
    </ul>
  );
}