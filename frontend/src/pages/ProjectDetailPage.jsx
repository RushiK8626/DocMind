import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getProject, getDocuments, getConversations } from '../services/api';
import { Upload, MessageSquare, FileText, Loader, ArrowLeft } from 'lucide-react';

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProjectData = async () => {
      setLoading(true);
      try {
        const projData = await getProject(projectId);
        setProject(projData.project);

        // Fetch docs and conversations concurrently
        const [docsData, convsData] = await Promise.all([
          getDocuments(projectId),
          getConversations(projectId, 1)
        ]);
        
        setDocuments(Array.isArray(docsData) ? docsData : docsData.documents || []);
        setConversations(convsData.conversations || []);
      } catch (err) {
        setError(err.message || 'Failed to load project details');
      } finally {
        setLoading(false);
      }
    };

    fetchProjectData();
  }, [projectId]);

  if (loading) {
    return <div className="page"><div className="page-loader"><div className="spinner" /></div></div>;
  }

  if (error || !project) {
    return (
      <div className="page">
        <div className="alert alert-error">{error || 'Project not found'}</div>
        <Link to="/projects" className="btn btn-ghost" style={{ marginTop: '1rem' }}>
          <ArrowLeft size={16} /> Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <Link to="/projects" className="btn-ghost btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-text-muted)' }}>
            <ArrowLeft size={14} /> Back
          </Link>
          <h1>{project.project_name}</h1>
          {project.description && <p className="page-subtitle">{project.description}</p>}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to={`/projects/${projectId}/upload`} className="btn btn-primary">
            <Upload size={16} /> Upload
          </Link>
          <Link to={`/projects/${projectId}/chat`} className="btn btn-secondary">
            <MessageSquare size={16} /> Chat
          </Link>
        </div>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon stat-icon-total">
            <FileText size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{documents.length}</span>
            <span className="stat-label">Documents</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon stat-icon-ready">
            <MessageSquare size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{conversations.length}</span>
            <span className="stat-label">Conversations</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
        {/* Recent Documents Section */}
        <section className="section" style={{ marginTop: 0 }}>
          <div className="section-header">
            <h2>Recent Documents</h2>
            <Link to={`/projects/${projectId}/documents`} className="btn btn-ghost btn-sm">View all</Link>
          </div>
          {documents.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem 1rem' }}>
              <p>No documents uploaded yet.</p>
              <Link to={`/projects/${projectId}/upload`} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>Upload Document</Link>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.slice(0, 5).map(doc => (
                    <tr key={doc.id}>
                      <td><Link to={`/documents/${doc.id}`} className="doc-link">{doc.file_name}</Link></td>
                      <td><span className={`badge badge-${doc.status}`}>{doc.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Recent Conversations Section */}
        <section className="section" style={{ marginTop: 0 }}>
          <div className="section-header">
            <h2>Recent Conversations</h2>
            <Link to={`/projects/${projectId}/chat`} className="btn btn-ghost btn-sm">View all</Link>
          </div>
          {conversations.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem 1rem' }}>
              <p>No conversations yet.</p>
              <Link to={`/projects/${projectId}/chat`} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>Start Chat</Link>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Topic</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {conversations.slice(0, 5).map(conv => (
                    <tr key={conv.id}>
                      <td>
                        {/* We don't have a direct route to a single conversation yet, but ChatPage handles selecting it if we implemented that. For now just link to ChatPage. */}
                        <Link to={`/projects/${projectId}/chat`} className="doc-link">{conv.title}</Link>
                      </td>
                      <td className="text-muted">{new Date(conv.updated_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
