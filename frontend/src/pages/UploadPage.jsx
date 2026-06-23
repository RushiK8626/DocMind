import { useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { uploadFiles } from '../services/api';
import { Upload, FileText, X } from 'lucide-react';

export default function UploadPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    console.log(files.length)
    if (files.length === 0) return;

    setUploading(true);
    setError('');
    setSuccess(null);

    try {
      const data = await uploadFiles(files, projectId);
      setSuccess(`Successfully uploaded ${data.summary.succeeded} files. ${data.summary.failed > 0 ? `Failed: ${data.summary.failed}` : ''}`);
      setFiles([]);
      // Redirect to project detail page after a short delay
      setTimeout(() => navigate(`/projects/${projectId}`), 2000);
    } catch (err) {
      setError(err.message || 'Failed to upload documents');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Upload Documents</h1>
          <p className="page-subtitle">Upload PDFs, images, or documents for processing</p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div
        className="upload-dropzone"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={48} stroke="var(--color-primary)" strokeWidth={1.5} />
        <h3>Click or drag files here</h3>
        <p>Supports PDF, PNG, JPG, JPEG, TIFF, DOCX</p>
        <input
          type="file"
          multiple
          ref={fileInputRef}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {files.length > 0 && (
        <div className="upload-file-list">
          <h3>Selected Files ({files.length})</h3>
          <ul className="file-list">
            {files.map((file, i) => (
              <li key={i} className="file-item">
                <div className="file-info">
                  <FileText size={20} />
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                </div>
                <button
                  className="btn-icon"
                  onClick={() => removeFile(i)}
                  disabled={uploading}
                >
                  <X size={18} />
                </button>
              </li>
            ))}
          </ul>

          <div className="upload-actions">
            <button
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? 'Uploading and Processing...' : 'Upload Files'}
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => setFiles([])}
              disabled={uploading}
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
