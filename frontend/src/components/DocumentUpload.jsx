import { useRef, useState } from 'react';
import {
  AlertCircleIcon,
  CheckIcon,
  DocumentIcon,
  UploadIcon,
  XIcon,
} from './Icons';
import { uploadDocument } from '../services/api';

const ACCEPTED_EXTENSIONS = ['.pdf', '.txt', '.docx'];

export default function DocumentUpload({ onUploadSuccess, onDocumentUploaded }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    if (!file) return false;
    const name = file.name.toLowerCase();
    const isValid = ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));

    if (!isValid) {
      setErrorMessage('Please select a valid document: PDF, TXT, or DOCX.');
      return false;
    }

    setErrorMessage(null);
    return true;
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file && validateFile(file)) {
      setSelectedFile(file);
      setUploadResult(null);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && validateFile(file)) {
      setSelectedFile(file);
      setUploadResult(null);
    }
  };

  const handleClearSelected = () => {
    setSelectedFile(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || isProcessing) return;

    setIsProcessing(true);
    setErrorMessage(null);
    setUploadResult(null);

    try {
      const data = await uploadDocument(selectedFile);
      const uploadedFilename = data?.filename || selectedFile.name;
      setUploadResult({
        filename: uploadedFilename,
        chunks: data?.number_of_chunks ?? 0,
      });
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (onUploadSuccess) {
        onUploadSuccess(data);
      }
      if (onDocumentUploaded) {
        onDocumentUploaded(uploadedFilename);
      }
    } catch (err) {
      console.error('Upload error:', err);
      setErrorMessage("We couldn't process this document. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Helper to format file size cleanly
  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <section className="knowledge-sources-section" aria-label="Knowledge Sources">
      <div className="sources-card">
        {/* Header */}
        <div className="sources-header">
          <h2 className="sources-heading">Add to your knowledge</h2>
          <p className="sources-description">
            Upload a document and AuraRAG will make its contents searchable.
          </p>
        </div>

        {/* Drag and Drop Box */}
        <div
          className={`sources-dropzone ${isDragging ? 'is-dragging' : ''} ${
            selectedFile ? 'has-file' : ''
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !selectedFile && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !selectedFile) {
              fileInputRef.current?.click();
            }
          }}
          aria-label="Upload document area"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.docx"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />

          {!selectedFile ? (
            <div className="dropzone-idle-content">
              <div className="dropzone-icon-circle">
                <UploadIcon size={20} />
              </div>
              <p className="dropzone-primary-text">
                Drag &amp; drop your file here <span className="text-dim">or</span>{' '}
                <span className="browse-link">Browse files</span>
              </p>
              <span className="supported-formats-label">
                Supported: PDF · TXT · DOCX
              </span>
            </div>
          ) : (
            <div className="selected-file-row">
              <div className="file-info-group">
                <div className="file-type-icon-wrapper">
                  <DocumentIcon size={20} />
                </div>
                <div className="file-details">
                  <span className="file-display-name" title={selectedFile.name}>
                    {selectedFile.name}
                  </span>
                  <span className="file-display-size">
                    {formatSize(selectedFile.size)}
                  </span>
                </div>
              </div>

              <button
                type="button"
                className="clear-file-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearSelected();
                }}
                disabled={isProcessing}
                aria-label="Remove selected file"
              >
                <XIcon size={16} />
              </button>
            </div>
          )}
        </div>

        {/* Action button when file is selected */}
        {selectedFile && (
          <div className="upload-action-bar">
            <button
              type="button"
              className={`upload-submit-btn ${isProcessing ? 'is-processing' : ''}`}
              onClick={handleUpload}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <span className="btn-spinner" />
                  <span>Processing document...</span>
                </>
              ) : (
                <>
                  <UploadIcon size={16} />
                  <span>Upload Document</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Error notification */}
        {errorMessage && (
          <div className="upload-alert error" role="alert">
            <AlertCircleIcon size={15} />
            <span>{errorMessage}</span>
            <button
              type="button"
              className="alert-dismiss"
              onClick={() => setErrorMessage(null)}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        {/* Success notification: "Document added" & "X chunks indexed" */}
        {uploadResult && (
          <div className="upload-alert success" role="status">
            <CheckIcon size={15} />
            <div className="success-text-group">
              <span className="success-main">Document added</span>
              <span className="success-chunks">
                · {uploadResult.chunks} {uploadResult.chunks === 1 ? 'chunk' : 'chunks'} indexed
              </span>
            </div>
            <button
              type="button"
              className="alert-dismiss"
              onClick={() => setUploadResult(null)}
              aria-label="Dismiss message"
            >
              ×
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
