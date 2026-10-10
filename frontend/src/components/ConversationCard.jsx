import { useEffect, useRef, useState } from 'react';
import {
  CopyIcon,
  CheckIcon,
  PlayIcon,
  ReplayIcon,
  SpeakerIcon,
} from './Icons';
import { resolveAudioUrl } from '../services/api';

export default function ConversationCard({
  conversation,
  onAudioPlayStateChange,
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [copied, setCopied] = useState(false);
  const audioRef = useRef(null);

  const onAudioPlayStateChangeRef = useRef(onAudioPlayStateChange);
  useEffect(() => {
    onAudioPlayStateChangeRef.current = onAudioPlayStateChange;
  });

  // Auto-play audio when audio_url arrives
  useEffect(() => {
    const audioUrl = conversation?.audio_url;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    if (!audioUrl) return;

    const fullUrl = resolveAudioUrl(audioUrl);
    const audio = new Audio(fullUrl);
    audioRef.current = audio;

    const handlePlay = () => {
      setIsPlaying(true);
      if (onAudioPlayStateChangeRef.current) {
        onAudioPlayStateChangeRef.current(true);
      }
    };

    const handlePause = () => {
      setIsPlaying(false);
      if (onAudioPlayStateChangeRef.current) {
        onAudioPlayStateChangeRef.current(false);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      if (onAudioPlayStateChangeRef.current) {
        onAudioPlayStateChangeRef.current(false);
      }
    };

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);

    audio.play().catch((err) => {
      console.warn('Auto-play prevented by browser policy:', err);
      setIsPlaying(false);
      if (onAudioPlayStateChangeRef.current) {
        onAudioPlayStateChangeRef.current(false);
      }
    });

    return () => {
      audio.pause();
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      if (audioRef.current === audio) {
        audioRef.current = null;
      }
      setIsPlaying(false);
      if (onAudioPlayStateChangeRef.current) {
        onAudioPlayStateChangeRef.current(false);
      }
    };
  }, [conversation?.audio_url]);

  const toggleAudio = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((e) => console.warn('Play error:', e));
    }
  };

  const replayAudio = () => {
    if (!audioRef.current) return;

    audioRef.current.currentTime = 0;
    audioRef.current.play().catch((e) => console.warn('Replay error:', e));
  };

  const handleCopy = () => {
    if (!conversation?.answer) return;
    navigator.clipboard.writeText(conversation.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!conversation) {
    return null;
  }

  return (
    <section className="knowledge-card active-conversation-card" aria-label="Active Conversation">
      {/* SECTION: YOUR QUESTION */}
      <div className="knowledge-card-section question-section">
        <div className="section-meta-header">
          <span className="section-label">YOU</span>
        </div>
        <p className="transcribed-question-text">
          {conversation.query}
        </p>
      </div>

      <div className="knowledge-divider" />

      {/* SECTION: AURARAG ANSWER */}
      <div className="knowledge-card-section answer-section">
        <div className="section-meta-header">
          <div className="aurarag-brand-pill">
            <span className="aurora-dot" />
            <span className="section-label brand-accent">AURARAG</span>
          </div>

          <div className="card-utility-actions">
            {/* Audio Controls */}
            {conversation.audio_url && (
              <div className="minimal-audio-controls">
                <button
                  type="button"
                  className={`audio-status-pill ${isPlaying ? 'is-speaking' : ''}`}
                  onClick={toggleAudio}
                  title={isPlaying ? 'Pause audio' : 'Play audio'}
                >
                  {isPlaying ? (
                    <>
                      <SpeakerIcon size={14} className="speaking-icon" />
                      <span>Speaking</span>
                    </>
                  ) : (
                    <>
                      <PlayIcon size={13} />
                      <span>Play response</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  className="audio-replay-btn"
                  onClick={replayAudio}
                  title="Replay audio"
                  aria-label="Replay response audio"
                >
                  <ReplayIcon size={14} />
                </button>
              </div>
            )}

            {/* Copy button */}
            <button
              type="button"
              className="copy-answer-btn"
              onClick={handleCopy}
              title="Copy answer"
              aria-label="Copy answer to clipboard"
            >
              {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>

        <div className="answer-content-body">
          {conversation.answer.split('\n\n').map((paragraph, idx) => (
            <p key={idx}>{paragraph}</p>
          ))}
        </div>
      </div>
    </section>
  );
}
