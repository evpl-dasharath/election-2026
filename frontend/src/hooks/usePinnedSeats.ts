import { useState } from 'react';

const STORAGE_KEY = 'pinned_seats';
const MAX_PINS = 10;

/**
 * Manages up to 14 pinned constituency IDs in localStorage.
 */
export function usePinnedSeats() {
  const [pinned, setPinned] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
      return [];
    }
  });

  const toggle = (id: string) => {
    setPinned(prev => {
      const next = prev.includes(id)
        ? prev.filter(x => x !== id)
        : prev.length < MAX_PINS
          ? [...prev, id]
          : prev; // silently ignore if at limit
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // localStorage unavailable (private mode, storage full, etc.)
      }
      return next;
    });
  };

  const isPinned = (id: string) => pinned.includes(id);

  return { pinned, toggle, isPinned };
}
