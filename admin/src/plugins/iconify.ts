import { _api, addAPIProvider, addCollection } from '@iconify/vue';

/**
 * 100% offline icon provider for the admin client.
 *
 * Background (why we hand-copy the two mini collections below instead of
 * importing @iconify/json wholesale):
 *   1. `@iconify/json/json/material-symbols.json` is 8.4 MB and `heroicons.json`
 *      is 627 KB. Pulling them wholesale through Vite's JSON loader bloats the
 *      initial vendor chunk — most of those 16k+ icons are never referenced.
 *   2. Even when those big JSONs import correctly, `addCollection(wholeSet)` can
 *      silently fail in some @iconify/vue builds because the JSON shape includes
 *      optional fields (info / aliases / suffixes) that are not part of the strict
 *      IconifyJSON contract. The symptom: icons are visibly blank — exactly the
 *      "all icons missing" report we received.
 *   3. By hand-copying only the 6 + 2 entries actually used by ThemeSchemaSwitch
 *      and LangSwitch, we get a sub-5 KB bundle delta, predictable icon bodies,
 *      and zero surprises from @iconify/vue's internal storage shaper.
 *
 * Priority of icon resolution:
 *   1. The two inline mini collections (always wins, 100% offline).
 *   2. VITE_ICONIFY_URL (optional, corporate mirror for any extra icon added
 *      later without having to redeploy a new offline list).
 *   3. Fallback stub (otherwise). Any remaining icon names return an empty
 *      icon body instead of hanging 8-12s on iconify CDN calls.
 */

/* eslint-disable max-len */
type MiniIconSet = { prefix: string; width: number; height: number; icons: Record<string, { body: string }> };

/**
 * Only the 6 material-symbols entries actually referenced in the UI today:
 *   sunny               (light theme  → ThemeSchemaSwitch)
 *   nightlight-rounded  (dark theme   → ThemeSchemaSwitch)
 *   hdr-auto            (auto theme   → ThemeSchemaSwitch)
 *   dark-mode / sunny-outline / dark-mode-outline  (kept so common dark/light
 *      variations keep resolving if a future page references them.)
 */
const MATERIAL_MINI: MiniIconSet = {
  prefix: 'material-symbols',
  width: 24,
  height: 24,
  icons: {
    sunny: {
      body:
        '<path fill="currentColor" d="M11 5V1h2v4zm6.65 2.75l-1.375-1.375l2.8-2.875l1.4 1.425zM19 13v-2h4v2zm-8 10v-4h2v4zM6.35 7.7L3.5 4.925l1.425-1.4L7.75 6.35zm12.7 12.8l-2.775-2.875l1.35-1.35l2.85 2.75zM1 13v-2h4v2zm3.925 7.5l-1.4-1.425l2.8-2.8l.725.675l.725.7zm2.825-4.25Q6 14.5 6 12t1.75-4.25T12 6t4.25 1.75T18 12t-1.75 4.25T12 18t-4.25-1.75"/>'
    },
    'nightlight-rounded': {
      body:
        '<path fill="currentColor" d="M14 22q-2.075 0-3.9-.788t-3.175-2.137T4.788 15.9T4 12t.788-3.9t2.137-3.175T10.1 2.788T14 2q.875 0 1.75.175t1.675.525q.3.125.45.387t.15.538q0 .225-.088.425t-.287.35q-1.75 1.375-2.7 3.375T14 12q0 2.25.925 4.25t2.7 3.35q.2.15.288.363T18 20.4q0 .275-.15.538t-.45.387q-.8.35-1.662.513T14 22"/>'
    },
    'hdr-auto': {
      body:
        '<path fill="currentColor" d="M6.9 17h1.9l1-2.8h4.4l1 2.8h1.9L13 6h-2zm3.45-4.4l1.6-4.55h.1l1.6 4.55zM12 22q-2.075 0-3.9-.788t-3.175-2.137T2.788 15.9T2 12t.788-3.9t2.137-3.175T8.1 2.788T12 2t3.9.788t3.175 2.137T21.213 8.1T22 12t-.788 3.9t-2.137 3.175t-3.175 2.138T12 22"/>'
    },
    'dark-mode': {
      body:
        '<path fill="currentColor" d="M12 21q-3.75 0-6.375-2.625T3 12t2.625-6.375T12 3q.35 0 .688.025t.662.075q-1.025.725-1.638 1.888T11.1 7.5q0 2.25 1.575 3.825T16.5 12.9q1.375 0 2.525-.613T20.9 10.65q.05.325.075.662T21 12q0 3.75-2.625 6.375T12 21"/>'
    },
    'sunny-outline': {
      body:
        '<path fill="currentColor" d="M11 5V1h2v4zm6.65 2.75l-1.375-1.375l2.8-2.875l1.4 1.425zM19 13v-2h4v2zm-8 10v-4h2v4zM6.35 7.7L3.5 4.925l1.425-1.4L7.75 6.35zm12.7 12.8l-2.775-2.875l1.35-1.35l2.85 2.75zM1 13v-2h4v2zm3.925 7.5l-1.4-1.425l2.8-2.8l.725.675l.725.7zm2.825-4.25Q6 14.5 6 12t1.75-4.25T12 6t4.25 1.75T18 12t-1.75 4.25T12 18t-4.25-1.75m7.075-1.425Q16 13.65 16 12t-1.175-2.825T12 8T9.175 9.175T8 12t1.175 2.825T12 16t2.825-1.175M12 12"/>'
    },
    'dark-mode-outline': {
      body:
        '<path fill="currentColor" d="M12 21q-3.75 0-6.375-2.625T3 12t2.625-6.375T12 3q.35 0 .688.025t.662.075q-1.025.725-1.638 1.888T11.1 7.5q0 2.25 1.575 3.825T16.5 12.9q1.375 0 2.525-.613T20.9 10.65q.05.325.075.662T21 12q0 3.75-2.625 6.375T12 21m0-2q2.2 0 3.95-1.213t2.55-3.162q-.5.125-1 .2t-1 .075q-3.075 0-5.238-2.163T9.1 7.5q0-.5.075-1t.2-1q-1.95.8-3.163 2.55T5 12q0 2.9 2.05 4.95T12 19m-.25-6.75"/>'
    }
  }
};

