import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  getDocument,
  getDocumentText,
  getDocumentContentUrl,
  getDocumentThumbnailUrl
} from '../services/api';
import {
  ArrowLeft,
  FileText,
  Image,
  AlignLeft,
  ExternalLink,
  Calendar,
  HardDrive,
  Layers,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
} from 'lucide-react';

const TABS = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'text', label: 'Extracted Text', icon: AlignLeft },
  { id: 'preview', label: 'File Preview', icon: Image },
];

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function formatBytes(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function DocumentPreviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [doc, setDoc] = useState(null);
  const [contentUrl, setContentUrl] = useState(null);
  const [thumbnailUrl, setThumbnailUrl] = useState(null);
  const [textData, setTextData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [textLoading, setTextLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const [imgError, setImgError] = useState(false);

  // Fetch document metadata
  useEffect(() => {
    setLoading(true);
    getDocument(id)
      .then(setDoc)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // Fetch extracted text when that tab is opened
  useEffect(() => {
    if (activeTab === 'text' && !textData) {
      setTextLoading(true);
      getDocumentText(id)
        .then(setTextData)
        .catch((err) => setError(err.message))
        .finally(() => setTextLoading(false));
    }
  }, [activeTab, id, textData]);

  useEffect(() => {
    if (doc?.id) {
      getDocumentThumbnailUrl(doc.id)
        .then(setThumbnailUrl)
        .catch(() => setImgError(true));
    }
  }, [doc?.id]);

  // Re-fetches every time tab is opened to always get a fresh non-expired URL
  useEffect(() => {
    if (activeTab === 'preview' && doc?.id) {
      getDocumentContentUrl(doc.id).then(setContentUrl);
    }
  }, [activeTab, doc?.id]);


  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner" />
      </div>
    );
  }

  if (error && !doc) {
    return (
      <div className="page">
        <div className="alert alert-error">{error}</div>
        <Link to="/documents" className="btn btn-ghost" style={{ marginTop: '1rem' }}>
          <ArrowLeft size={16} /> Back to Documents
        </Link>
      </div>
    );
  }

  const isPDF = doc?.file_type === 'pdf';
  const isImage = ['png', 'jpg', 'jpeg', 'tiff'].includes(doc?.file_type);

  const pages = textData?.pages || [];
  const pageCount = pages.length;

  return (
    <div className="doc-preview-page">
      {/* ── Breadcrumb header ── */}
      <div className="doc-preview-header">
        <button className="btn btn-ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Back
        </button>

        <div className="doc-preview-title-area">
          <div className="doc-preview-icon">
            <FileText size={28} />
          </div>
          <div>
            <h1 className="doc-preview-title">{doc?.file_name}</h1>
            <div className="doc-preview-meta-row">
              <StatusBadge status={doc?.status} />
              <span className="badge badge-type">{doc?.file_type?.toUpperCase()}</span>
              <span className="doc-preview-meta-item">
                <HardDrive size={13} /> {formatBytes(doc?.file_size)}
              </span>
              {doc?.page_count > 0 && (
                <span className="doc-preview-meta-item">
                  <Layers size={13} /> {doc.page_count} page{doc.page_count !== 1 ? 's' : ''}
                </span>
              )}
              <span className="doc-preview-meta-item">
                <Calendar size={13} />
                {doc?.created_at ? new Date(doc.created_at).toLocaleDateString(undefined, {
                  year: 'numeric', month: 'long', day: 'numeric',
                }) : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="doc-preview-actions">
          <a
            href={contentUrl ?? '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost"
          >
            <ExternalLink size={15} /> Open File
          </a>
          <Link to="/chat" className="btn btn-primary">
            <MessageSquare size={15} /> Chat with Doc
          </Link>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ margin: '0 2.5rem' }}>{error}</div>}

      {/* ── Tabs ── */}
      <div className="doc-preview-tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`doc-tab ${activeTab === tab.id ? 'doc-tab-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={15} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ── Tab Panels ── */}
      <div className="doc-preview-body">

        {/* Overview tab */}
        {activeTab === 'overview' && (
          <div className="doc-overview-grid">
            {/* Thumbnail card */}
            <div className="doc-thumbnail-card">
              <p className="doc-section-label">Thumbnail</p>
              {imgError ? (
                <div className="doc-thumb-placeholder">
                  <FileText size={56} strokeWidth={1.2} />
                  <p>No thumbnail</p>
                </div>
              ) : !thumbnailUrl ? (
                <div className="doc-thumb-placeholder" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                  <div className="spinner" />
                  <p>Loading...</p>
                </div>
              ) : (
                <img
                  src={thumbnailUrl}
                  alt={doc?.file_name}
                  className="doc-thumb-img"
                  onError={() => setImgError(true)}
                />
              )}
            </div>

            {/* Details card */}
            <div className="doc-details-card">
              <p className="doc-section-label">Document Details</p>
              <dl className="doc-detail-list">
                <div className="doc-detail-row">
                  <dt>File Name</dt>
                  <dd>{doc?.file_name}</dd>
                </div>
                <div className="doc-detail-row">
                  <dt>File Type</dt>
                  <dd><span className="badge badge-type">{doc?.file_type?.toUpperCase()}</span></dd>
                </div>
                <div className="doc-detail-row">
                  <dt>Status</dt>
                  <dd><StatusBadge status={doc?.status} /></dd>
                </div>
                <div className="doc-detail-row">
                  <dt>File Size</dt>
                  <dd>{formatBytes(doc?.file_size)}</dd>
                </div>
                <div className="doc-detail-row">
                  <dt>Pages</dt>
                  <dd>{doc?.page_count ?? '—'}</dd>
                </div>
                <div className="doc-detail-row">
                  <dt>Uploaded</dt>
                  <dd>
                    {doc?.created_at
                      ? new Date(doc.created_at).toLocaleString()
                      : '—'}
                  </dd>
                </div>
                <div className="doc-detail-row">
                  <dt>Last Updated</dt>
                  <dd>
                    {doc?.updated_at
                      ? new Date(doc.updated_at).toLocaleString()
                      : '—'}
                  </dd>
                </div>
                <div className="doc-detail-row">
                  <dt>Document ID</dt>
                  <dd className="doc-id-val">{doc?.id}</dd>
                </div>
              </dl>

              <div className="doc-detail-ctas">
                <button
                  className="btn btn-ghost"
                  onClick={() => setActiveTab('text')}
                  disabled={doc?.status !== 'ready'}
                >
                  <AlignLeft size={15} /> View Text
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={() => setActiveTab('preview')}
                >
                  <Image size={15} /> Preview File
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Extracted Text tab */}
        {activeTab === 'text' && (
          <div className="doc-text-panel">
            {textLoading ? (
              <div className="doc-text-loader">
                <div className="spinner" />
                <p>Loading extracted text…</p>
              </div>
            ) : pageCount === 0 ? (
              <div className="empty-state">
                <AlignLeft size={48} strokeWidth={1.5} stroke="var(--color-text-muted)" />
                <p>
                  {doc?.status !== 'ready'
                    ? 'Text is not yet available — document is still processing.'
                    : 'No text content was extracted from this document.'}
                </p>
              </div>
            ) : (
              <>
                {/* Page navigator */}
                <div className="doc-text-nav">
                  <span className="doc-text-nav-label">
                    Page {currentPage + 1} of {pageCount}
                  </span>
                  <div className="doc-text-nav-btns">
                    <button
                      className="btn btn-ghost"
                      disabled={currentPage === 0}
                      onClick={() => setCurrentPage((p) => p - 1)}
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <button
                      className="btn btn-ghost"
                      disabled={currentPage === pageCount - 1}
                      onClick={() => setCurrentPage((p) => p + 1)}
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>

                {/* Page jump pills */}
                {pageCount > 1 && (
                  <div className="doc-page-pills">
                    {pages.map((_, idx) => (
                      <button
                        key={idx}
                        className={`doc-page-pill ${idx === currentPage ? 'active' : ''}`}
                        onClick={() => setCurrentPage(idx)}
                      >
                        {idx + 1}
                      </button>
                    ))}
                  </div>
                )}

                <pre className="doc-text-content">
                  {pages[currentPage]?.raw_text || '(No text on this page)'}
                </pre>
              </>
            )}
          </div>
        )}

        {/* File Preview tab */}
        {activeTab === 'preview' && (
          <div className="doc-file-preview-panel">
            {!contentUrl ? (
              <div className="doc-file-preview-loader" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px' }}>
                <div className="spinner" />
                <p>Loading preview...</p>
              </div>
            ) : isPDF ? (
              <iframe
                src={contentUrl}
                title={doc?.file_name}
                className="doc-pdf-embed"
              />
            ) : isImage ? (
              <div className="doc-image-preview-wrap">
                <img
                  src={contentUrl}
                  alt={doc?.file_name}
                  className="doc-image-preview"
                />
              </div>
            ) : (
              <div className="empty-state">
                <FileText size={48} strokeWidth={1.5} stroke="var(--color-text-muted)" />
                <p>In-browser preview is not available for this file type.</p>
                <a
                  href={contentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                >
                  <ExternalLink size={15} /> Download / Open File
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
