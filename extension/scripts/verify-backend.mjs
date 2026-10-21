/**
 * Live verification of the extension's backend integration.
 *
 * This script exercises the real client code the popup uses
 * (`src/popup/api.ts` -> `src/background/api.ts`) against a running Saral
 * backend. The `chrome.runtime.sendMessage` bridge is stubbed with the real
 * background request handler, so the payloads and the response parsing are
 * exactly what the extension does in Chrome.
 *
 * Usage:
 *   node --import ./scripts/register-ts.mjs scripts/verify-backend.mjs
 *
 * Optional environment variables:
 *   SARAL_BASE_URL  backend base URL (default http://127.0.0.1:8000)
 */
import { performApiRequest } from '../src/background/api.ts';
import { saralApi } from '../src/services/api.ts';
import { joinUrl } from '../src/shared/config.ts';

const BASE_URL = process.env.SARAL_BASE_URL ?? 'http://127.0.0.1:8000';
const EXTENSION_ORIGIN = 'chrome-extension://abcdefghijklmnopqrstuvwxyz012345';

const ORIGINAL_TEXT =
  'Eligible applicants must submit the application before 31 December 2026. ' +
  'The assistance amount is ₹2,50,000. Applicants must be at least 18 years old and ' +
  'must submit Aadhaar, income certificate, and bank account details. ' +
  'The concerned District Officer may extend the deadline by fifteen days on genuine grounds.';

let passed = 0;
let failed = 0;

