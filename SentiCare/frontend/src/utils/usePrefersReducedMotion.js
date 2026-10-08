import { useEffect, useState } from "react";

export default function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const canListen = typeof window !== "undefined" && "matchMedia" in window;
    if (!canListen) {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    function updatePrefersReducedMotion() {
      setPrefersReducedMotion(() => mediaQuery.matches);
    }
    mediaQuery.addEventListener("change", updatePrefersReducedMotion);
    updatePrefersReducedMotion();
    return () =>
      mediaQuery.removeEventListener("change", updatePrefersReducedMotion);
  }, []);

  return prefersReducedMotion;
}
