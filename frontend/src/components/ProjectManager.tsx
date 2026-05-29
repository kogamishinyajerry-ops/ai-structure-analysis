// FM-04a Phase 41.2 — ProjectManager restyle. The pre-41 markup used
// Tailwind utility classes (bg-slate-*/text-indigo-*/w-64/space-y-*), but
// this project has NO Tailwind pipeline, so every one of those classes was
// DEAD — the left rail rendered as unstyled browser defaults (the "empty
// broken rail" the demo audit flagged). This rewrite swaps the dead Tailwind
// for the real 41.1 token system + the existing .glass-sidebar / .case-item /
// .glass-panel shared classes. Behavior (fetch, create, select, modal) is
// unchanged.
import { useState, useEffect, type CSSProperties } from 'react';
import { Folder, FolderPlus, Clock } from 'lucide-react';

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
  // Codex R0 P2: gate the empty-state hint on load completion so a slow or
  // unavailable backend never flashes a misleading "No projects yet" during
  // the in-flight / error window.
  const [loadStatus, setLoadStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/projects')
      .then(res => res.json())
      .then(data => { setProjects(data); setLoadStatus('ready'); })
      .catch(err => { console.error("Failed to fetch projects", err); setLoadStatus('error'); });
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
    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
      <div style={headerStyle}>
        <span className="eyebrow">Projects</span>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          aria-label="Create new project"
          style={addButtonStyle}
        >
          <FolderPlus size={16} />
        </button>
      </div>

      <div style={listStyle}>
        {projects.map(project => {
          const active = selectedProjectId === project.id;
          return (
            <button
              key={project.id}
              onClick={() => onSelectProject(project.id)}
              className={`case-item${active ? ' active' : ''}`}
              style={{ ...projectButtonStyle, ...(active ? projectButtonActiveStyle : null) }}
            >
              <Folder size={15} style={{ color: active ? 'var(--accent)' : 'var(--text-muted)', flexShrink: 0 }} />
              <span style={{ flex: 1, overflow: 'hidden' }}>
                <span style={{ ...projectNameStyle, color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {project.name}
                </span>
                <span style={projectDateStyle}>
                  <Clock size={11} />
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
              </span>
            </button>
          );
        })}
        {loadStatus === 'ready' && projects.length === 0 && (
          <p style={emptyHintStyle}>No projects yet. Create one to organize your analyses.</p>
        )}
        {loadStatus === 'error' && (
          <p style={emptyHintStyle}>Couldn&rsquo;t load projects — is the backend running?</p>
        )}
      </div>

      {isModalOpen && (
        <div style={modalOverlayStyle}>
          <div className="glass-panel" style={modalCardStyle}>
            <h3 style={modalTitleStyle}>Create new project</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
              <div>
                <label style={fieldLabelStyle}>Project name</label>
                <input
                  value={newProject.name}
                  onChange={e => setNewProject({ ...newProject, name: e.target.value })}
                  style={fieldInputStyle}
                  placeholder="e.g. Truss bridge design"
                />
              </div>
              <div>
                <label style={fieldLabelStyle}>Description</label>
                <textarea
                  value={newProject.description}
                  onChange={e => setNewProject({ ...newProject, description: e.target.value })}
                  style={{ ...fieldInputStyle, height: 96, resize: 'vertical' }}
                  placeholder="Analyze the structural stability of…"
                />
              </div>
              <div style={{ display: 'flex', gap: 'var(--sp-3)', paddingTop: 'var(--sp-1)' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} style={cancelButtonStyle}>
                  Cancel
                </button>
                <button type="button" onClick={handleCreateProject} style={createButtonStyle}>
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

const rootStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  overflow: 'hidden',
};
const headerStyle: CSSProperties = {
  padding: 'var(--sp-4)',
  borderBottom: '1px solid var(--border)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};
const addButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 'var(--sp-1)',
  borderRadius: 'var(--r-sm)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
};
const listStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 'var(--sp-2)',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-1)',
};
const projectButtonStyle: CSSProperties = {
  width: '100%',
  textAlign: 'left',
  display: 'flex',
  alignItems: 'center',
  gap: 'var(--sp-3)',
  padding: 'var(--sp-3)',
  borderRadius: 'var(--r-md)',
  border: '1px solid transparent',
  background: 'transparent',
  cursor: 'pointer',
  fontFamily: 'inherit',
};
const projectButtonActiveStyle: CSSProperties = {
  background: 'var(--accent-glow)',
  border: '1px solid var(--border-focus)',
};
const projectNameStyle: CSSProperties = {
  display: 'block',
  fontSize: 'var(--fs-sm)',
  fontWeight: 600,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
};
const projectDateStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  marginTop: 2,
  fontSize: 'var(--fs-xs)',
  color: 'var(--text-muted)',
};
const emptyHintStyle: CSSProperties = {
  margin: 0,
  padding: 'var(--sp-3)',
  fontSize: 'var(--fs-xs)',
  color: 'var(--text-muted)',
  lineHeight: 1.5,
};
const modalOverlayStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0, 0, 0, 0.6)',
  backdropFilter: 'blur(4px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 50,
  padding: 'var(--sp-4)',
};
const modalCardStyle: CSSProperties = {
  width: '100%',
  maxWidth: 420,
  padding: 'var(--sp-6)',
  boxShadow: 'var(--elev-3)',
};
const modalTitleStyle: CSSProperties = {
  margin: '0 0 var(--sp-4)',
  fontSize: 'var(--fs-lg)',
  fontWeight: 700,
  letterSpacing: 'var(--tracking-tight)',
  color: 'var(--text-primary)',
};
const fieldLabelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 'var(--sp-1)',
  fontSize: 'var(--fs-sm)',
  fontWeight: 500,
  color: 'var(--text-secondary)',
};
const fieldInputStyle: CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'var(--c-900)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-sm)',
  padding: 'var(--sp-2) var(--sp-3)',
  color: 'var(--text-primary)',
  fontFamily: 'inherit',
  fontSize: 'var(--fs-sm)',
};
const cancelButtonStyle: CSSProperties = {
  flex: 1,
  padding: 'var(--sp-2)',
  background: 'transparent',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
  borderRadius: 'var(--r-sm)',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontWeight: 600,
};
const createButtonStyle: CSSProperties = {
  flex: 1,
  padding: 'var(--sp-2)',
  background: 'var(--accent)',
  border: '1px solid var(--accent)',
  color: '#04130d',
  borderRadius: 'var(--r-sm)',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontWeight: 700,
};
