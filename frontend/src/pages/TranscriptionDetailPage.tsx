/**
 * Transcription Detail Page
 * Sprint 3 - View and edit call transcriptions
 */

import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { transcriptionService, Transcription } from '../services/transcriptionService'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { Skeleton, SkeletonText } from '../components/Skeleton'
import { useToast } from '../components/Toast'

const formatDateTime = (d: string) =>
  new Date(d).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

const formatDuration = (seconds: number | null) => {
  if (!seconds) return '—'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const TranscriptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  const [transcription, setTranscription] = useState<Transcription | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editedText, setEditedText] = useState('')
  const [saving, setSaving] = useState(false)

  const fetchTranscription = useCallback(async () => {
    if (!id) return
    try {
      setLoading(true)
      const data = await transcriptionService.getTranscription(Number(id))
      setTranscription(data)
      setEditedText(data.text)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch transcription')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchTranscription()
  }, [fetchTranscription])

  const handleSave = async () => {
    if (!transcription) return
    setSaving(true)
    try {
      const updated = await transcriptionService.updateTranscriptionText(
        transcription.id,
        editedText
      )
      setTranscription(updated)
      setIsEditing(false)
      toast.success('Transcription saved', `${updated.word_count} words`)
    } catch (err: any) {
      toast.error('Save failed', err.response?.data?.detail || 'Try again later.')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (transcription) setEditedText(transcription.text)
    setIsEditing(false)
  }

  if (loading) {
    return (
      <div className="page-container">
        <Breadcrumbs trailing="Loading…" />
        <div className="page-heading">
          <div>
            <Skeleton width={220} height={28} />
            <div style={{ marginTop: 8 }}>
              <Skeleton width={300} height={14} />
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <SkeletonText lines={6} />
          </div>
        </div>
      </div>
    )
  }

  if (error && !transcription) {
    return (
      <div className="page-container">
        <Breadcrumbs />
        <ErrorState
          title="Couldn't load transcription"
          message={error}
          onRetry={fetchTranscription}
          retrying={loading}
        />
      </div>
    )
  }

  if (!transcription) {
    return (
      <div className="page-container">
        <Breadcrumbs />
        <EmptyState
          icon="mic"
          title="Transcription not found"
          description="It may have been deleted or you don't have permission to view it."
          action={
            <Button variant="primary" onClick={() => navigate('/call-logs')}>
              Back to Call Logs
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="page-container">
      <Breadcrumbs trailing={`Call #${transcription.id}`} />
      <div className="page-heading">
        <div>
          <h1>Call transcription</h1>
          <p>
            {transcription.patient_name} · {transcription.patient_phone}
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => navigate('/call-logs')}
          leftIcon={<Icon name="chevron-left" size={14} />}
        >
          Back to Call Logs
        </Button>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't refresh"
          message={error}
          onRetry={fetchTranscription}
          retrying={loading}
        />
      )}

      {/* Call info */}
      <div className="card mb-4">
        <div className="card-head">
          <h5>Call information</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <InfoCell label="Patient" value={transcription.patient_name} />
            <InfoCell label="Phone" value={transcription.patient_phone} />
            <InfoCell label="Call date" value={formatDateTime(transcription.call_date)} />
            <InfoCell label="Duration" value={formatDuration(transcription.call_duration)} />
            <InfoCell
              label="Status"
              value={<span className="badge badge-success">{transcription.status}</span>}
            />
            <InfoCell label="Word count" value={transcription.word_count} />
          </div>

          {/* Recording player */}
          {transcription.recording_url && (
            <div className="mt-4">
              <div
                className="small-muted"
                style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8 }}
              >
                Call Recording
              </div>
              <audio
                controls
                style={{ width: '100%', maxWidth: 600 }}
                preload="metadata"
              >
                <source src={transcription.recording_url} type="audio/mpeg" />
                Your browser does not support the audio element.
              </audio>
            </div>
          )}

          {transcription.is_edited && (
            <div className="alert alert-info mt-4" role="status">
              <Icon name="edit" size={16} />
              <div>
                Edited by <strong>{transcription.last_edited_by_name}</strong> on{' '}
                {formatDateTime(transcription.last_edited_at!)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Transcription body */}
      <div className="card">
        <div className="card-head">
          <div>
            <h5>Transcription text</h5>
            <p>Manually corrected transcripts override the automatic Whisper output.</p>
          </div>
          {!isEditing ? (
            <Button
              variant="primary"
              onClick={() => setIsEditing(true)}
              leftIcon={<Icon name="edit" size={14} />}
            >
              Edit
            </Button>
          ) : (
            <div className="d-flex gap-2">
              <Button variant="ghost" onClick={handleCancel} disabled={saving}>
                Cancel
              </Button>
              <Button variant="success" onClick={handleSave} loading={saving}>
                Save changes
              </Button>
            </div>
          )}
        </div>
        <div className="card-body">
          {isEditing ? (
            <>
              <label htmlFor="t-text" className="visually-hidden">
                Transcription text
              </label>
              <textarea
                id="t-text"
                className="form-textarea"
                rows={15}
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                style={{ fontFamily: 'var(--font-mono)', fontSize: 14, minHeight: 320 }}
              />
            </>
          ) : (
            <div
              style={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'Georgia, serif',
                fontSize: 16,
                lineHeight: 1.8,
                padding: 20,
                background: 'var(--surface-2)',
                borderRadius: 'var(--r-md)',
              }}
            >
              {transcription.text || (
                <span className="small-muted">No transcription text was generated.</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="card mt-4">
        <div className="card-head">
          <h5>Metadata</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <InfoCell label="Whisper model" value={transcription.whisper_model || '—'} />
            <InfoCell label="Created" value={formatDateTime(transcription.created_at)} />
            <InfoCell label="Last updated" value={formatDateTime(transcription.updated_at)} />
            {transcription.confidence_score && (
              <InfoCell
                label="Confidence"
                value={`${(transcription.confidence_score * 100).toFixed(1)}%`}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const InfoCell: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="col-md-6">
    <div
      className="small-muted"
      style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}
    >
      {label}
    </div>
    <div style={{ fontWeight: 500, marginTop: 2 }}>{value}</div>
  </div>
)

export default TranscriptionDetailPage
