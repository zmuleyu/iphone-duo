(() => {
  // Step 3.7.3 — Monotonic / Plateau Framing
  //
  // The current Step 3.7.2 build already applies a bell-shaped optical correction
  // inside main.js. Rather than reintroduce another hard keyframe curve, this small
  // overlay converts that existing correction into a monotonic plateau in screen
  // space. Closed remains unchanged; the correction eases in once and then stays
  // present through Open, eliminating the late-stage snap-back.

  const CURRENT_START = 0.45;
  const CURRENT_PEAK_PROGRESS = 0.65;
  const CURRENT_END = 0.92;
  const CURRENT_PEAK = 0.65;

  const TARGET_START = 0.40;
  const TARGET_PLATEAU_START = 0.68;
  const TARGET_PLATEAU = 0.55;

  const clamp01 = value => Math.max(0, Math.min(1, value));
  const smoothstep = (edge0, edge1, value) => {
    const t = clamp01((value - edge0) / Math.max(edge1 - edge0, 1e-6));
    return t * t * (3 - 2 * t);
  };

  function currentOptical(progress) {
    const p = clamp01(progress);
    if (p <= CURRENT_START || p >= CURRENT_END) return 0;
    if (p <= CURRENT_PEAK_PROGRESS) {
      return CURRENT_PEAK * smoothstep(CURRENT_START, CURRENT_PEAK_PROGRESS, p);
    }
    return CURRENT_PEAK * (1 - smoothstep(CURRENT_PEAK_PROGRESS, CURRENT_END, p));
  }

  function targetOptical(progress) {
    const p = clamp01(progress);
    if (p <= TARGET_START) return 0;
    if (p >= TARGET_PLATEAU_START) return TARGET_PLATEAU;
    return TARGET_PLATEAU * smoothstep(TARGET_START, TARGET_PLATEAU_START, p);
  }

  function tick() {
    const viewport = document.querySelector('#viewport');
    const slider = document.querySelector('#angle');
    const canvas = viewport?.querySelector('canvas');

    if (viewport && slider && canvas) {
      const progress = Number(slider.value || 0) / 180;
      const deltaScene = targetOptical(progress) - currentOptical(progress);
      const { width, height } = viewport.getBoundingClientRect();
      const pixelsPerUnit = Math.min(width / 25, height / 17, 37);
      const deltaPx = deltaScene * pixelsPerUnit;

      canvas.style.transformOrigin = '50% 50%';
      canvas.style.transform = `translate3d(${deltaPx.toFixed(3)}px, 0, 0)`;
      canvas.dataset.framingStep = '3.7.3';
      canvas.dataset.framingDeltaPx = deltaPx.toFixed(3);
    }

    requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
})();
