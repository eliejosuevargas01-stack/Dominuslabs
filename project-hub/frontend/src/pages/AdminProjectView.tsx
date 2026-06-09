import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import ProgressBar from '../components/ProgressBar';
import TaskChecklist from '../components/TaskChecklist';

export default function AdminProjectView() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);

  useEffect(() => {
    // Stub
    setProject({
      id,
      name: "Clínica Odontológica Marcos",
      client_name: "Marcos",
      value: 500,
      description: "Landing page para clínica.",
      github_url: "https://github.com/user/repo",
      deploy_url: "https://clinica.netlify.app",
      status: "IN_PROGRESS",
      public_token: "abc-123"
    });
  }, [id]);

  if (!project) return <div>Loading...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Gerenciar Projeto: {project.name}</h1>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-4 shadow rounded border">
          <h2 className="text-xl font-semibold mb-2">Detalhes</h2>
          <div className="space-y-2">
            <p><strong>Cliente:</strong> {project.client_name}</p>
            <p><strong>Valor:</strong> R$ {project.value}</p>
            <p><strong>Descrição:</strong> {project.description}</p>
            <p><strong>GitHub:</strong> <a href={project.github_url} className="text-blue-600" target="_blank">{project.github_url}</a></p>
            <p><strong>Deploy:</strong> <a href={project.deploy_url} className="text-blue-600" target="_blank">{project.deploy_url}</a></p>
            <p><strong>Link Público:</strong> /project/{project.public_token}</p>
          </div>
          <button className="mt-4 bg-gray-200 px-4 py-2 rounded">Editar Detalhes</button>
        </div>

        <div className="bg-white p-4 shadow rounded border">
          <h2 className="text-xl font-semibold mb-2">Progresso</h2>
          <ProgressBar progress={60} />

          <div className="mt-6">
            <h3 className="font-semibold mb-2">Tarefas</h3>
            <TaskChecklist projectId={project.id} admin={true} />
          </div>
        </div>

        <div className="bg-white p-4 shadow rounded border">
          <h2 className="text-xl font-semibold mb-2">Arquivos (Assets)</h2>
          <button className="bg-blue-600 text-white px-4 py-2 rounded">Upload Arquivo</button>
          <ul className="mt-4 list-disc pl-5">
            <li>logo.png</li>
            <li>briefing.pdf</li>
          </ul>
        </div>

        <div className="bg-white p-4 shadow rounded border">
          <h2 className="text-xl font-semibold mb-2">Histórico (Webhooks)</h2>
          <h3 className="font-semibold">Últimos Commits</h3>
          <ul className="list-disc pl-5 mb-4 text-sm">
            <li>fix: header styling (hash123)</li>
          </ul>
          <h3 className="font-semibold">Últimos Deploys</h3>
          <ul className="list-disc pl-5 text-sm">
            <li>Deploy Netlify - SUCCESS (27/10/2023)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}