"use client";

import React, { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  depth: number;
  baseSize: number;
  spriteKey: string;
  alpha: number;
  wobbleSpeed: number;
  wobbleOffset: number;
}

export const AmbientMotionBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    let animationFrameId: number;
    let isVisible = true;
    let width = 0;
    let height = 0;
    let dpr = 1;

    // Mouse coordinates & lerped tracking
    let targetMouseX = -1000;
    let targetMouseY = -1000;
    let currentMouseX = -1000;
    let currentMouseY = -1000;
    let mouseVelocity = 0;
    let lastEventX = -1000;
    let lastEventY = -1000;
    let lastEventTime = performance.now();
    let hasMouseMoved = false;

    // --- Sprite Cache (Offscreen GPU Texture Optimization) ---
    // Pre-rendering shapes to offscreen canvases so the render loop uses fast drawImage()
    const spriteCache: Record<string, HTMLCanvasElement> = {};

    const SPRITE_CONFIGS = [
      { key: "mint-glow", color: "#00F5A0", glow: "rgba(0, 245, 160, 0.4)", shape: "circle" },
      { key: "mint-diamond", color: "#00F5A0", glow: "rgba(0, 245, 160, 0.3)", shape: "diamond" },
      { key: "azure-glow", color: "#0070F3", glow: "rgba(0, 112, 243, 0.4)", shape: "circle" },
      { key: "cyan-spec", color: "#38BDF8", glow: "rgba(56, 189, 248, 0.3)", shape: "circle" },
      { key: "white-spec", color: "#F8FAFC", glow: "rgba(248, 250, 252, 0.2)", shape: "circle" },
    ];

    const initSpriteCache = () => {
      const size = 32;
      const center = size / 2;

      SPRITE_CONFIGS.forEach((cfg) => {
        const offCanvas = document.createElement("canvas");
        offCanvas.width = size;
        offCanvas.height = size;
        const offCtx = offCanvas.getContext("2d");
        if (!offCtx) return;

        // Baked radial shadow for weightless neon luminescence
        offCtx.shadowColor = cfg.glow;
        offCtx.shadowBlur = 8;
        offCtx.fillStyle = cfg.color;

        offCtx.translate(center, center);
        offCtx.beginPath();

        if (cfg.shape === "diamond") {
          const r = 5;
          offCtx.moveTo(0, -r);
          offCtx.lineTo(r, 0);
          offCtx.lineTo(0, r);
          offCtx.lineTo(-r, 0);
          offCtx.closePath();
        } else {
          // Circle
          offCtx.arc(0, 0, 4.5, 0, Math.PI * 2);
        }

        offCtx.fill();
        spriteCache[cfg.key] = offCanvas;
      });
    };

    initSpriteCache();

    // --- Particle Field Setup ---
    const PARTICLE_COUNT = 30;
    const particles: Particle[] = [];

    const resetParticle = (p: Partial<Particle>, spawnAtBottom = false): Particle => {
      const depth = 0.5 + Math.random() * 0.9; // 0.5 to 1.4 depth layer
      const spriteKeys = [
        "mint-glow",
        "mint-glow",
        "mint-diamond",
        "azure-glow",
        "azure-glow",
        "cyan-spec",
        "white-spec",
      ];
      const spriteKey = spriteKeys[Math.floor(Math.random() * spriteKeys.length)];

      return {
        x: p.x ?? Math.random() * width,
        y: spawnAtBottom ? height + 20 + Math.random() * 30 : Math.random() * height,
        vx: (Math.random() - 0.5) * 0.2,
        vy: -0.2 - Math.random() * 0.3, // Antigravity upward drift
        depth,
        baseSize: 2.2 + Math.random() * 2.2,
        spriteKey,
        alpha: 0.12 + Math.random() * 0.22, // Subtle opacity
        wobbleSpeed: 0.001 + Math.random() * 0.002,
        wobbleOffset: Math.random() * Math.PI * 2,
      };
    };

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.scale(dpr, dpr);

      // Re-initialize particles if empty
      if (particles.length === 0) {
        for (let i = 0; i < PARTICLE_COUNT; i++) {
          particles.push(resetParticle({}));
        }
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize, { passive: true });

    // --- Passive Pointer & Velocity Tracking ---
    const handlePointerMove = (e: PointerEvent) => {
      hasMouseMoved = true;
      targetMouseX = e.clientX;
      targetMouseY = e.clientY;

      const now = performance.now();
      const dt = Math.max(now - lastEventTime, 16);
      if (lastEventX > -500 && lastEventY > -500) {
        const dist = Math.hypot(e.clientX - lastEventX, e.clientY - lastEventY);
        const speed = dist / dt; // px/ms
        mouseVelocity = Math.min(mouseVelocity * 0.6 + speed * 15, 2.5);
      }
      lastEventX = e.clientX;
      lastEventY = e.clientY;
      lastEventTime = now;
    };

    const handlePointerLeave = () => {
      targetMouseX = -1000;
      targetMouseY = -1000;
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    window.addEventListener("pointerleave", handlePointerLeave, { passive: true });

    // --- Visibility API Optimization ---
    // Automatically halt loop when tab is hidden to save 100% idle GPU/CPU cycles
    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
      if (isVisible) {
        lastEventTime = performance.now();
        animationFrameId = requestAnimationFrame(render);
      } else {
        cancelAnimationFrame(animationFrameId);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    // --- Render Loop ---

    const render = (currentTime: number) => {
      if (!isVisible) return;


      // Exponential decay on mouse velocity
      mouseVelocity *= 0.94;

      // Smooth linear interpolation for cursor glow coordinates (lerp)
      if (targetMouseX > -500 && targetMouseY > -500) {
        if (!hasMouseMoved || currentMouseX < -500) {
          currentMouseX = targetMouseX;
          currentMouseY = targetMouseY;
        } else {
          currentMouseX += (targetMouseX - currentMouseX) * 0.08;
          currentMouseY += (targetMouseY - currentMouseY) * 0.08;
        }
      }

      ctx.clearRect(0, 0, width, height);

      // 1. Ambient Dual-Hue Dynamic Light Pools (Electric Mint + Azure Sapphire)
      // A. Static Anchor in Top-Left (Subtle Electric Mint Atmosphere)
      const mintAnchor = ctx.createRadialGradient(
        width * 0.15,
        height * 0.2,
        0,
        width * 0.15,
        height * 0.2,
        width * 0.55
      );
      mintAnchor.addColorStop(0, "rgba(0, 245, 160, 0.038)");
      mintAnchor.addColorStop(0.5, "rgba(0, 245, 160, 0.012)");
      mintAnchor.addColorStop(1, "rgba(11, 15, 25, 0)");
      ctx.fillStyle = mintAnchor;
      ctx.fillRect(0, 0, width, height);

      // B. Static Anchor in Bottom-Right (Subtle Electric Azure Atmosphere)
      const azureAnchor = ctx.createRadialGradient(
        width * 0.85,
        height * 0.8,
        0,
        width * 0.85,
        height * 0.8,
        width * 0.6
      );
      azureAnchor.addColorStop(0, "rgba(0, 112, 243, 0.045)");
      azureAnchor.addColorStop(0.5, "rgba(37, 99, 235, 0.018)");
      azureAnchor.addColorStop(1, "rgba(11, 15, 25, 0)");
      ctx.fillStyle = azureAnchor;
      ctx.fillRect(0, 0, width, height);

      // C. Interactive Cursor-Following Radiant Spotlight Mesh
      if (currentMouseX > -500 && currentMouseY > -500) {
        const baseRadius = 260;
        const dynamicRadius = baseRadius + mouseVelocity * 50;
        const velocityBoost = Math.min(mouseVelocity * 0.04, 0.05);

        // Core Electric Mint Inner Glow
        const cursorGlow = ctx.createRadialGradient(
          currentMouseX,
          currentMouseY,
          0,
          currentMouseX,
          currentMouseY,
          dynamicRadius
        );
        cursorGlow.addColorStop(0, `rgba(0, 245, 160, ${0.065 + velocityBoost})`);
        cursorGlow.addColorStop(0.35, `rgba(0, 245, 160, ${0.032 + velocityBoost * 0.5})`);
        cursorGlow.addColorStop(0.65, `rgba(0, 112, 243, ${0.025 + velocityBoost * 0.3})`);
        cursorGlow.addColorStop(1, "rgba(11, 15, 25, 0)");

        ctx.fillStyle = cursorGlow;
        ctx.fillRect(0, 0, width, height);
      }

      // If prefers-reduced-motion is active, skip particle animation to respect user preference
      if (prefersReducedMotion) return;

      // 2. Antigravity Particle Simulation Loop
      const interactionRadius = 145;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // A. Physics Drift: Gentle Antigravity upward acceleration
        p.vy += -0.018 * p.depth;

        // B. Gentle harmonic horizontal wave
        p.x += p.vx * p.depth + Math.sin(currentTime * p.wobbleSpeed + p.wobbleOffset) * 0.22;
        p.y += p.vy * p.depth;

        // C. Interactive Cursor Repulsion (Antigravity Deflection Field)
        if (targetMouseX > -500 && targetMouseY > -500) {
          const dx = p.x - targetMouseX;
          const dy = p.y - targetMouseY;
          const dist = Math.hypot(dx, dy);

          if (dist < interactionRadius && dist > 1) {
            const force = Math.pow((interactionRadius - dist) / interactionRadius, 1.6);
            const angle = Math.atan2(dy, dx);
            const push = force * (2.8 + mouseVelocity * 1.5);

            p.vx += Math.cos(angle) * push;
            p.vy += Math.sin(angle) * push;
          }
        }

        // D. Atmospheric Drag / Air Friction
        p.vx *= 0.95;
        p.vy *= 0.96;

        // Clamp extreme speeds
        p.vx = Math.max(Math.min(p.vx, 3.5), -3.5);
        p.vy = Math.max(Math.min(p.vy, 2.5), -3.5);

        // E. Toroidal Boundary Wrapping & Upward Reset
        if (p.x < -30) p.x = width + 30;
        if (p.x > width + 30) p.x = -30;

        // Floating out top -> re-enter from bottom
        if (p.y < -40) {
          particles[i] = resetParticle({ x: Math.random() * width }, true);
          continue;
        }

        // F. Sprite Rendering with Pre-baked GPU Textures
        const sprite = spriteCache[p.spriteKey];
        if (sprite) {
          ctx.save();
          // Subtle alpha scaling by depth and velocity excitation
          const renderAlpha = Math.min(p.alpha + mouseVelocity * 0.04, 0.45);
          ctx.globalAlpha = renderAlpha;

          // Scale sprite: drawSize 32px is mapped down to p.baseSize * p.depth
          const renderSize = (p.baseSize * p.depth * 32) / 9;
          ctx.drawImage(
            sprite,
            p.x - renderSize / 2,
            p.y - renderSize / 2,
            renderSize,
            renderSize
          );
          ctx.restore();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerleave", handlePointerLeave);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden z-0"
      aria-hidden="true"
    >
      {/* Dynamic Antigravity GPU Canvas Layer */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 block w-full h-full pointer-events-none"
        style={{ willChange: "transform" }}
      />

      {/* Subtle Architectural Grid Overlay to retain Swiss precision */}
      <div
        className="absolute inset-0 opacity-[0.035] pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(#F8FAFC 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
    </div>
  );
};
