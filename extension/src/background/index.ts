/**
 * Saral background service worker.
 *
 * Responsibilities:
 *  - own the backend base URL (persisted in chrome.storage.local),
 *  - perform every HTTP call to the FastAPI backend,
 *  - inject the content script on demand and collect readable page text,
 *  - expose the Alt+S keyboard command.
 */
import { performApiRequest } from './api';
import {
  DEFAULT_BASE_URL,
  STORAGE_KEY,
  toHostPermission,
  validateBaseUrl,
} from '../shared/config';
import type {
  BackgroundRequestMessage,
  ExtensionConfig,
  ExtractedContent,
  SaralEnvelope,
} from '../types/messages';

const CONTENT_SCRIPT_FILE = 'content.js';

/** Pages that Chrome does not let extensions read. */
const UNSUPPORTED_PROTOCOLS = ['chrome:', 'chrome-untrusted:', 'edge:', 'about:', 'devtools:'];

async function loadConfig(): Promise<ExtensionConfig> {
  try {
    const stored = await chrome.storage.local.get(STORAGE_KEY);
    const value = stored[STORAGE_KEY] as Partial<ExtensionConfig> | undefined;
    if (value && typeof value.baseUrl === 'string' && value.baseUrl.trim()) {
      return { baseUrl: value.baseUrl.replace(/\/+$/, '') };
    }
  } catch {
    // Fall through to the default below.
  }
  return { baseUrl: DEFAULT_BASE_URL };
}

async function saveConfig(baseUrl: string): Promise<ExtensionConfig> {
  const config: ExtensionConfig = { baseUrl };
  await chrome.storage.local.set({ [STORAGE_KEY]: config });
  return config;
}

function unsupportedPageError(url: string | undefined): SaralEnvelope<never> {
  const host = url ? safeHost(url) : 'this page';
  return {
    ok: false,
    error: {
      code: 'UNSUPPORTED_PAGE',
      message: `Saral cannot read ${host}. Chrome blocks extensions on browser settings, the web store and other restricted pages. Open a normal website and try again.`,
      status: 0,
    },
  };
}

function safeHost(url: string): string {
  try {
    return new URL(url).hostname || 'this page';
  } catch {
    return 'this page';
  }
}

function isReadableUrl(url: string | undefined): boolean {
  if (!url) return false;
  const lower = url.toLowerCase();
  if (UNSUPPORTED_PROTOCOLS.some((protocol) => lower.startsWith(protocol))) return false;
  return lower.startsWith('http://') || lower.startsWith('https://');
}

/**
 * Injects the content script into the active tab and asks it for the readable
 * text of the page (or the current selection when the user highlighted one).
 */
async function extractActiveTab(): Promise<SaralEnvelope<ExtractedContent>> {
  let tabs: chrome.tabs.Tab[];
  try {
    tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  } catch {
    tabs = [];
  }

  const tab = tabs[0];
  if (!tab || typeof tab.id !== 'number') {
    return {
      ok: false,
      error: {
        code: 'NO_ACTIVE_TAB',
        message: 'Saral could not find the active tab. Open the page you want to read and try again.',
        status: 0,
      },
    };
  }

  if (!isReadableUrl(tab.url)) {
    return unsupportedPageError(tab.url);
  }

  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: [CONTENT_SCRIPT_FILE] });
  } catch {
    return {
      ok: false,
      error: {
        code: 'CONTENT_SCRIPT_BLOCKED',
        message:
          'Chrome blocked Saral from reading this page. Pages such as the Chrome Web Store, PDF viewer and browser settings cannot be read by extensions.',
        status: 0,
      },
    };
  }

  try {
    const response = await chrome.tabs.sendMessage<{ kind: 'extract-content' }, SaralEnvelope<ExtractedContent>>(
      tab.id,
      { kind: 'extract-content' },
    );

    if (!response) {
      return {
        ok: false,
        error: {
          code: 'NO_RESPONSE',
          message: 'Saral did not receive a response from the page. Reload the tab and try again.',
          status: 0,
        },
      };
    }
    return response;
  } catch {
    return {
      ok: false,
      error: {
        code: 'CONTENT_SCRIPT_UNAVAILABLE',
        message:
          'Saral could not talk to the page. Reload the tab, then click “Read Active Tab” again.',
        status: 0,
      },
    };
  }
}

async function handleRequest(
  message: BackgroundRequestMessage,
): Promise<SaralEnvelope<unknown>> {
  switch (message.kind) {
    case 'api-request': {
      const config = await loadConfig();
      return performApiRequest(config.baseUrl, message);
    }

    case 'extract-active-tab':
      return extractActiveTab() as Promise<SaralEnvelope<unknown>>;

    case 'get-config': {
      const config = await loadConfig();
      return { ok: true, data: config };
    }

    case 'set-config': {
      const validation = validateBaseUrl(message.baseUrl);
      if (!validation.ok || !validation.value) {
        return {
          ok: false,
          error: {
            code: 'INVALID_BASE_URL',
            message: validation.message ?? 'That backend address is not valid.',
            status: 0,
          },
        };
      }

      const baseUrl = validation.value;

      // Ask for host access only when the user points Saral at a new host.
      const permission = toHostPermission(baseUrl);
      if (permission) {
        try {
          const granted = await chrome.permissions.request({ origins: [permission] });
          if (!granted) {
            return {
              ok: false,
              error: {
                code: 'PERMISSION_DENIED',
                message: `Saral needs access to ${permission} to reach that backend. The address was not saved.`,
                status: 0,
              },
            };
          }
        } catch {
          // permissions.request throws outside a user gesture; fall through and
          // still persist the address so the user can retry from the banner.
        }
      }

      const config = await saveConfig(baseUrl);
      return { ok: true, data: config };
    }

    default: {
      const exhaustive: never = message;
      return exhaustive;
    }
  }
}

chrome.runtime.onMessage.addListener(
  (message: BackgroundRequestMessage, _sender, sendResponse) => {
    if (!message || typeof message !== 'object' || !('kind' in message)) {
      sendResponse({
        ok: false,
        error: { code: 'BAD_MESSAGE', message: 'Unknown request.', status: 0 },
      });
      return false;
    }

    handleRequest(message)
      .then((envelope) => sendResponse(envelope))
      .catch(() =>
        sendResponse({
          ok: false,
          error: {
            code: 'UNEXPECTED_ERROR',
            message: 'Saral hit an unexpected problem. Please try again.',
            status: 0,
          },
        }),
      );

    return true;
  },
);

// Alt+S opens the popup so the user can immediately read the active tab.
if (chrome.commands && typeof chrome.action?.openPopup === 'function') {
  chrome.commands.onCommand.addListener((command) => {
    if (command !== 'read-active-tab') return;
    chrome.action.openPopup().catch(() => {
      /* Older Chrome builds cannot open the popup programmatically. */
    });
  });
}
