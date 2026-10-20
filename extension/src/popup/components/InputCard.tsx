import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import {
  ALLOWED_FILE_EXTENSIONS,
  MAX_FILE_SIZE_MB,
  MAX_SIMPLIFY_TEXT_LENGTH,
  formatBytes,
} from '../../shared/config';
import { ClearIcon, PlusIcon, SpinnerIcon, TabIcon, UploadIcon } from './Icons';

type InputCardProps = {
  value: string;
  onChange: (value: string) => void;
  onReadActiveTab: () => void;
  onSelectFile: (file: File) => void;
  onClear: () => void;
  file: File | null;
  fileError: string | null;
  isReading: boolean;
  detectedLanguage: string | null;
  sourceNote: string | null;
};

const ACCEPT_ATTRIBUTE = ALLOWED_FILE_EXTENSIONS.map((extension) => `.${extension}`).join(',');

export default function InputCard({
  value,
  onChange,
  onReadActiveTab,
  onSelectFile,
  onClear,
  file,
  fileError,
  isReading,
  detectedLanguage,
  sourceNote,
}: InputCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    // Reset so selecting the same file again re-triggers the change event.
    event.target.value = '';
    if (selected) onSelectFile(selected);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) onSelectFile(dropped);
  }

  const overLimit = value.length > MAX_SIMPLIFY_TEXT_LENGTH;

  return (
    <section className="brutal-card bg-white p-3">
      {/* ---- Document upload ---- */}
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center rounded-lg p-2.5 text-center transition-colors ${
          isDragging ? 'bg-saral-yellow/40' : 'bg-saral-lavender hover:bg-saral-lavenderHigh'
        }`}
      >
        <input
          ref={inputRef}
          id="saral-file-input"
          type="file"
          accept={ACCEPT_ATTRIBUTE}
          className="sr-only"
          onChange={handleFileChange}
        />
        <span className="brutal-card-sm mb-1.5 flex h-8 w-8 items-center justify-center bg-saral-yellow text-saral-ink">
          <UploadIcon className="text-[18px]" />
        </span>
        <p className="text-[12px] font-extrabold text-saral-ink">
          {file ? `Attached: ${file.name}` : 'Attach government document'}
        </p>
        <p className="mt-0.5 text-[10px] font-semibold text-saral-ink/60">
          {file
            ? `${formatBytes(file.size)} · ready to read`
            : `PDF, JPG, PNG, TXT, DOCX up to ${MAX_FILE_SIZE_MB}MB`}
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="btn-tactile brutal-pill-sm pointer-events-none mt-1.5 inline-flex items-center gap-1 bg-white px-3 py-1 text-[11px] font-bold text-saral-ink"
        >
          <PlusIcon className="text-[14px]" />
          <span>{file ? 'Choose another file' : 'Choose file'}</span>
        </button>
      </div>

      {fileError ? (
        <p role="alert" className="mt-1.5 text-[11px] font-bold text-red-700">
          {fileError}
        </p>
      ) : null}

      {/* ---- Divider ---- */}
      <div className="relative flex items-center justify-center py-2">
        <div className="h-0.5 w-full bg-saral-outline/60" />
        <span className="absolute bg-white px-3 text-[10px] font-bold uppercase tracking-widest text-saral-ink/50">
          or
        </span>
      </div>

      {/* ---- Text / URL ---- */}
      <div className="flex flex-col gap-1.5">
        <div className="relative">
          <label htmlFor="saral-text-input" className="sr-only">
            Paste circular text, a gazette excerpt, or a portal URL
          </label>
          <textarea
            id="saral-text-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            rows={3}
            spellCheck={false}
            aria-describedby="saral-text-meta"
            placeholder="Paste complex circular text, gazette excerpt, or portal URL..."
            className="scroll-area w-full resize-none rounded-lg bg-saral-lavender p-2.5 pr-9 text-[12px] font-medium text-saral-ink placeholder:text-saral-ink/40 focus:outline-none focus:bg-white focus:shadow-[2px_2px_0_0_#0D0D0D]"
          />
          {value ? (
            <button
              type="button"
              onClick={onClear}
              aria-label="Clear the text box"
              className="focus-ring absolute right-1.5 top-1.5 rounded-full p-1 text-saral-ink/50 hover:text-saral-ink"
            >
              <ClearIcon className="text-[15px]" />
            </button>
          ) : null}
        </div>

        <p id="saral-text-meta" className="text-[10px] font-semibold text-saral-ink/55">
          {value.length.toLocaleString()} / {MAX_SIMPLIFY_TEXT_LENGTH.toLocaleString()} characters
          {overLimit ? ' · too long, please shorten' : ''}
        </p>

        <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
          <button
            type="button"
            onClick={onReadActiveTab}
            disabled={isReading}
            className="btn-tactile brutal-pill-sm inline-flex items-center gap-1 bg-saral-lavenderHigh px-2.5 py-1 text-[11px] font-bold text-saral-ink disabled:opacity-50"
          >
            {isReading ? (
              <SpinnerIcon className="text-[14px] text-saral-ink" />
            ) : (
              <TabIcon className="text-[14px]" />
            )}
            <span>{isReading ? 'Reading page…' : 'Read Active Tab'}</span>
          </button>

          <p
            className="text-[10px] font-semibold text-saral-ink/55"
            title="Saral's backend detects the language when it reads a document or a URL. Translation is currently available in English and Kannada."
          >
            Language:{' '}
            <strong className="text-saral-ink">
              {detectedLanguage ? `${detectedLanguage} (detected)` : 'auto-detect'}
            </strong>
          </p>
        </div>

        {sourceNote ? (
          <p className="rounded-md bg-saral-lavender px-2 py-1 text-[10px] font-semibold text-saral-ink/70">
            {sourceNote}
          </p>
        ) : null}
      </div>
    </section>
  );
}
