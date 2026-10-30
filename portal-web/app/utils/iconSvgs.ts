/**
 * SVG icon library — replaces emoji-as-icon across C-end (Pre-Delivery Checklist:
 * "No Emoji as Structural Icons"). All icons share a consistent Lucide-style
 * stroke language (viewBox 24, stroke-width 1.8, currentColor) so they inherit
 * text color and scale with font-size via width/height 1em.
 */

const wrap = (inner: string) =>
  `<svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`

/* ---- Pet faces ---- */
export const petSvgs: Record<string, string> = {
  dog: wrap(
    `<circle cx="12" cy="13.5" r="6"/><path d="M8.5 9 6.5 4.5M15.5 9l2-4.5"/><circle cx="9.5" cy="12.5" r="1" fill="currentColor" stroke="none"/><circle cx="14.5" cy="12.5" r="1" fill="currentColor" stroke="none"/><path d="M10 16.5c1.3.8 2.7.8 4 0"/>`
  ),
  cat: wrap(
    `<circle cx="12" cy="13.5" r="5.5"/><path d="M8.5 9.5 6 4.5l3.5 3.5M15.5 9.5 18 4.5l-3.5 3.5"/><path d="M6.5 15.5H3.5M17.5 15.5h3M7 18.5 5 21M17 18.5l2 2.5"/>`
  ),
  bird: wrap(
    `<path d="M4.5 15c3.5 4 9.5 3 11-1.5 1.2-3-.5-5-2.5-4.2C13 6 9.5 4.5 7.5 5c-1 .8-.2 2.5 1 3.5-2 1-4.5 3.5-4 6.5z"/><circle cx="15.5" cy="9.5" r="1.4"/>`
  ),
  fish: wrap(
    `<path d="M4 12c3-4 11-4 14 0-3 4-11 4-14 0z"/><path d="M18 12h3M5 7.5 3 12l2 4.5"/>`
  ),
  rabbit: wrap(
    `<circle cx="12" cy="15" r="4.5"/><path d="M9 10c-.7-2.2.3-4.5 2-4.5s2 1.5 2 2.5M15 10c.7-2.2-.3-4.5-2-4.5s-2 1.5-2 2.5"/><path d="M9.5 17.5c1.7 1 3.3 1 5 0"/>`
  ),
  hamster: wrap(
    `<circle cx="12" cy="13" r="6"/><circle cx="9" cy="11.5" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="11.5" r="1" fill="currentColor" stroke="none"/><path d="M8 15c.5 1.3 1.6 2 2.8 2h2.4c1.2 0 2.3-.7 2.8-2"/>`
  ),
  paw: wrap(
    `<circle cx="9" cy="6" r="2"/><circle cx="16" cy="7" r="2"/><circle cx="4.5" cy="12" r="2"/><circle cx="19.5" cy="12" r="2"/><path d="M7.5 15.5c1.6-1 3.2-1.3 4.5-1.3s2.9.3 4.5 1.3c1.3.9 2 2.1 2 3.3 0 1.7-1.4 3-3 3-1.1 0-1.8-.5-3.5-.5s-2.4.5-3.5.5c-1.6 0-3-1.3-3-3 0-1.2.7-2.4 2-3.3z"/>`
  ),
}

/* ---- Product category icons ---- */
export const productSvgs: Record<string, string> = {
  food: wrap(
    `<path d="M4 10h16a8 8 0 0 1-16 0z"/><path d="M7 10c0-3 2.5-5 5-5s5 2 5 5"/><path d="M9.5 14v3M14.5 14v3"/>`
  ),
  toy: wrap(
    `<circle cx="12" cy="12" r="8"/><path d="M4.5 12h15M12 4c-3 3-3 14 0 17M12 4c3 3 3 14 0 17"/>`
  ),
  bed: wrap(
    `<path d="M3 7.5v11M21 7.5v11M3 12h18"/><path d="M3 16.5h18"/><path d="M6 9.5c1.5-2 3.5-2 5 0M13 9.5c1.5-2 3.5-2 5 0"/>`
  ),
  leash: wrap(
    `<circle cx="12" cy="6" r="2.5"/><path d="M12 8.5V16"/><circle cx="12" cy="18.5" r="2.5"/><path d="M9.5 20.5 7 22.5M14.5 20.5 17 22.5"/>`
  ),
  grooming: wrap(
    `<rect x="4" y="4" width="16" height="7" rx="2"/><path d="M7 11v8M11 11v8M15 11v8M17 11v6"/>`
  ),
  health: wrap(
    `<path d="M10.5 20.5a4.5 4.5 0 0 1-6.4-6.4l12-12a4.5 4.5 0 0 1 6.4 6.4z"/><path d="M8.5 16.5 16 9"/>`
  ),
  litter: wrap(
    `<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><path d="M10 14v2M14 14v2"/>`
  ),
  box: wrap(
    `<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12 20.7 7"/><path d="M12 22V12"/>`
  ),
  cart: wrap(
    `<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>`
  ),
  chat: wrap(
    `<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>`
  ),
  package: wrap(
    `<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12 20.7 7"/><path d="M12 22V12"/>`
  ),
}

/* ---- Category mapping helpers (return SVG string) ---- */
export function productIcon(name: string): string {
  const n = (name || '').toLowerCase()
  if (n.includes('food') || n.includes('kibble') || n.includes('treat') || n.includes('snack')) return productSvgs.food
  if (n.includes('toy') || n.includes('ball') || n.includes('chew') || n.includes('play')) return productSvgs.toy
  if (n.includes('bed') || n.includes('crate') || n.includes('nest') || n.includes('house')) return productSvgs.bed
  if (n.includes('collar') || n.includes('leash') || n.includes('harness') || n.includes('wear')) return productSvgs.leash
  if (n.includes('shampoo') || n.includes('brush') || n.includes('groom') || n.includes('care')) return productSvgs.grooming
  if (n.includes('health') || n.includes('vitamin') || n.includes('supplement') || n.includes('med')) return productSvgs.health
  if (n.includes('litter') || n.includes('pad') || n.includes('potty') || n.includes('clean')) return productSvgs.litter
  return productSvgs.box
}

export function petIcon(type: string): string {
  return petSvgs[(type || '').toLowerCase()] || petSvgs.paw
}

/** Smart pet type mapping by breed keywords (pets.vue). */
export function petTypeByBreed(breed: string): string {
  const b = (breed || '').toLowerCase()
  if (b.includes('retriever') || b.includes('labrador') || b.includes('bulldog') || b.includes('shepherd') || b.includes('poodle') || b.includes('terrier') || b.includes('husky') || b.includes('chihuahua') || b.includes('beagle') || b.includes('dog')) return petSvgs.dog
  if (b.includes('siamese') || b.includes('persian') || b.includes('maine') || b.includes('ragdoll') || b.includes('cat') || b.includes('kitten')) return petSvgs.cat
  if (b.includes('parrot') || b.includes('budgie') || b.includes('bird') || b.includes('cockatiel')) return petSvgs.bird
  if (b.includes('fish') || b.includes('goldfish')) return petSvgs.fish
  if (b.includes('rabbit') || b.includes('bunny')) return petSvgs.rabbit
  if (b.includes('hamster') || b.includes('guinea') || b.includes('mouse') || b.includes('rat')) return petSvgs.hamster
  return petSvgs.paw
}

/** Standalone large icons for empty states. */
export function emptyStateIcon(kind: 'cart' | 'chat' | 'paw' | 'package'): string {
  return productSvgs[kind] || petSvgs[kind] || petSvgs.paw
}
