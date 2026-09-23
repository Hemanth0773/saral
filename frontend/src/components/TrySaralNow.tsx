import { useEffect, useRef, useState } from 'react';
import { API_BASE_URL, extractDocumentUrl, type DocumentExtractionResponse } from '../services/api';

type TrySaralNowProps = {
  sampleUrl: string | null;
  samplePulse: number;
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

export default function TrySaralNow({ sampleUrl, samplePulse }: TrySaralNowProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('Uploading document...');
  const [urlValue, setUrlValue] = useState('');
  const [urlIndicator, setUrlIndicator] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentExtractionResponse | null>(null);
  const [submittingUrl, setSubmittingUrl] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCounterRef = useRef(0);
  const requestRef = useRef<XMLHttpRequest | null>(null);

  const resetResult = () => {
    setResult(null);
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

    xhr.addEventListener('load', () => {
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
        setResult(payload as DocumentExtractionResponse);
        setProgress(100);
        setStatusText('Extraction complete');
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

  const handleUrlSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    stopRequest();
    resetResult();

    const url = urlValue.trim();
    if (!url) {
      setError('Paste a document or gazette URL first.');
      return;
    }

    let parsedUrl: URL;
    try {
      parsedUrl = new URL(url);
    } catch {
      setError('Enter a complete URL starting with http:// or https://.');
      return;
    }
    if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
      setError('Only HTTP and HTTPS URLs are allowed.');
      return;
    }

    setSubmittingUrl(true);
    setProcessing(true);
    setUploading(false);
    setProgress(20);
    setStatusText('Contacting document source...');

    try {
      const response = await extractDocumentUrl(url);
      setResult(response);
      setProgress(100);
      setStatusText('Extraction complete');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The document could not be extracted.');
    } finally {
      setSubmittingUrl(false);
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (!sampleUrl) return;

    setUrlValue(sampleUrl);
    setUrlIndicator(true);
    const timer = window.setTimeout(() => setUrlIndicator(false), 2000);
    return () => window.clearTimeout(timer);
  }, [samplePulse, sampleUrl]);

  useEffect(() => () => stopRequest(), []);

  const busy = uploading || processing || submittingUrl;

  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section" id="try-saral">
      <div className="bg-white stroke-border rounded-3xl p-8 sm:p-12 card-shadow-lg">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-block bg-[#F9C915] stroke-border-thin px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider mb-3">TRY IT LIVE</div>
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
          <form className="space-y-4" onSubmit={handleUrlSubmit}>
            <div>
              <label className="block text-xs font-extrabold uppercase tracking-wider mb-2 text-neutral-800" htmlFor="gazette-url">Paste Document or Gazette URL</label>
              <div className="relative">
                <input
                  className="w-full bg-neutral-50 border-2 border-neutral-900 rounded-xl px-4 py-3.5 text-sm font-medium focus:ring-2 focus:ring-black focus:border-black outline-none placeholder:text-neutral-400 transition-colors disabled:opacity-70"
                  disabled={busy}
                  id="gazette-url"
                  onChange={(event) => setUrlValue(event.target.value)}
                  placeholder="https://egazette.gov.in/notification..."
                  type="url"
                  value={urlValue}
                />
                <span className={`${urlIndicator ? 'flex' : 'hidden'} absolute right-3 top-3.5 bg-black text-white text-[10px] font-black uppercase px-2 py-0.5 rounded-full pop-pulse`}>Sample Loaded</span>
              </div>
            </div>
            <button className="btn-tactile w-full bg-black hover:bg-neutral-900 text-white font-extrabold text-sm sm:text-base py-4 rounded-xl stroke-border flex items-center justify-center gap-2 group cursor-pointer disabled:opacity-70 disabled:cursor-wait" disabled={busy} type="submit">
              <span>{submittingUrl || processing ? (urlValue.trim() ? 'Analyzing Gazette...' : 'Processing...') : 'Simplify Document'}</span>
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
          {result && (
            <div className="mt-6 bg-[#FEF9C3] stroke-border rounded-2xl p-5 text-left">
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-black/15">
                <span className="w-2.5 h-2.5 bg-black rounded-full"></span>
                <span className="text-xs font-extrabold uppercase tracking-wider">Extraction complete</span>
              </div>
              <p className="text-sm font-medium text-neutral-800 leading-relaxed">
                {result.filename ? `${result.filename} was extracted` : 'The document URL was extracted'} · {result.metadata.word_count} words · {result.language.toUpperCase()} · {result.extraction_method.replace(/_/g, ' ')}
              </p>
              {result.text && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-extrabold uppercase tracking-wider">View extracted text</summary>
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-white stroke-border-thin p-3 text-xs leading-relaxed text-neutral-700">{result.text}</pre>
                </details>
              )}
              <p className="mt-3 text-[11px] font-bold text-neutral-500">Document extraction is connected. The full simplification pipeline will be added in the next frontend milestone.</p>
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
