import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import ProgressBar from '../components/ProgressBar';
import TaskChecklist from '../components/TaskChecklist';

export default function PublicProjectView() {
  const { public_token } = useParams();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    // Stub
    setData({
      project: {
        name: "Clínica Odontológica Marcos",
        client_name: "Marcos",
        status: "IN_PROGRESS",
        deploy_url: "https://clinica.netlify.app"
      },
      progress: 60,
      commits: [{ id: 1, message: "feat: hero section", commit_date: "2023-10-27" }],
      deploys: [{ id: 1, status: "SUCCESS", deploy_date: "2023-10-27" }]
    });
  }, [public_token]);

  if (!data) return <div>Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 mt-10 bg-white shadow rounded border">
      <h1 className="text-3xl font-bold mb-2">{data.project.name}</h1>
      <p className="text-gray-600 mb-6">Cliente: {data.project.client_name} | Status: {data.project.status}</p>

      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Progresso do Projeto</h2>
        <ProgressBar progress={data.progress} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">Tarefas</h2>
          {/* Read only view */}
          <TaskChecklist projectId={public_token || "unknown"} admin={false} />
        </div>

        <div>
          <div className="mb-4">
            <h2 className="text-xl font-semibold mb-2">Últimos Commits</h2>
            <ul className="list-disc pl-5 text-sm">
              {data.commits.map((c: any) => <li key={c.id}>{c.message}</li>)}
            </ul>
          </div>

          <div className="mb-4">
            <h2 className="text-xl font-semibold mb-2">Últimos Deploys</h2>
            <ul className="list-disc pl-5 text-sm">
              {data.deploys.map((d: any) => <li key={d.id}>{d.status} - {d.deploy_date}</li>)}
            </ul>
          </div>

          {data.project.deploy_url && (
            <div className="mt-6">
              <a href={data.project.deploy_url} target="_blank" className="bg-green-600 text-white px-4 py-2 rounded inline-block">
                Visualizar Preview do Projeto
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}