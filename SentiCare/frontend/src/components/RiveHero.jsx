import { useEffect, useRef } from "react";
import {
  useRive,
  useStateMachineInput,
  Layout,
  Fit,
  Alignment,
} from "@rive-app/react-canvas";

import useMediaQuery from "../utils/useMediaBreakpoint";
import usePrefersReducedMotion from "../utils/usePrefersReducedMotion";
import RiveButton from "./RiveButton";

export default function RiveHero() {
  const initializedRef = useRef(false);

  const lgQuery = useMediaQuery("only screen and (min-width: 1025px)");
  const prefersReducedMotion = usePrefersReducedMotion();

  const {
    rive,
    setCanvasRef,
    setContainerRef,
    canvas: canvasRef,
    container: canvasContainerRef,
  } = useRive(
    {
      src: "/hero_use_case.riv",
      artboard: "Hero Demo Listeners Resize",
      stateMachines: "State Machine 1",
      layout: new Layout({
        fit: Fit.Cover,
        alignment: Alignment.Center,
      }),
      autoplay: true,
    },
    {
      shouldResizeCanvasToContainer: true,
    }
  );

  useEffect(() => {
    if (rive) {
      // Always use Cover fit for full screen coverage
      rive.layout = new Layout({
        fit: Fit.Cover,
        alignment: Alignment.Center,
      });
    }
  }, [rive, lgQuery]);

  const numX = useStateMachineInput(rive, "State Machine 1", "numX", 50);
  const numY = useStateMachineInput(rive, "State Machine 1", "numY", 50);
  const numSize = useStateMachineInput(rive, "State Machine 1", "numSize", 0);

  useEffect(() => {
    if (rive) {
      prefersReducedMotion ? rive.pause() : rive.play();
    }
  }, [rive, prefersReducedMotion]);

  // Simplified: Let Rive handle canvas resizing automatically
  useEffect(() => {
    if (rive && canvasRef && canvasContainerRef && !initializedRef.current) {
      initializedRef.current = true;
      rive.startRendering();
    }
  }, [rive, canvasRef, canvasContainerRef]);

  // Simple window resize handler for Rive inputs only
  useEffect(() => {
    if (!rive || !numSize) return;

    const handleWindowResize = () => {
      const newWidth = window.innerWidth;

      // Update size input based on screen width
      if (newWidth <= 1200) {
        const resizeRange = 1200 - 500;
        numSize.value = ((1200 - newWidth) / resizeRange) * 100;
      } else {
        numSize.value = 0;
      }
    };

    // Initial call
    handleWindowResize();

    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, [rive, numSize]);

  const onMouseMove = (e) => {
    // Early return if inputs are not ready
    if (!numX || !numY || !rive) {
      return;
    }

    try {
      const maxWidth = window.innerWidth;
      const maxHeight = window.innerHeight;

      // Ensure we have valid dimensions
      if (maxWidth > 0 && maxHeight > 0) {
        numX.value = (e.clientX / maxWidth) * 100;
        numY.value = 100 - (e.clientY / maxHeight) * 100;
      }
    } catch (error) {
      console.warn("Mouse move error:", error);
    }
  };

  return (
    <div
      className="bg-[#09090E] fixed inset-0 rive-canvas-container overflow-hidden"
      ref={setContainerRef}
      onMouseMove={onMouseMove}
    >
      <canvas
        className="bg-[#09090E] rive-canvas w-full h-full"
        ref={setCanvasRef}
        aria-label="Hero element for the Explore page; an interactive graphic showing planets thru a spacesuit visor"
      ></canvas>
      <RiveButton />
    </div>
  );
}
