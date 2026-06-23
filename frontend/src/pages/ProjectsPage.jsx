import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getProjects, deleteProject } from '../services/api';
import { Folder, Plus, Trash2 } from 'lucide-react';
import CreateProjectModal from '../components/CreateProjectModal';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({});

  const fetchProjects = (pageNum = 1) => {
    setLoading(true);
    getProjects(pageNum, 20)
      .then((data) => {
        setProjects(Array.isArray(data) ? data : data.projects || []);
        if (data.pagination) setPagination(data.pagination);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchProjects(page);
  }, [page]);

  const handleProjectCreated = (newProject) => {
    fetchProjects(1); // Refresh the list
  };

  const handleDelete = async (projectId) => {
    if (!window.confirm('Are you sure you want to delete this project? This will also delete all documents and conversations inside it.')) return;
    
    try {
      await deleteProject(projectId);
      setProjects(projects.filter(p => p.id !== projectId));
    } catch (err) {
      alert(err.message || 'Failed to delete project');
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Projects</h1>
          <p className="page-subtitle">Manage your workspaces</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} />
          Create Project
        </button>
      </header>

      <section className="section">
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
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Project Name</th>
                    <th>Description</th>
                    <th>Documents</th>
                    <th>Last Updated</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
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
                      <td style={{ textAlign: 'right' }}>
                        <button 
                          className="btn btn-ghost btn-sm" 
                          onClick={() => handleDelete(project.id)}
                          title="Delete project"
                          style={{ color: 'var(--color-error)' }}
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Pagination Controls */}
            {pagination && pagination.total_pages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem', alignItems: 'center' }}>
                <button 
                  className="btn btn-ghost" 
                  disabled={!pagination.has_prev} 
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </button>
                <span className="text-muted">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
                <button 
                  className="btn btn-ghost" 
                  disabled={!pagination.has_next} 
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            )}
          </>
        }
      </section>
      
      <CreateProjectModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onProjectCreated={handleProjectCreated}
      />
    </div>
  );
}
