import React, { useState } from 'react';
import { ArchiveEntry } from '../types';

/**
 * ArchiveViewer - Read-only cartridge browser
 * Displays immutable archive entries with retrieval metadata
 */

interface ArchiveViewerProps {
  archives: ArchiveEntry[];
  isAdmin?: boolean;
}

export const ArchiveViewer: React.FC<ArchiveViewerProps> = ({ archives, isAdmin = false }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div
      className="archive-viewer"
      role="region"
      aria-label="Archive storage"
    >
      <div
        style={{
          fontSize: 'var(--font-size-lg)',
          fontWeight: 'var(--font-weight-bold)',
          marginBottom: 'var(--spacing-4)',
          paddingBottom: 'var(--spacing-3)',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        Archive Cartridges ({archives.length})
      </div>

      {archives.length === 0 ? (
        <div
          style={{
            padding: 'var(--spacing-8)',
            textAlign: 'center',
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          No archived cartridges
        </div>
      ) : (
        <div className="archive-list" role="list">
          {archives.map((archive) => (
            <div key={archive.archive_record_id} role="listitem">
              <button
                className="archive-item"
                onClick={() =>
                  setExpandedId(
                    expandedId === archive.archive_record_id ? null : archive.archive_record_id
                  )
                }
                style={{
                  width: '100%',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all var(--transition-base)',
                  padding: 'var(--spacing-4)',
                }}
                aria-expanded={expandedId === archive.archive_record_id}
                aria-label={`Archive: ${archive.storage_path}`}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--spacing-1)' }}>
                      {archive.storage_path.split('/').pop()}
                    </div>
                    <div
                      className="archive-path"
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        marginBottom: 'var(--spacing-2)',
                      }}
                    >
                      {archive.storage_path}
                    </div>
                    <div
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-text-tertiary)',
                      }}
                    >
                      Created: {formatDate(archive.created_at)}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--font-size-xl)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {expandedId === archive.archive_record_id ? '▼' : '▶'}
                  </div>
                </div>
              </button>

              {expandedId === archive.archive_record_id && (
                <div
                  style={{
                    padding: 'var(--spacing-4)',
                    backgroundColor: 'var(--color-bg-primary)',
                    borderTop: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-xs)',
                    fontFamily: 'var(--font-family-mono)',
                  }}
                  role="region"
                  aria-label={`Details for ${archive.storage_path}`}
                >
                  <div
                    style={{
                      display: 'grid',
                      gap: 'var(--spacing-3)',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: 'var(--spacing-2)',
                        backgroundColor: 'var(--color-bg-tertiary)',
                        borderRadius: '4px',
                      }}
                    >
                      <span style={{ color: 'var(--color-text-secondary)' }}>Record ID:</span>
                      <span style={{ wordBreak: 'break-all' }}>{archive.archive_record_id}</span>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: 'var(--spacing-2)',
                        backgroundColor: 'var(--color-bg-tertiary)',
                        borderRadius: '4px',
                      }}
                    >
                      <span style={{ color: 'var(--color-text-secondary)' }}>Hash:</span>
                      <span style={{ wordBreak: 'break-all' }}>
                        {archive.immutable_hash.substring(0, 20)}...
                      </span>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: 'var(--spacing-2)',
                        backgroundColor: 'var(--color-bg-tertiary)',
                        borderRadius: '4px',
                      }}
                    >
                      <span style={{ color: 'var(--color-text-secondary)' }}>Retention:</span>
                      <span>{archive.retention_years} years</span>
                    </div>

                    {Boolean(archive.retrieval_metadata?.size_bytes) && (
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: 'var(--spacing-2)',
                          backgroundColor: 'var(--color-bg-tertiary)',
                          borderRadius: '4px',
                        }}
                      >
                        <span style={{ color: 'var(--color-text-secondary)' }}>Size:</span>
                        <span>{formatBytes(Number(archive.retrieval_metadata.size_bytes))}</span>
                      </div>
                    )}

                    {isAdmin && (
                      <div
                        style={{
                          marginTop: 'var(--spacing-2)',
                          padding: 'var(--spacing-2)',
                          backgroundColor: 'rgba(59, 130, 246, 0.1)',
                          borderRadius: '4px',
                          color: 'var(--color-low-blue)',
                        }}
                      >
                        Admin: Archive is write-once immutable. No modifications after creation.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {isAdmin && (
        <div
          style={{
            marginTop: 'var(--spacing-6)',
            padding: 'var(--spacing-4)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderRadius: '6px',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-low-blue)',
          }}
          role="complementary"
          aria-label="Admin information"
        >
          Admin View: All archives are stored in HP durable storage. Immutable hash prevents tampering.
          7-year retention enforced by law. No purge operations permitted until retention expires.
        </div>
      )}
    </div>
  );
};

export default ArchiveViewer;