function check(name, condition, detail = '') {
  if (condition) {
    passed += 1;
    console.log(`  PASS  ${name}${detail ? ` — ${detail}` : ''}`);
  } else {
    failed += 1;
    console.log(`  FAIL  ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

// Stub the extension message bridge with the real background handler.
globalThis.chrome = {
  runtime: {
    sendMessage: async (message) => {
      if (message.kind === 'api-request') {
        return performApiRequest(BASE_URL, message);
      }
      if (message.kind === 'get-config') {
        return { ok: true, data: { baseUrl: BASE_URL } };
      }
      throw new Error(`Unsupported message: ${message.kind}`);
    },
  },
};

async function main() {
  console.log(`\nSaral extension — live backend verification against ${BASE_URL}\n`);

  /* ---------------------------------------------------------------- */
  console.log('1. Health + CORS from an extension origin');
  const health = await fetch(`${BASE_URL}/api/health`, { headers: { Origin: EXTENSION_ORIGIN } });
  const healthBody = await health.json();
  check('health endpoint responds', health.status === 200, `status ${health.status}`);
  check(
    'CORS allows the extension origin',
    health.headers.get('access-control-allow-origin') === EXTENSION_ORIGIN,
    String(health.headers.get('access-control-allow-origin')),
  );
  check('health payload has a status', typeof healthBody.status === 'string');

  /* ---------------------------------------------------------------- */
  console.log('\n2. Simplification (POST /api/documents/simplify)');
  let simplifiedText = '';
  let simplification = null;
  try {
    simplification = await saralApi.simplify(ORIGINAL_TEXT, 5);
    simplifiedText = simplification.simplified_text;
    check('simplify succeeds', simplification.success === true);
    check('simplified text is returned', typeof simplifiedText === 'string' && simplifiedText.length > 0, `${simplifiedText.length} chars`);
    check('model is reported', typeof simplification.model_used === 'string' && simplification.model_used.length > 0, simplification.model_used);
    check('preserved_facts is an array', Array.isArray(simplification.preserved_facts));
    check('validation_passed is a boolean', typeof simplification.validation_passed === 'boolean');
    check('document_id is returned', typeof simplification.document_id === 'string' && simplification.document_id.length > 0);
    check('key_terms is an array', Array.isArray(simplification.key_terms));
  } catch (error) {
    check('simplify succeeds', false, error.message);
  }

  /* ---------------------------------------------------------------- */
  console.log('\n3. Structured facts (POST /api/documents/extract-info)');
  try {
    const extracted = await saralApi.extractInfo(ORIGINAL_TEXT);
    const info = extracted.structured_information;
    check('extract-info succeeds', extracted.success === true);
    check('deadlines are extracted', Array.isArray(info.deadlines) && info.deadlines.length > 0, `${info.deadlines?.length ?? 0} found`);
    check('required documents are extracted', Array.isArray(info.required_documents) && info.required_documents.length > 0, `${info.required_documents?.length ?? 0} found`);
    check('amounts are extracted', Array.isArray(info.financial_information) && info.financial_information.length > 0, `${info.financial_information?.length ?? 0} found`);
  } catch (error) {
    check('extract-info succeeds', false, error.message);
  }

  /* ---------------------------------------------------------------- */
  console.log('\n4. Readability (POST /api/documents/readability)');
  if (simplifiedText) {
    try {
      const readability = await saralApi.readability(ORIGINAL_TEXT, simplifiedText, 5);
      check('readability succeeds', readability.success === true);
      check('readability is supported for English', readability.supported === true, String(readability.message ?? ''));
      check(
        'a real grade level is measured',
        typeof readability.simplified?.flesch_kincaid_grade === 'number',
        `grade ${readability.simplified?.flesch_kincaid_grade}`,
      );
    } catch (error) {
      check('readability succeeds', false, error.message);
    }
  }

  /* ---------------------------------------------------------------- */
  console.log('\n5. Translation (POST /api/translate)');
  if (simplifiedText) {
    try {
      const kannada = await saralApi.translate(simplifiedText, 'en', 'kn');
      check('translate succeeds', kannada.success === true);
      check('Kannada text is returned', typeof kannada.translated_text === 'string' && kannada.translated_text.length > 0, `${kannada.translated_text?.length ?? 0} chars`);
      check('target language is Kannada', kannada.target_language === 'kn');
      check(
        'the output is actually translated',
        kannada.translated_text !== simplifiedText,
      );
    } catch (error) {
      check('translate succeeds', false, error.message);
    }

    try {
      await saralApi.translate(simplifiedText, 'en', 'hi');
      check('the backend rejects Hindi', false, 'Hindi was accepted — the extension must not offer it');
    } catch (error) {
      check('the backend rejects Hindi (as the extension assumes)', true, error.message);
    }
  }

  /* ---------------------------------------------------------------- */
  console.log('\n6. Text to speech (POST /api/tts + GET /api/media/audio/...)');
  if (simplifiedText) {
    try {
      const speech = await saralApi.synthesizeSpeech(simplifiedText, 'en', 1);
      check('tts succeeds', speech.success === true);
      check('an audio url is returned', typeof speech.audio_url === 'string' && speech.audio_url.startsWith('/api/media/audio/'), speech.audio_url);
      check('a filename is returned', typeof speech.filename === 'string' && speech.filename.endsWith('.mp3'), speech.filename);
      check('the voice is reported', typeof speech.voice === 'string' && speech.voice.length > 0, speech.voice);

      const audioUrl = joinUrl(BASE_URL, speech.audio_url);
      const audio = await fetch(audioUrl);
      check('the generated audio is reachable', audio.status === 200, `status ${audio.status}`);
      check('the audio is served as mpeg', (audio.headers.get('content-type') ?? '').includes('audio/mpeg'), String(audio.headers.get('content-type')));
      const bytes = (await audio.arrayBuffer()).byteLength;
      check('the audio file has content', bytes > 0, `${bytes} bytes`);
    } catch (error) {
      check('tts succeeds', false, error.message);
    }
  }

  /* ---------------------------------------------------------------- */
  console.log('\n7. Error handling');
  try {
    await saralApi.simplify('', 5);
    check('empty text is rejected', false, 'the backend accepted empty text');
  } catch (error) {
    check('empty text is rejected', true, error.message.slice(0, 90));
  }

  try {
    await saralApi.extractUrl('http://127.0.0.1:8000/api/health');
    check('private URLs are rejected by the backend', false, 'a private URL was accepted');
  } catch (error) {
    check('private URLs are rejected by the backend', true, error.message.slice(0, 90));
  }

  console.log(`\nResult: ${passed} passed, ${failed} failed\n`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error('\nVerification crashed:', error);
  process.exit(1);
});
