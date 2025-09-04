/**
 * Hook for preloading battle images to improve UX
 */

import { useEffect, useState } from 'react';
import { imageCache } from '../utils/imageCache';

interface BattleCard {
  firebase_image_url?: string;
  name: string;
}

interface UseImagePreloaderResult {
  preloadComplete: boolean;
  preloadedCount: number;
  totalCount: number;
  preloadProgress: number;
}

export const useImagePreloader = (cards: BattleCard[]): UseImagePreloaderResult => {
  const [preloadComplete, setPreloadComplete] = useState(false);
  const [preloadedCount, setPreloadedCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    const validCards = cards.filter(card => 
      card.firebase_image_url && card.firebase_image_url.trim() !== ''
    );

    setTotalCount(validCards.length);
    setPreloadedCount(0);
    setPreloadComplete(false);

    if (validCards.length === 0) {
      setPreloadComplete(true);
      return;
    }

    let completed = 0;

    const preloadPromises = validCards.map(async (card) => {
      try {
        if (card.firebase_image_url) {
          await imageCache.preload(card.firebase_image_url);
        }
        completed++;
        setPreloadedCount(completed);
      } catch (error) {
        // Image failed to load, but still count as "processed"
        completed++;
        setPreloadedCount(completed);
        console.warn(`Failed to preload image for ${card.name}:`, error);
      }
    });

    Promise.allSettled(preloadPromises).then(() => {
      setPreloadComplete(true);
    });

  }, [cards]);

  return {
    preloadComplete,
    preloadedCount,
    totalCount,
    preloadProgress: totalCount > 0 ? (preloadedCount / totalCount) * 100 : 100
  };
};

/**
 * Hook for preloading specific image URLs
 */
export const useImageUrlPreloader = (urls: string[]): UseImagePreloaderResult => {
  const cards = urls.map(url => ({ firebase_image_url: url, name: 'preload' }));
  return useImagePreloader(cards);
};