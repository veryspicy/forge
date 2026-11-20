// Forge — 游客标识（游客态会话归属用；登录后会被后端认领到账号）
const STORAGE_KEY = "forge_guest_key";

export function useGuestKey(): string | null {
  if (!import.meta.client) return null;
  try {
    let key = localStorage.getItem(STORAGE_KEY);
    if (!key) {
      const uuid =
        globalThis.crypto?.randomUUID?.() ??
        `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
      key = `guest-${uuid}`;
      localStorage.setItem(STORAGE_KEY, key);
    }
    return key;
  } catch {
    return null;
  }
}
