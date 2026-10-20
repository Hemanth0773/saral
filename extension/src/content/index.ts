/**
 * On-demand content script.
 *
 * The script is injected by the background service worker with
 * `chrome.scripting.executeScript` only when the user explicitly asks Saral to
 * read the active tab. Nothing is collected in the background and no page
 * content ever leaves the browser without a deliberate user action.
 */
import { extractReadableContent } from './extractor';
import type { ContentRequestMessage, ExtractedContent, SaralEnvelope } from '../types/messages';

const INJECTED_FLAG = '__saralContentScriptReady';

interface SaralWindow extends Window {
  [INJECTED_FLAG]?: boolean;
}

const scope = window as SaralWindow;

if (!scope[INJECTED_FLAG]) {
  scope[INJECTED_FLAG] = true;

  chrome.runtime.onMessage.addListener(
    (message: ContentRequestMessage, _sender, sendResponse) => {
      if (!message || message.kind !== 'extract-content') return false;

      try {
        const data: ExtractedContent = extractReadableContent();
        const envelope: SaralEnvelope<ExtractedContent> = { ok: true, data };
        sendResponse(envelope);
      } catch {
        const envelope: SaralEnvelope<ExtractedContent> = {
          ok: false,
          error: {
            code: 'EXTRACTION_FAILED',
            message: 'Saral could not read the text on this page.',
            status: 0,
          },
        };
        sendResponse(envelope);
      }

      return false;
    },
  );
}
