import { useEffect, useRef, useState } from 'react';
import { API_BASE_URL, extractDocumentUrl, simplifyDocument, type DocumentExtractionResponse, type SimplificationResponse } from '../services/api';

type TrySaralNowProps = {
  sampleUrl: string | null;
  samplePulse: number;
  onSimplificationComplete?: (simplifiedText: string) => void;
};

const acceptedExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
const maxFileSize = 10 * 1024 * 1024;

function getPayloadMessage(payload: unknown) {
  const value = payload as {
    error?: { message?: string; code?: string };
    detail?: unknown;
    message?: string;
  } | null;

  if (value?.error?.message) return value.error.message;
  if (value?.message) return value.message;
  if (typeof value?.detail === 'string') return value.detail;
  if (value?.error?.code) return value.error.code.replace(/_/g, ' ');
  return 'The backend returned an unexpected response.';
}

function isUrl(input: string) {
  try {
    const parsed = new URL(input);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

export default function TrySaralNow({ sampleUrl, samplePulse, onSimplificationComplete }: TrySaralNowProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('Uploading document...');
  const [inputValue, setInputValue] = useState('');
  const [urlIndicator, setUrlIndicator] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractionResult, setExtractionResult] = useState<DocumentExtractionResponse | null>(null);
  const [simplificationResult, setSimplificationResult] = useState<SimplificationResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCounterRef = useRef(0);
  const requestRef = useRef<XMLHttpRequest | null>(null);

  const resetResult = () => {
    setExtractionResult(null);
    setSimplificationResult(null);
    setError(null);
  };

  const stopRequest = () => {
    if (requestRef.current) {
      requestRef.current.abort();
      requestRef.current = null;
    }
  };

  const handleFile = (file: File) => {
    stopRequest();
    resetResult();
    const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
    if (!acceptedExtensions.includes(extension)) {
      setSelectedFile(null);
      setError('Please choose a PDF, JPG, or PNG document.');
      return;
    }

    if (file.size > maxFileSize) {
      setSelectedFile(null);
      setError('Please choose a document smaller than 10 MB.');
      return;
    }

    setSelectedFile(file);
    setUploading(true);
    setProcessing(false);
    setProgress(0);
    setStatusText(`Processing: ${file.name}`);

    const xhr = new XMLHttpRequest();
    requestRef.current = xhr;
    const formData = new FormData();
    formData.append('file', file);

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        setProgress(Math.round((event.loaded / event.total) * 80));
      }
    });

    xhr.addEventListener('load', async () => {
      setUploading(false);
      setProcessing(false);
      requestRef.current = null;

      let payload: unknown = {};
      try {
        payload = JSON.parse(xhr.responseText || '{}');
      } catch {
        payload = {};
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        const extractionResponse = payload as DocumentExtractionResponse;
        setExtractionResult(extractionResponse);
        setProgress(90);
        setStatusText('Simplifying...');

        try {
          const simplificationResponse = await simplifyDocument(extractionResponse.text);
          setSimplificationResult(simplificationResponse);
          setProgress(100);
          setStatusText('Simplification complete');
          if (simplificationResponse.simplified_text && onSimplificationComplete) {
            onSimplificationComplete(simplificationResponse.simplified_text);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Simplification failed.');
        }
      } else {
        setError(getPayloadMessage(payload));
      }
    });

    xhr.addEventListener('error', () => {
      setUploading(false);
      setProcessing(false);
      requestRef.current = null;
      setError('Unable to connect to the Saral backend. Make sure it is running on port 8000.');
    });

    xhr.addEventListener('abort', () => {
      setUploading(false);
      setProcessing(false);
      requestRef.current = null;
    });

    xhr.open('POST', `${API_BASE_URL}/api/documents/extract`);
    xhr.send(formData);
  };

  const handleInputSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    stopRequest();
    resetResult();

    const input = inputValue.trim();
    if (!input) {
      setError('Paste a document URL or enter text to simplify.');
      return;
    }

    const isUrlInput = isUrl(input);

    setSubmitting(true);
    setProcessing(true);
    setUploading(false);
    setProgress(isUrlInput ? 20 : 10);
    setStatusText(isUrlInput ? 'Contacting document source...' : 'Simplifying...');

    try {
      let extractedText: string;

      if (isUrlInput) {
        const response = await extractDocumentUrl(input);
        setExtractionResult(response);
        extractedText = response.text;
        setProgress(50);
        setStatusText('Simplifying...');
      } else {
        extractedText = input;
        setProgress(50);
        setStatusText('Simplifying...');
      }

      const simplificationResponse = await simplifyDocument(extractedText);
      setSimplificationResult(simplificationResponse);
      setProgress(100);
      setStatusText('Simplification complete');
      if (simplificationResponse.simplified_text && onSimplificationComplete) {
        onSimplificationComplete(simplificationResponse.simplified_text);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not process the input.');
    } finally {
      setSubmitting(false);
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (!sampleUrl) return;

    setInputValue(sampleUrl);
    setUrlIndicator(true);
    const timer = window.setTimeout(() => setUrlIndicator(false), 2000);
    return () => window.clearTimeout(timer);
  }, [samplePulse, sampleUrl]);

  useEffect(() => () => stopRequest(), []);

  const busy = uploading || processing || submitting;

  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section" id="try-saral">
      <div className="bg-white stroke-border rounded-3xl p-8 sm:p-12 card-shadow-lg">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-block bg-[#F9C915] stroke-border-thin px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider mb-3">1 / SIMPLIFY</div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">Try Saral right now</h2>
          <p className="text-neutral-700 font-medium text-base">Upload a government circular, notice, or bill to witness instant plain-language conversion.</p>
        </div>
        <div className="max-w-3xl mx-auto">
          <div
            className={`border-2 border-dashed border-neutral-900 bg-[#FEF9C3]/50 hover:bg-[#FEF9C3] rounded-2xl p-8 sm:p-12 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center relative select-none ${dragOver ? 'dropzone-dashed dragover' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragEnter={(event) => {
              event.preventDefault();
              dragCounterRef.current += 1;
              setDragOver(true);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              event.stopPropagation();
              setDragOver(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              dragCounterRef.current -= 1;
              if (dragCounterRef.current <= 0) {
                dragCounterRef.current = 0;
                setDragOver(false);
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              event.stopPropagation();
              dragCounterRef.current = 0;
              setDragOver(false);
              const file = event.dataTransfer.files?.[0];
              if (file) handleFile(file);
            }}
          >
            <div className="w-16 h-16 rounded-2xl bg-[#F9C915] stroke-border flex items-center justify-center mb-4 transition-transform duration-300">
              <svg className="w-8 h-8 text-black" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
            </div>
            <h3 className="text-lg font-extrabold mb-1">{selectedFile ? `Processing: ${selectedFile.name}` : 'Drop your government document here'}</h3>
            <p className="text-xs font-bold text-neutral-600 mb-5">Supports PDF, JPG, PNG, or Scanned Circulars</p>
            <div className={`w-full max-w-xs mb-4 ${uploading || processing ? 'block' : 'hidden'}`}>
              <div className="flex justify-between text-xs font-bold mb-1">
                <span>{statusText}</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full h-3 bg-neutral-200 stroke-border-thin rounded-full overflow-hidden">
                <div className="h-full bg-black transition-all duration-200" style={{ width: `${progress}%` }}></div>
              </div>
            </div>
            <label className="btn-tactile bg-white hover:bg-neutral-100 text-black text-sm font-extrabold px-6 py-2.5 rounded-full stroke-border cursor-pointer inline-block">
              <span>Choose a file</span>
              <input
                ref={fileInputRef}
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) handleFile(file);
                  event.target.value = '';
                }}
                type="file"
              />
            </label>
          </div>
          <div className="relative my-8 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-neutral-200"></div>
            </div>
            <span className="relative bg-white px-4 text-xs font-black uppercase tracking-widest text-neutral-500">OR</span>
          </div>
          <form className="space-y-4" onSubmit={handleInputSubmit}>
            <div>
              <label className="block text-xs font-extrabold uppercase tracking-wider mb-2 text-neutral-800" htmlFor="gazette-url">Paste Document URL or Plain Text</label>
              <div className="relative">
                <textarea
                  className="w-full bg-neutral-50 border-2 border-neutral-900 rounded-xl px-4 py-3.5 text-sm font-medium focus:ring-2 focus:ring-black focus:border-black outline-none placeholder:text-neutral-400 transition-colors disabled:opacity-70 resize-none min-h-[100px]"
                  disabled={busy}
                  id="gazette-url"
                  onChange={(event) => setInputValue(event.target.value)}
                  placeholder="https://egazette.gov.in/notification... or paste plain text here"
                  value={inputValue}
                />
                <span className={`${urlIndicator ? 'flex' : 'hidden'} absolute right-3 top-3.5 bg-black text-white text-[10px] font-black uppercase px-2 py-0.5 rounded-full pop-pulse`}>Sample Loaded</span>
              </div>
            </div>
            <button className="btn-tactile w-full bg-black hover:bg-neutral-900 text-white font-extrabold text-sm sm:text-base py-4 rounded-xl stroke-border flex items-center justify-center gap-2 group cursor-pointer disabled:opacity-70 disabled:cursor-wait" disabled={busy} type="submit">
              <span>{submitting || processing ? (inputValue.trim() ? 'Simplifying...' : 'Processing...') : 'Simplify Document'}</span>
              <span className={`group-hover:translate-x-1.5 transition-transform duration-200 ${busy ? 'hidden' : ''}`}>→</span>
              <svg className={`animate-spin h-5 w-5 text-white ${busy ? 'block' : 'hidden'}`} fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
              </svg>
            </button>
          </form>
          {error && (
            <div role="alert" className="mt-6 bg-[#FEF9C3] stroke-border-thin rounded-xl px-4 py-3 text-xs font-bold text-black">
              {error}
            </div>
          )}
          {extractionResult && !simplificationResult && (
            <div className="mt-6 bg-[#FEF9C3] stroke-border rounded-2xl p-5 text-left">
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-black/15">
                <span className="w-2.5 h-2.5 bg-black rounded-full"></span>
                <span className="text-xs font-extrabold uppercase tracking-wider">Extraction complete</span>
              </div>
              <p className="text-sm font-medium text-neutral-800 leading-relaxed">
                {extractionResult.filename ? `${extractionResult.filename} was extracted` : 'The document URL was extracted'} · {extractionResult.metadata.word_count} words · {extractionResult.language.toUpperCase()} · {extractionResult.extraction_method.replace(/_/g, ' ')}
              </p>
              {extractionResult.text && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-extrabold uppercase tracking-wider">View extracted text</summary>
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-white stroke-border-thin p-3 text-xs leading-relaxed text-neutral-700">{extractionResult.text}</pre>
                </details>
              )}
            </div>
          )}
          {simplificationResult && (
            <div className="mt-6 bg-[#FEF9C3] stroke-border rounded-2xl p-5 text-left">
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-black/15">
                <span className="w-2.5 h-2.5 bg-black rounded-full"></span>
                <span className="text-xs font-extrabold uppercase tracking-wider">Simplification complete</span>
              </div>
              <p className="text-sm font-medium text-neutral-800 leading-relaxed">
                Simplified to Grade {simplificationResult.target_grade_level} · {simplificationResult.model_used} · {simplificationResult.processing_time_ms}ms
              </p>
              {simplificationResult.simplified_text && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-extrabold uppercase tracking-wider">View simplified text</summary>
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-white stroke-border-thin p-3 text-xs leading-relaxed text-neutral-700">{simplificationResult.simplified_text}</pre>
                </details>
              )}
            </div>
          )}
          <div className="mt-6 flex items-center justify-center gap-2 text-xs font-bold text-neutral-500">
            <svg className="w-4 h-4 text-neutral-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" strokeLinecap="round" strokeLinejoin="round"></path>
            </svg>
            <span>Files are processed privately and never used for public training.</span>
          </div>
        </div>
      </div>
    </section>
  );
}