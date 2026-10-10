import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { AlertCircleIcon, MicIcon, StopIcon } from './Icons';

/**
 * VoiceOrb Component
 *
 * Responsibilities:
 * - Handle microphone permissions
 * - Record audio via MediaRecorder
 * - Transition between IDLE, RECORDING, PROCESSING, RESPONSE states
 * - Pass recorded audio Blob to parent on stop
 */

const VoiceOrb = forwardRef(function VoiceOrb(
  {
    currentState = 'IDLE',
    onVoiceRecorded,
    errorMessage = null,
    onResetError,
    onRecordingStateChange,
  },
  ref
) {
  const [isRecording, setIsRecording] = useState(false);
  const [internalError, setInternalError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Cleanup microphone tracks on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const getSupportedMimeType = () => {
    if (typeof MediaRecorder === 'undefined') return '';
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    for (const type of candidates) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    return '';
  };

  const startRecording = async () => {
    setInternalError(null);
    if (onResetError) onResetError();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setInternalError('Microphone access is not available in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      streamRef.current = stream;

      const mime = getSupportedMimeType();
      const options = mime ? { mimeType: mime } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mime || 'audio/webm',
        });

        // Release mic hardware tracks only AFTER audio chunks are collected
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        if (audioBlob.size > 0) {
          if (onVoiceRecorded) {
            onVoiceRecorded(audioBlob);
          }
        } else {
          setInternalError('No voice audio recorded. Please try again.');
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      if (onRecordingStateChange) {
        onRecordingStateChange(true);
      }
    } catch (err) {
      console.error('Microphone error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setInternalError(
          'Microphone permission was denied. Please allow microphone access in your browser and try again.'
        );
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setInternalError('No microphone hardware detected on your device.');
      } else {
        setInternalError(
          'Could not access microphone: ' + (err.message || 'Please check system permissions.')
        );
      }
      setIsRecording(false);
      if (onRecordingStateChange) {
        onRecordingStateChange(false);
      }
    }
  };

  const stopRecording = () => {
    // Stop recording, but allow onstop/ondataavailable to collect the audio
    // before closing the stream tracks (prevents race condition).
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    if (onRecordingStateChange) {
      onRecordingStateChange(false);
    }
  };

  useImperativeHandle(ref, () => ({
    startRecording,
    stopRecording,
    isRecording,
  }));

  const handleOrbClick = (e) => {
    if (e && e.stopPropagation) e.stopPropagation();
    if (currentState === 'PROCESSING') return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // Determine active visual state
  const effectiveState = internalError || errorMessage
    ? 'ERROR'
    : isRecording
    ? 'RECORDING'
    : currentState;

  const getStateText = () => {
    switch (effectiveState) {
      case 'RECORDING':
        return 'Listening...';
      case 'PROCESSING':
        return 'Thinking...';
      case 'RESPONSE':
        return 'Speaking...';
      case 'ERROR':
        return 'Something went wrong';
      case 'IDLE':
      default:
        return 'Click the microphone to speak';
    }
  };

  const activeError = internalError || errorMessage;

  return (
    <div className="voice-orb-section">
      <div className={`voice-orb-container state-${effectiveState.toLowerCase()}`}>
        {/* Subtle animated aura / waveform rings */}
        <div className="voice-aura-rings" aria-hidden="true">
          <div className="aura-halo halo-inner" />
          <div className="aura-halo halo-mid" />
          <div className="aura-halo halo-outer" />

          {effectiveState === 'RECORDING' && (
            <div className="subtle-waveform-ring">
              <span className="wave-pulse p1" />
              <span className="wave-pulse p2" />
              <span className="wave-pulse p3" />
            </div>
          )}
        </div>

        {/* Circular Microphone Button */}
        <button
          type="button"
          className={`voice-orb-button ${isRecording ? 'is-recording' : ''}`}
          onClick={handleOrbClick}
          disabled={effectiveState === 'PROCESSING'}
          aria-label={
            isRecording
              ? 'Stop recording'
              : effectiveState === 'PROCESSING'
              ? 'Thinking...'
              : effectiveState === 'RESPONSE'
              ? 'Speaking...'
              : 'Click the microphone to speak'
          }
          title={
            isRecording
              ? 'Stop recording'
              : effectiveState === 'PROCESSING'
              ? 'Thinking...'
              : effectiveState === 'RESPONSE'
              ? 'Speaking...'
              : 'Click the microphone to speak'
          }
          aria-pressed={isRecording}
        >
          <div className="voice-orb-inner" style={{ pointerEvents: 'none' }}>
            {isRecording ? (
              <StopIcon size={32} className="orb-icon stop-icon" />
            ) : effectiveState === 'PROCESSING' ? (
              <div className="orb-thinking-indicator" aria-hidden="true">
                <span className="thinking-dot d1" />
                <span className="thinking-dot d2" />
                <span className="thinking-dot d3" />
              </div>
            ) : (
              <MicIcon size={34} className="orb-icon mic-icon" />
            )}
          </div>
        </button>
      </div>

      {/* State Text below the microphone */}
      <div
        className="voice-state-caption"
        onClick={handleOrbClick}
        role="button"
        tabIndex={0}
        style={{ cursor: effectiveState === 'PROCESSING' ? 'default' : 'pointer' }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleOrbClick(e);
          }
        }}
      >
        <span className={`voice-state-label state-${effectiveState.toLowerCase()}`}>
          {getStateText()}
        </span>
      </div>

      {/* Error notification if present */}
      {activeError && (
        <div className="voice-error-banner" role="alert">
          <AlertCircleIcon size={16} className="error-icon" />
          <span className="error-text">{activeError}</span>
          <button
            type="button"
            className="error-dismiss-btn"
            onClick={(e) => {
              e.stopPropagation();
              setInternalError(null);
              if (onResetError) onResetError();
            }}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
});

export default VoiceOrb;
