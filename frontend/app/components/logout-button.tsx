'use client';

import { clearAuthSession, clearServerSession, STORAGE_SUPER_ADMIN_KEY } from '../lib/api-client';

export default function LogoutButton() {
  return (
    <button
      type="button"
      className="institutional-pill"
      onClick={() => {
        clearAuthSession();
        if (globalThis.window) {
          globalThis.sessionStorage?.removeItem(STORAGE_SUPER_ADMIN_KEY);
          void clearServerSession().finally(() => {
            globalThis.location.href = '/';
          });
        }
      }}
    >
      Logout
    </button>
  );
}
