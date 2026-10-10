/**
 * AuraRAG Backend API Service
 *
 * Communicates with the FastAPI backend:
 * - POST /upload  (Multipart FormData with field 'file')
 * - POST /voice   (Multipart FormData with fields 'file' + optional 'filename')
 * - POST /ask     (JSON { query, filename })
 * - GET  /        (Health check)
 * - GET  /voice-audio/{filename} (Audio playback static mount)
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000';


/**
 * Check if the FastAPI backend is running and reachable
 */
export async function checkBackendHealth() {
  try {
    const controller = new AbortController();

    const timeoutId = setTimeout(
      () => controller.abort(),
      4000
    );

    const response = await fetch(`${API_BASE_URL}/`, {
      method: 'GET',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return {
        ok: false,
        message: `HTTP ${response.status}: ${response.statusText}`,
      };
    }

    const data = await response.json();

    return {
      ok: true,
      message: data.message || 'AuraRAG is running',
    };

  } catch (error) {
    return {
      ok: false,
      message:
        error.name === 'AbortError'
          ? 'Connection timed out. Ensure backend is running at ' +
            API_BASE_URL
          : 'Cannot reach backend at ' +
            API_BASE_URL +
            '. Is uvicorn running?',
    };
  }
}


/**
 * Upload a document to the /upload endpoint
 *
 * Supported types:
 * - .pdf
 * - .docx
 * - .txt
 *
 * Backend expects:
 * multipart/form-data with field 'file'
 *
 * Returns:
 * {
 *   filename,
 *   message,
 *   number_of_chunks
 * }
 */
export async function uploadDocument(file) {
  const formData = new FormData();

  formData.append('file', file);

  const response = await fetch(
    `${API_BASE_URL}/upload`,
    {
      method: 'POST',
      body: formData,
    }
  );

  if (!response.ok) {
    let errorDetail = 'Upload failed';

    try {
      const errJson = await response.json();

      errorDetail =
        errJson.detail ||
        errJson.message ||
        errorDetail;

    } catch {
      errorDetail =
        `Server returned HTTP ${response.status}`;
    }

    throw new Error(errorDetail);
  }

  return await response.json();
}


/**
 * Send voice recording to the /voice endpoint
 *
 * Backend expects:
 * multipart/form-data with:
 * - file      → audio recording
 * - filename  → active document filename (optional)
 *
 * Returns:
 * {
 *   query,
 *   answer,
 *   audio_url
 * }
 */
export async function sendVoiceRecording(
  audioBlob,
  audioFilename = 'voice.webm',
  documentFilename = null
) {
  const formData = new FormData();

  // Voice recording
  formData.append(
    'file',
    audioBlob,
    audioFilename
  );

  // Active document
  if (documentFilename) {
    formData.append(
      'filename',
      documentFilename
    );
  }

  const response = await fetch(
    `${API_BASE_URL}/voice`,
    {
      method: 'POST',
      body: formData,
    }
  );

  if (!response.ok) {
    let errorDetail =
      'Voice processing failed';

    try {
      const errJson = await response.json();

      errorDetail =
        errJson.detail ||
        errJson.message ||
        errorDetail;

    } catch {
      errorDetail =
        `Server returned HTTP ${response.status}`;
    }

    throw new Error(errorDetail);
  }

  return await response.json();
}


/**
 * Send direct text query to the /ask endpoint
 *
 * Backend expects:
 * {
 *   query: string,
 *   filename: string | null
 * }
 *
 * Returns:
 * {
 *   question,
 *   answer
 * }
 */
export async function sendTextQuery(
  query,
  documentFilename = null
) {
  const response = await fetch(
    `${API_BASE_URL}/ask`,
    {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json',
      },

      body: JSON.stringify({
        query,
        filename: documentFilename,
      }),
    }
  );

  if (!response.ok) {
    let errorDetail = 'Query failed';

    try {
      const errJson = await response.json();

      errorDetail =
        errJson.detail ||
        errJson.message ||
        errorDetail;

    } catch {
      errorDetail =
        `Server returned HTTP ${response.status}`;
    }

    throw new Error(errorDetail);
  }

  return await response.json();
}


/**
 * Resolve audio URL to an absolute URL
 * ready for browser playback.
 */
export function resolveAudioUrl(audioUrl) {
  if (!audioUrl) {
    return '';
  }

  if (
    audioUrl.startsWith('http://') ||
    audioUrl.startsWith('https://')
  ) {
    return audioUrl;
  }

  // Remove trailing slash from API base URL
  const base = API_BASE_URL.replace(/\/$/, '');

  // Ensure audio path starts with /
  const path = audioUrl.startsWith('/')
    ? audioUrl
    : `/${audioUrl}`;

  return `${base}${path}`;
}