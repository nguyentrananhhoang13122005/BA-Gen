/**
 * JavaScript Animation Engine (BA-Gen Studio)
 * Sử dụng Web Animations API (WAAPI) & requestAnimationFrame (60fps)
 * Tôn trọng prefers-reduced-motion theo chuẩn Accessibility.
 */

import { useEffect, useState } from 'react';

export function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Hook đếm số chuyển động mượt 60fps bằng requestAnimationFrame (Quartic Ease-Out)
 */
export function useAnimatedNumber(targetValue, duration = 650) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const target = Number(targetValue) || 0;
    if (prefersReducedMotion()) {
      setDisplayValue(target);
      return;
    }

    let startTimestamp = null;
    let rafId = null;
    const startValue = 0;

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const elapsed = timestamp - startTimestamp;
      const progress = Math.min(elapsed / duration, 1);
      // Quartic ease-out: 1 - (1 - t)^4
      const eased = 1 - Math.pow(1 - progress, 4);
      const current = Math.round(startValue + (target - startValue) * eased);
      setDisplayValue(current);

      if (progress < 1) {
        rafId = window.requestAnimationFrame(step);
      }
    };

    rafId = window.requestAnimationFrame(step);
    return () => {
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, [targetValue, duration]);

  return displayValue;
}

/**
 * Hiệu ứng chuyển cảnh mượt khi đổi màn hình chính (View Transition)
 */
export function animateContainerEntrance(containerEl) {
  if (!containerEl || prefersReducedMotion() || !containerEl.animate) return;
  containerEl.animate(
    [
      { opacity: 0, transform: 'translateY(10px)' },
      { opacity: 1, transform: 'translateY(0px)' },
    ],
    {
      duration: 280,
      easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
      fill: 'both',
    }
  );
}

/**
 * Hiệu ứng xuất hiện nối tiếp (Staggered List Reveal) cho danh sách thẻ yêu cầu / kịch bản
 */
export function animateStaggerItems(containerEl, selector = '.js-stagger-item') {
  if (!containerEl || prefersReducedMotion()) return;
  const items = containerEl.querySelectorAll(selector);
  items.forEach((el, index) => {
    if (!el.animate) return;
    const delay = Math.min(index * 28, 280);
    el.animate(
      [
        { opacity: 0, transform: 'translateY(10px) scale(0.99)' },
        { opacity: 1, transform: 'translateY(0px) scale(1)' },
      ],
      {
        duration: 320,
        delay,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        fill: 'both',
      }
    );
  });
}

/**
 * Hiệu ứng chuyển đổi bảng chi tiết bên phải (Inspector Panel Transition)
 */
export function animateInspectorPanel(panelEl) {
  if (!panelEl || prefersReducedMotion() || !panelEl.animate) return;
  panelEl.animate(
    [
      { opacity: 0.25, transform: 'translateX(8px)' },
      { opacity: 1, transform: 'translateX(0px)' },
    ],
    {
      duration: 240,
      easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
      fill: 'both',
    }
  );
}

/**
 * Hiệu ứng nháy sáng xác nhận khi người dùng bấm "Áp dụng gợi ý SMART" hoặc "Lưu phân loại"
 */
export function animateSuccessFlash(targetEl) {
  if (!targetEl || prefersReducedMotion() || !targetEl.animate) return;
  targetEl.animate(
    [
      { boxShadow: '0 0 0 0 rgba(22, 163, 74, 0.55)', borderColor: '#16A34A' },
      { boxShadow: '0 0 0 10px rgba(22, 163, 74, 0)', borderColor: '#E2E8F0' },
    ],
    {
      duration: 650,
      easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
    }
  );
}
