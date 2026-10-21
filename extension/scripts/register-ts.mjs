/**
 * Registers the TypeScript resolution hook used by the extension test suite.
 */
import { register } from 'node:module';
import { pathToFileURL } from 'node:url';

register('./ts-resolve-hook.mjs', pathToFileURL('./scripts/'));
