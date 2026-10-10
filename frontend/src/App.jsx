import { useEffect, useRef, useState } from 'react';
import Navbar from './components/Navbar';
import VoiceOrb from './components/VoiceOrb';
import ConversationCard from './components/ConversationCard';
import DocumentUpload from './components/DocumentUpload';
import {
  checkBackendHealth,
  sendTextQuery,
  sendVoiceRecording,
} from './services/api';
import './App.css';

export default function App() {
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const [voiceState, setVoiceState] = useState('IDLE');
  const [voiceError, setVoiceError] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [textQuery, setTextQuery] = useState('');

  // Currently active/uploaded document
  const [activeDocument, setActiveDocument] = useState(null);

  const voiceOrbRef = useRef(null);

  // Initial health check on mount
  useEffect(() => {
    let active = true;

    checkBackendHealth().then((status) => {
      if (active) {
        setIsBackendOnline(status.ok);
        if (!status.ok) {
          setVoiceError('Backend is offline. Start the FastAPI server.');
        }
      }
    });

    return () => {
      active = false;
    };
  }, []);

  // Handle voice recording submission to POST /voice
  const handleVoiceRecorded = async (audioBlob) => {
    setVoiceState('PROCESSING');
    setVoiceError(null);

    try {
      const result = await sendVoiceRecording(
        audioBlob,
        'voice.webm',
        activeDocument
      );

      // Update activeDocument if returned
      if (result.active_document && result.active_document !== activeDocument) {
        setActiveDocument(result.active_document);
      }

      setConversation({
        query: result.query || 'Voice query',
        answer: result.answer || 'No response returned.',
        audio_url: result.audio_url || null,
      });

      if (result.audio_url) {
        setVoiceState('RESPONSE');
      } else {
        setVoiceState('IDLE');
      }
      setIsBackendOnline(true);
    } catch (err) {
      console.error('Voice processing error:', err);
      setVoiceState('IDLE');
      setVoiceError('Backend is offline. Start the FastAPI server.');
      setIsBackendOnline(false);
    }
  };

  const handleStartVoiceRecording = () => {
    if (voiceOrbRef.current) {
      voiceOrbRef.current.startRecording();
    }
  };

  const handleStopVoiceRecording = () => {
    if (voiceOrbRef.current) {
      voiceOrbRef.current.stopRecording();
    }
  };

  const handleRecordingStateChange = (recording) => {
    if (recording) {
      setVoiceState('RECORDING');
    } else if (voiceState === 'RECORDING') {
      setVoiceState('IDLE');
    }
  };

  // Text query fallback (/ask)
  const handleTextSubmit = async (e) => {
    e.preventDefault();
    const query = textQuery.trim();
    if (!query) return;

    setVoiceState('PROCESSING');
    setVoiceError(null);

    try {
      const result = await sendTextQuery(query, activeDocument);

      if (result.active_document && result.active_document !== activeDocument) {
        setActiveDocument(result.active_document);
      }

      setConversation({
        query: result.question || query,
        answer: result.answer || 'No response returned.',
        audio_url: result.audio_url || null,
      });

      setTextQuery('');
      if (result.audio_url) {
        setVoiceState('RESPONSE');
      } else {
        setVoiceState('IDLE');
      }
      setIsBackendOnline(true);
    } catch (err) {
      console.error('Text query error:', err);
      setVoiceState('IDLE');
      setVoiceError('Backend is offline. Start the FastAPI server.');
      setIsBackendOnline(false);
    }
  };

  // Sync speaking audio state with voice state
  const handleAudioPlayStateChange = (isPlaying) => {
    if (isPlaying) {
      setVoiceState('RESPONSE');
    } else if (voiceState === 'RESPONSE') {
      // Transition from RESPONSE to IDLE when audio playback completes
      setVoiceState('IDLE');
    }
  };

  return (
    <div className="aurarag-app">
      {/* Background ambient aurora lighting */}
      <div className="aurora-ambient-glow" aria-hidden="true">
        <div className="glow-orb orb-primary" />
        <div className="glow-orb orb-secondary" />
      </div>

      {/* Navigation Bar */}
      <Navbar isBackendOnline={isBackendOnline} />

      {/* Main Content Area */}
      <main className="main-content-flow">
        {/* Offline notification banner if backend is unreachable */}
        {!isBackendOnline && (
          <div className="offline-banner" role="alert">
            <span>Backend is offline. Start the FastAPI server.</span>
          </div>
        )}

        {/* Main Hero / Voice Area */}
        <section className="hero-voice-section">
          <h1 className="hero-heading">AuraRAG</h1>
          <p className="hero-supporting-text">Voice RAG Assistant</p>

          {/* Active document pill if document is selected */}
          {activeDocument && (
            <div className="active-doc-badge">
              <span className="active-doc-dot" />
              <span>Active Document: <strong>{activeDocument}</strong></span>
            </div>
          )}

          {/* Centerpiece Microphone Interaction */}
          <VoiceOrb
            ref={voiceOrbRef}
            currentState={voiceState}
            onVoiceRecorded={handleVoiceRecorded}
            onRecordingStateChange={handleRecordingStateChange}
            errorMessage={voiceError}
            onResetError={() => {
              setVoiceError(null);
              setVoiceState('IDLE');
            }}
          />

          {/* Simple Text Query Fallback */}
          <form className="text-query-fallback-form" onSubmit={handleTextSubmit}>
            <input
              type="text"
              value={textQuery}
              onChange={(e) => setTextQuery(e.target.value)}
              placeholder="Or type a question..."
              className="text-query-input"
              disabled={voiceState === 'PROCESSING'}
            />
            <button
              type="submit"
              className="text-query-submit-btn"
              disabled={!textQuery.trim() || voiceState === 'PROCESSING'}
            >
              Ask
            </button>
          </form>
        </section>

        {/* Conversation / Result Area */}
        <ConversationCard
          conversation={conversation}
          onAudioPlayStateChange={handleAudioPlayStateChange}
        />

        {/* Knowledge Sources / Document Upload */}
        <DocumentUpload
          onDocumentUploaded={(filename) => {
            const docName = typeof filename === 'object' && filename !== null ? filename.filename : filename;
            setActiveDocument(docName);
          }}
          onUploadSuccess={(data) => {
            const docName = typeof data === 'object' && data !== null ? data.filename : data;
            setActiveDocument(docName);
          }}
        />
      </main>

      {/* Minimal Footer */}
      <footer className="minimal-footer">
        <span>AuraRAG &bull; AI Voice RAG</span>
      </footer>
    </div>
  );
}