/**
 * Only the 2 heroicons entries actually referenced in the UI today:
 *   language         (language switcher → LangSwitch via <SvgIcon icon="heroicons:language">)
 *   language-solid   (kept in case a designer prefers solid variant)
 */
const HEROICONS_MINI: MiniIconSet = {
  prefix: 'heroicons',
  width: 24,
  height: 24,
  icons: {
    language: {
      body:
        '<path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="m10.5 21l5.25-11.25L21 21m-9-3h7.5M3 5.621a49 49 0 0 1 6-.371m0 0q1.681 0 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138q1.344.092 2.666.257m-4.589 8.495a18 18 0 0 1-3.827-5.802"/>'
    },
    'language-solid': {
      body:
        '<path fill="currentColor" fill-rule="evenodd" d="M9 2.25a.75.75 0 0 1 .75.75v1.506a49 49 0 0 1 5.343.371a.75.75 0 1 1-.186 1.489q-.99-.124-1.99-.206a18.7 18.7 0 0 1-2.97 6.323q.476.576 1 1.108a.75.75 0 0 1-1.07 1.05A19 19 0 0 1 9 13.688a18.8 18.8 0 0 1-5.656 4.482a.75.75 0 0 1-.688-1.333a17.3 17.3 0 0 0 5.396-4.353A18.7 18.7 0 0 1 5.89 8.598a.75.75 0 0 1 1.388-.568A17.2 17.2 0 0 0 9 11.224a17.2 17.2 0 0 0 2.391-5.165a48 48 0 0 0-8.298.307a.75.75 0 0 1-.186-1.489a49 49 0 0 1 5.343-.371V3A.75.75 0 0 1 9 2.25M15.75 9a.75.75 0 0 1 .68.433l5.25 11.25a.75.75 0 1 1-1.36.634l-1.198-2.567h-6.744l-1.198 2.567a.75.75 0 0 1-1.36-.634l5.25-11.25A.75.75 0 0 1 15.75 9m-2.672 8.25h5.344l-2.672-5.726z" clip-rule="evenodd"/>'
    }
  }
};
/* eslint-enable max-len */

export function setupIconifyOffline() {
  const { VITE_ICONIFY_URL } = import.meta.env;

  // 1) Always register the two mini collections first — 100% offline, sub-5 KB total.
  //    Guard each addCollection() return value so a silent failure (for example if
  //    @iconify/vue changes its storage contract) is surfaced in the dev console
  //    instead of mysteriously rendering empty icons.
  const okMaterial = addCollection(MATERIAL_MINI);
  const okHero = addCollection(HEROICONS_MINI);
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug('[iconify] offline registered:', { material: okMaterial, heroicons: okHero });
  }

  if (VITE_ICONIFY_URL) {
    // 2) Corporate mirror — any icons not in the two mini lists can be fetched
    //    internally (e.g. new marketing icons added before a redeploy).
    addAPIProvider('', { resources: [VITE_ICONIFY_URL] });
  } else {
    // 3) Fallback stub — prevent any remaining icon name lookups from issuing
    //    hanging outbound iconify.design calls. Returns an empty JSON payload so
    //    @iconify/vue short-circuits and renders a 0-shape icon (no DOM block).
    _api.setFetch(async (): Promise<Response> => {
      return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
  }
}
