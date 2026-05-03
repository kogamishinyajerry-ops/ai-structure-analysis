import { useState, useEffect } from 'react';
import { Folder, FolderPlus, Clock, Layout } from 'lucide-react';

interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

interface ProjectManagerProps {
  onSelectProject: (projectId: number) => void;
  selectedProjectId: number | null;
}

export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectManagerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/projects')
      .then(res => res.json())
      .then(data => setProjects(data))
      .catch(err => console.error("Failed to fetch projects", err));
  }, []);

  const handleCreateProject = async () => {
    if (!newProject.name) return;
    
    try {
      const resp = await fetch('http://localhost:8000/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject)
      });
      if (resp.ok) {
        const created = await resp.json();
        setProjects([...projects, created]);
        setIsModalOpen(false);
        setNewProject({ name: '', description: '' });
      }
    } catch (err) {
      console.error("Failed to create project", err);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border-r border-slate-800 w-64">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Layout className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-slate-200">Projects</h2>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="p-1 hover:bg-slate-800 rounded-md transition-colors text-slate-400 hover:text-indigo-400"
        >
          <FolderPlus className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {projects.map(project => (
          <button
            key={project.id}
            onClick={() => onSelectProject(project.id)}
            className={`w-full text-left p-3 rounded-lg flex items-center group transition-all ${
              selectedProjectId === project.id 
                ? 'bg-indigo-600/20 border border-indigo-500/50' 
                : 'hover:bg-slate-800 border border-transparent'
            }`}
          >
            <Folder className={`w-4 h-4 mr-3 ${selectedProjectId === project.id ? 'text-indigo-400' : 'text-slate-500'}`} />
            <div className="flex-1 overflow-hidden">
              <div className={`text-sm font-medium truncate ${selectedProjectId === project.id ? 'text-white' : 'text-slate-300'}`}>
                {project.name}
              </div>
              <div className="text-[10px] text-slate-500 truncate flex items-center mt-0.5">
                <Clock className="w-3 h-3 mr-1" />
                {new Date(project.created_at).toLocaleDateString()}
              </div>
            </div>
          </button>
        ))}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Create New Project</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Project Name</label>
                <input 
                  value={newProject.name}
                  onChange={e => setNewProject({...newProject, name: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. Truss Bridge Design"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
                <textarea 
                  value={newProject.description}
                  onChange={e => setNewProject({...newProject, description: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2 px-3 text-white h-24 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Analyze the structural stability of..."
                />
              </div>
              <div className="flex space-x-3 pt-2">
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleCreateProject}
                  className="flex-1 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors font-semibold"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
