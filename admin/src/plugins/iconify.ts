import { _api, addAPIProvider } from '@iconify/vue';

/**
 * Setup the iconify icon loader behavior.
 *
 * Key points (critical for "Page Not Responding" fix on first open):
 *  - If VITE_ICONIFY_URL is provided, treat it as private iconify mirror and register as default provider.
 *  - Otherwise, **fully disable remote icon fetch** by replacing the internal fetch() with a stub that
 *    immediately returns empty body — this prevents @iconify/vue from hanging on icon requests when
 *    the host has no outbound Internet access (e.g. production intranet / Docker isolated networks).
 *    Without this stub, the icon component waits on Promise<fetch> until the browser's TCP retransmit
 *    timeout (~8-12s) to iconify.design → the parent Vue Transition with mode="out-in" sees nested
 *    Icon components still in "pending" state and holds rendering of the actual slot content (pwd-login
 *    form) → Chrome shows the "Page Not Responding" dialog.
 *  - The stub is installed regardless of dev/prod mode because dev environments can also lose
 *    Internet connectivity unexpectedly.
 */
export function setupIconifyOffline() {
  const { VITE_ICONIFY_URL } = import.meta.env;

  if (VITE_ICONIFY_URL) {
    addAPIProvider('', { resources: [VITE_ICONIFY_URL] });
  } else {
    _api.setFetch(async (): Promise<Response> => {
      // Respond with an empty 200 Response so iconify treats it as "icons not available"
      // and immediately falls back instead of keeping Promise pending.
      return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
  }
}
