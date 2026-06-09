import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function AdminDashboard() {
  const [projects, setProjects] = useState<any[]>([]);

  useEffect(() => {
    // In a real app, fetch from API
    // fetch('/api/v1/projects/').then(res => res.json()).then(setProjects);
    setProjects([
      { id: 1, name: "Clínica Odontológica Marcos", client_name: "Marcos", value: 500, status: "IN_PROGRESS", progress: 60, last_deploy_date: "2023-10-27" }
    ]);
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Dashboard Admin</h1>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 shadow rounded border">
          <p className="text-gray-500">Total Projetos</p>
          <p className="text-xl font-bold">{projects.length}</p>
        </div>
        <div className="bg-white p-4 shadow rounded border">
          <p className="text-gray-500">Projetos Ativos</p>
          <p className="text-xl font-bold">{projects.filter(p => p.status === 'IN_PROGRESS').length}</p>
        </div>
        <div className="bg-white p-4 shadow rounded border">
          <p className="text-gray-500">Projetos Concluídos</p>
          <p className="text-xl font-bold">{projects.filter(p => p.status === 'DELIVERED').length}</p>
        </div>
        <div className="bg-white p-4 shadow rounded border">
          <p className="text-gray-500">Receita Total</p>
          <p className="text-xl font-bold">R$ {projects.reduce((acc, p) => acc + p.value, 0)}</p>
        </div>
      </div>

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Projetos</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded">Novo Projeto</button>
      </div>

      <table className="w-full text-left bg-white shadow rounded border overflow-hidden">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="p-4">Nome</th>
            <th className="p-4">Cliente</th>
            <th className="p-4">Valor</th>
            <th className="p-4">Status</th>
            <th className="p-4">Progresso</th>
            <th className="p-4">Último Deploy</th>
          </tr>
        </thead>
        <tbody>
          {projects.map(p => (
            <tr key={p.id} className="border-b">
              <td className="p-4">
                <Link to={`/admin/project/${p.id}`} className="text-blue-600 hover:underline">
                  {p.name}
                </Link>
              </td>
              <td className="p-4">{p.client_name}</td>
              <td className="p-4">R$ {p.value}</td>
              <td className="p-4">{p.status}</td>
              <td className="p-4">{p.progress}%</td>
              <td className="p-4">{p.last_deploy_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}