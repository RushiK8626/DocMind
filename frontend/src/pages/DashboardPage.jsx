import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getProjects } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Folder, Plus, Loader, LayoutDashboard, Search } from 'lucide-react';
import CreateProjectModal from '../components/CreateProjectModal';

export default function DashboardPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchProjects = () => {
    setLoading(true);
    getProjects(1, 5) // Fetch up to 5 recent projects
      .then((data) => setProjects(Array.isArray(data) ? data : data.projects || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleProjectCreated = (newProject) => {
    setProjects([newProject, ...projects].slice(0, 5));
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="page-subtitle">Welcome back, {user?.email || 'User'}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} />
          Create Project
        </button>
      </header>

      {/* Recent projects */}
      <section className="section">
        <div className="section-header">
          <h2>Recent Projects</h2>
          <Link to="/projects" className="btn btn-ghost">View all</Link>
        </div>

        {loading && <div className="empty-state"><div className="spinner" /></div>}
        {error && <div className="alert alert-error">{error}</div>}

        {!loading && !error && projects.length === 0 && (
          <div className="empty-state">
            <Folder size={48} strokeWidth={1.5} stroke="var(--color-text-muted)" />
            <p>You haven't created any projects yet.</p>
            <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
              Create your first project
            </button>
          </div>
        )}

        {!loading && !error && projects.length > 0 &&
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Description</th>
                  <th>Documents</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.id} className="table-row-hover">
                    <td className="font-medium">
                      <Link to={`/projects/${project.id}`} className="doc-link">
                        {project.project_name}
                      </Link>
                    </td>
                    <td className="text-muted">
                      {project.description ? (
                        project.description.length > 50
                          ? project.description.substring(0, 50) + '...'
                          : project.description
                      ) : '—'}
                    </td>
                    <td>
                      <span className="badge badge-ready">{project.document_count || 0}</span>
                    </td>
                    <td className="text-muted">
                      {project.updated_at
                        ? new Date(project.updated_at).toLocaleDateString()
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        }
      </section>
      {/* Quick actions */}
      <section className="section">
        <h2>Quick Actions</h2>
        <div className="quick-actions">
          <button className="action-card" onClick={() => setIsModalOpen(true)} style={{ textAlign: 'left', border: 'none', background: 'var(--color-surface)', cursor: 'pointer', fontFamily: 'inherit' }}>
            <Plus size={24} />
            <span>Create New Project</span>
          </button>
          <Link to="/projects" className="action-card">
            <Folder size={24} />
            <span>Browse All Projects</span>
          </Link>
        </div>
      </section>

      <CreateProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onProjectCreated={handleProjectCreated}
      />
    </div>
  );
}
