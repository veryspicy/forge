import { _api, addAPIProvider, addCollection } from '@iconify/vue';
import materialSymbols from '@iconify/json/json/material-symbols.json';
import heroicons from '@iconify/json/json/heroicons.json';

/**
 * Setup iconify icons: prefer 100% offline collections registered via addCollection().
 *
 * The previous hotfix used `_api.setFetch` to stub remote fetches with an empty
 * response, which prevented 8-12s hanging on air-gapped hosts but also made all
 * remote icons invisible (empty placeholders). This upgrade makes the icon set
 * truly local by bundling the two icon prefixes the UI actually uses:
 *
 *   - prefix "material-symbols" : e.g. material-symbols:sunny (theme switcher)
 *   - prefix "heroicons"        : e.g. heroicons:language      (language switcher)
 *
 * Both JSON files are re-exported from `@iconify/json` which is already a
 * devDependency (see package.json → "@iconify/json": "2.2.472"). Importing them
 * here makes Vite inline the (tree-shaken) subsets into the initial vendor
 * chunk; the two files are ~300KB combined which is negligible for the admin
 * bundle and buys us zero runtime network dependency on iconify CDNs.
 *
 * Priority order:
 *   1. addCollection()                – always-on, matches the two bundled prefixes
 *   2. VITE_ICONIFY_URL (mirror)      – if provided, additional icon sets can be
 *                                       fetched from the internal private mirror
 *   3. else (no mirror configured)    – fallback stub: disable remote fetches so
 *                                       any unregistered icon name resolves to an
 *                                       empty placeholder instead of hanging 8-12s
 *                                       on outbound DNS / TCP
 */
export function setupIconifyOffline() {
  const { VITE_ICONIFY_URL } = import.meta.env;

  // 1) Bundled offline collections – always register first.
  //    @iconify/json stores per-prefix JSONs already shaped as IconifyJSON.
  //    `as never` casts silence TS's strict-json mismatch for deeply nested
  //    {width,height} fields without pulling @iconify/types at runtime.
  addCollection(materialSymbols as never);
  addCollection(heroicons as never);

  if (VITE_ICONIFY_URL) {
    // 2) Internal mirror: additional requests for unregistered prefixes go here.
    addAPIProvider('', { resources: [VITE_ICONIFY_URL] });
  } else {
    // 3) Stub fallback – any icon name outside the two registered prefixes still
    //    must NOT produce a hanging fetch.
    _api.setFetch(async (): Promise<Response> => {
      return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
  }
}
