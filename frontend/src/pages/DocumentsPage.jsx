import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getDocuments, deleteDocuments } from '../services/api';
import { FileText, Eye, Upload, Search, Trash2 } from 'lucide-react';

export default function DocumentsPage() {
  const { projectId } = useParams();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState([]);

  const loadDocuments = () => {
    setLoading(true);
    getDocuments(projectId)
      .then((data) => setDocuments(Array.isArray(data) ? data : data.documents || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const filtered = documents.filter((d) =>
    d.file_name?.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedDocIds(filtered.map(d => d.id));
    } else {
      setSelectedDocIds([]);
    }
  };

  const handleSelectOne = (id, checked) => {
    if (checked) {
      setSelectedDocIds(prev => [...prev, id]);
    } else {
      setSelectedDocIds(prev => prev.filter(item => item !== id));
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedDocIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete the ${selectedDocIds.length} selected document(s)?`)) return;
    
    try {
      setLoading(true);
      const res = await deleteDocuments(selectedDocIds);
      const succeeded = res.summary?.succeeded || 0;
      const failed = res.summary?.failed || 0;
      
      if (failed > 0) {
        alert(`Deleted ${succeeded} document(s). Failed to delete ${failed} document(s).`);
      }
      setSelectedDocIds([]);
      loadDocuments();
    } catch (err) {
      setError(`Failed to delete documents: ${err.message}`);
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>My Documents</h1>
          <p className="page-subtitle">Manage and preview your uploaded files</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {selectedDocIds.length > 0 && (
            <button className="btn btn-danger" onClick={handleDeleteSelected}>
              <Trash2 size={16} />
              Delete Selected ({selectedDocIds.length})
            </button>
          )}
          <Link to={`/projects/${projectId}/upload`} className="btn btn-primary">
            <Upload size={16} />
            Upload Files
          </Link>
        </div>
      </header>

      {/* Search bar */}
      <div className="docs-search-bar">
        <Search size={16} className="docs-search-icon" />
        <input
          type="search"
          placeholder="Search documents…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="docs-search-input"
        />
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loader" style={{ height: '40vh' }}>
          <div className="spinner" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} strokeWidth={1.5} stroke="var(--color-text-muted)" />
          <p>
            {documents.length === 0
              ? "You haven't uploaded any documents yet."
              : 'No documents match your search.'}
          </p>
          {documents.length === 0 && (
            <Link to={`/projects/${projectId}/upload`} className="btn btn-primary">
              Upload your first document
            </Link>
          )}
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '40px', paddingLeft: '1.5rem', paddingRight: '0' }}>
                  <input
                    type="checkbox"
                    className="doc-checkbox"
                    checked={filtered.length > 0 && selectedDocIds.length === filtered.length}
                    onChange={handleSelectAll}
                  />
                </th>
                <th>File Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Date Uploaded</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc) => (
                <tr key={doc.id} className={`table-row-hover ${selectedDocIds.includes(doc.id) ? 'row-selected' : ''}`}>
                  <td style={{ width: '40px', paddingLeft: '1.5rem', paddingRight: '0' }}>
                    <input
                      type="checkbox"
                      className="doc-checkbox"
                      checked={selectedDocIds.includes(doc.id)}
                      onChange={(e) => handleSelectOne(doc.id, e.target.checked)}
                    />
                  </td>
                  <td className="font-medium">
                    <Link to={`/documents/${doc.id}`} className="doc-link">
                      {doc.file_name}
                    </Link>
                  </td>
                  <td>
                    <span className="badge badge-type">{doc.file_type?.toUpperCase()}</span>
                  </td>
                  <td>
                    <span className={`badge badge-${doc.status}`}>{doc.status}</span>
                  </td>
                  <td className="text-muted">
                    {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Link
                      to={`/documents/${doc.id}`}
                      className="btn btn-ghost btn-sm"
                      title="Preview document"
                    >
                      <Eye size={15} /> Preview
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
