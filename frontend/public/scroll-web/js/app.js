(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  const CONFIG = {
    FRAME_COUNT: 192,
    FRAME_PATH: 'scroll-web/frames/frame_',
    FRAME_EXT: '.webp',
    FRAME_PAD: 4,
    IMAGE_SCALE: window.innerWidth < 768 ? 0.92 : 0.88,
    FRAME_SPEED: 1,
    PRODUCT_END: 0.55,
    BATCH_SIZE: 18,
    FIRST_BATCH: 10,
  };

  const STATE = {
    frames: [],
    currentFrame: 0,
    targetFrame: 0,
    lastRenderedFrame: -1,
    loaded: false,
    dirty: true,
    canvas: null,
    ctx: null,
    rafId: null,
    lenis: null,
    visualScale: 1,
    visualOpacity: 1,
    visualBlur: 0,
  };

  function framePath(index) {
    return `${CONFIG.FRAME_PATH}${String(index).padStart(CONFIG.FRAME_PAD, '0')}${CONFIG.FRAME_EXT}`;
  }

  function init() {
    setupCanvas();
    preloadFrames();
  }

  function setupCanvas() {
    STATE.canvas = document.getElementById('product-canvas');
    STATE.ctx = STATE.canvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', debounce(handleResize, 150));
  }

  function handleResize() {
    CONFIG.IMAGE_SCALE = window.innerWidth < 768 ? 0.92 : 0.88;
    resizeCanvas();
    ScrollTrigger.refresh();
  }

  function resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const width = window.innerWidth;
    const height = window.innerHeight;

    STATE.canvas.width = width * dpr;
    STATE.canvas.height = height * dpr;
    STATE.canvas.style.width = `${width}px`;
    STATE.canvas.style.height = `${height}px`;
    STATE.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    STATE.dirty = true;
  }

  function preloadFrames() {
    const loaderFill = document.getElementById('loader-fill');
    const loaderPercent = document.getElementById('loader-percent');
    const total = CONFIG.FRAME_COUNT;
    let loadedCount = 0;

    STATE.frames = new Array(total);

    function loadImage(index) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.decoding = 'async';
        image.onload = () => {
          STATE.frames[index] = image;
          loadedCount += 1;
          const pct = Math.round((loadedCount / total) * 100);
          loaderFill.style.width = `${pct}%`;
          loaderPercent.textContent = `${pct}%`;

          if (index === 0) {
            STATE.currentFrame = 0;
            STATE.targetFrame = 0;
            STATE.dirty = true;
            renderFrame(0);
          }

          resolve();
        };
        image.onerror = reject;
        image.src = framePath(index + 1);
      });
    }

    async function loadInBatches() {
      const firstBatch = [];
      for (let i = 0; i < Math.min(CONFIG.FIRST_BATCH, total); i += 1) {
        firstBatch.push(loadImage(i));
      }
      await Promise.all(firstBatch);

      for (let i = CONFIG.FIRST_BATCH; i < total; i += CONFIG.BATCH_SIZE) {
        const batch = [];
        for (let j = i; j < Math.min(i + CONFIG.BATCH_SIZE, total); j += 1) {
          batch.push(loadImage(j));
        }
        await Promise.all(batch);
      }

      onAllFramesLoaded();
    }

    loadInBatches().catch((error) => {
      console.error('Frame preload failed:', error);
    });
  }

  function onAllFramesLoaded() {
    STATE.loaded = true;
    document.getElementById('loader').classList.add('loaded');

    setTimeout(() => {
      initLenis();
      initScrollAnimations();
      initHeader();
      initHeroTransition();
      initCounters();
      initCopyButtons();
      startRenderLoop();
      ScrollTrigger.refresh();
    }, 650);
  }

  function renderFrame(index) {
    const image = STATE.frames[index];
    if (!image || !STATE.ctx) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    const canvasWidth = STATE.canvas.width / dpr;
    const canvasHeight = STATE.canvas.height / dpr;
    const imageAspect = image.width / image.height;
    const canvasAspect = canvasWidth / canvasHeight;

    let drawWidth;
    let drawHeight;

    const visualScale = CONFIG.IMAGE_SCALE * STATE.visualScale;

    if (imageAspect > canvasAspect) {
      drawWidth = canvasWidth * visualScale;
      drawHeight = drawWidth / imageAspect;
    } else {
      drawHeight = canvasHeight * visualScale;
      drawWidth = drawHeight * imageAspect;
    }

    const x = (canvasWidth - drawWidth) / 2;
    const y = (canvasHeight - drawHeight) / 2;

    STATE.ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    STATE.ctx.drawImage(image, x, y, drawWidth, drawHeight);
    drawWatermarkMask(x, y, drawWidth, drawHeight);
    STATE.lastRenderedFrame = index;
    STATE.dirty = false;
  }

  function drawWatermarkMask(x, y, drawWidth, drawHeight) {
    const maskWidth = drawWidth;
    const maskHeight = drawHeight * 0.16;
    const maskX = x;
    const maskY = y + drawHeight - maskHeight;
    const gradient = STATE.ctx.createLinearGradient(maskX, maskY, maskX, maskY + maskHeight);

    gradient.addColorStop(0, 'rgba(7, 7, 7, 0)');
    gradient.addColorStop(0.22, 'rgba(7, 7, 7, 0.1)');
    gradient.addColorStop(0.5, 'rgba(7, 7, 7, 0.34)');
    gradient.addColorStop(0.76, 'rgba(7, 7, 7, 0.9)');
    gradient.addColorStop(1, 'rgba(7, 7, 7, 1)');

    STATE.ctx.fillStyle = gradient;
    STATE.ctx.fillRect(maskX, maskY, maskWidth, maskHeight);

    const radial = STATE.ctx.createRadialGradient(
      x + drawWidth * 0.93,
      y + drawHeight * 0.9,
      0,
      x + drawWidth * 0.93,
      y + drawHeight * 0.9,
      drawWidth * 0.14
    );
    radial.addColorStop(0, 'rgba(7, 7, 7, 0.82)');
    radial.addColorStop(0.46, 'rgba(7, 7, 7, 0.46)');
    radial.addColorStop(1, 'rgba(7, 7, 7, 0)');

    STATE.ctx.fillStyle = radial;
    STATE.ctx.fillRect(x + drawWidth * 0.72, y + drawHeight * 0.72, drawWidth * 0.28, drawHeight * 0.28);
  }

  function startRenderLoop() {
    function tick() {
      const delta = STATE.targetFrame - STATE.currentFrame;
      if (Math.abs(delta) > 0.001) {
        STATE.currentFrame += delta * 0.18;
        STATE.dirty = true;
      } else {
        STATE.currentFrame = STATE.targetFrame;
      }

      const renderIndex = clamp(Math.round(STATE.currentFrame), 0, CONFIG.FRAME_COUNT - 1);

      if (STATE.dirty || renderIndex !== STATE.lastRenderedFrame) {
        renderFrame(renderIndex);
      }
      STATE.rafId = requestAnimationFrame(tick);
    }

    tick();
  }

  function initLenis() {
    STATE.lenis = new Lenis({
      duration: 1.15,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      smoothTouch: false,
      touchMultiplier: 1.8,
    });

    STATE.lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((time) => {
      STATE.lenis.raf(time * 1000);
    });
    gsap.ticker.lagSmoothing(0);
  }

  function initScrollAnimations() {
    const container = document.getElementById('scroll-container');

    ScrollTrigger.create({
      trigger: container,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        const pageProgress = self.progress;
        const progress = Math.min(pageProgress / 0.68, 1);
        const frameIndex = progress * (CONFIG.FRAME_COUNT - 1) * CONFIG.FRAME_SPEED;
        STATE.targetFrame = clamp(frameIndex, 0, CONFIG.FRAME_COUNT - 1);
        updateCanvasPresence(pageProgress, progress);
      },
    });

    initSectionAnimations();
    initDarkOverlay();
  }

  function initSectionAnimations() {
    const sections = document.querySelectorAll('.scroll-section');
    const container = document.getElementById('scroll-container');

    sections.forEach((section) => {
      const enter = parseFloat(section.dataset.enter);
      const leave = parseFloat(section.dataset.leave);
      const persist = section.dataset.persist === 'true';
      const animation = section.dataset.animation || 'fade-up';
      const children = section.querySelectorAll('.section-label, .section-title, .section-body, .section-cta, .stat-item, .cta-group, .cta-logo');
      const initial = getInitialState(animation);
      const final = getFinalState(animation);
      let active = false;
      let completed = false;

      gsap.set(children, initial);
      gsap.set(section, { opacity: 0 });

      ScrollTrigger.create({
        trigger: container,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => {
          const progress = self.progress;
          const inside = progress >= enter && progress <= leave;
          const past = progress > leave;

          if (inside && !active) {
            active = true;
            gsap.to(section, { opacity: 1, duration: 0.35, overwrite: true });
            children.forEach((child, index) => {
              gsap.to(child, {
                ...final,
                duration: 0.72,
                delay: index * 0.12,
                ease: 'expo.out',
                overwrite: true,
              });
            });
          }

          if (!inside && active && !(persist && past)) {
            active = false;
            completed = false;
            gsap.to(section, { opacity: 0, duration: 0.28, overwrite: true });
            children.forEach((child) => {
              gsap.to(child, {
                ...initial,
                duration: 0.25,
                overwrite: true,
              });
            });
          }

          if (persist && past && !completed) {
            completed = true;
            gsap.set(section, { opacity: 1 });
            gsap.set(children, final);
          }

          if (progress < enter && persist) {
            completed = false;
          }
        },
      });
    });
  }

  function getInitialState(type) {
    const map = {
      'fade-up': { y: 56, opacity: 0 },
      'slide-left': { x: -100, opacity: 0 },
      'slide-right': { x: 100, opacity: 0 },
      'scale-up': { scale: 0.84, opacity: 0 },
      'rotate-in': { y: 42, rotation: 4, opacity: 0 },
      'stagger-up': { y: 66, opacity: 0 },
      'clip-reveal': { clipPath: 'inset(100% 0% 0% 0%)', opacity: 0 },
    };
    return map[type] || map['fade-up'];
  }

  function getFinalState(type) {
    const map = {
      'fade-up': { y: 0, opacity: 1 },
      'slide-left': { x: 0, opacity: 1 },
      'slide-right': { x: 0, opacity: 1 },
      'scale-up': { scale: 1, opacity: 1 },
      'rotate-in': { y: 0, rotation: 0, opacity: 1 },
      'stagger-up': { y: 0, opacity: 1 },
      'clip-reveal': { clipPath: 'inset(0% 0% 0% 0%)', opacity: 1 },
    };
    return map[type] || map['fade-up'];
  }

  function initHeroTransition() {
    const hero = document.getElementById('hero');
    const canvas = document.getElementById('product-canvas');

    ScrollTrigger.create({
      trigger: '#scroll-container',
      start: 'top bottom',
      end: 'top top',
      scrub: true,
      onUpdate: (self) => {
        const progress = self.progress;
        gsap.set(hero, {
          opacity: 1 - progress,
          scale: 1 - progress * 0.05,
        });
        canvas.style.clipPath = `circle(${progress * 75}% at 50% 50%)`;
      },
    });
  }

  function updateCanvasPresence(pageProgress, productProgress) {
    const canvas = document.getElementById('product-canvas');
    const enterScale = window.innerWidth < 768
      ? 1.08 - productProgress * 0.04
      : 1.1 - productProgress * 0.06;
    const exit = clamp((pageProgress - 0.58) / 0.16, 0, 1);

    STATE.visualScale = Math.max(window.innerWidth < 768 ? 1.02 : 1.04, enterScale);
    STATE.visualOpacity = 1 - exit;
    STATE.visualBlur = exit * 12;
    STATE.dirty = true;

    gsap.set(canvas, {
      opacity: STATE.visualOpacity,
      filter: `blur(${STATE.visualBlur}px)`,
    });
  }

  function initDarkOverlay() {
    const overlay = document.getElementById('dark-overlay');
    const sections = document.querySelectorAll('[data-overlay="true"]');

    sections.forEach((section) => {
      const enter = parseFloat(section.dataset.enter);
      const leave = parseFloat(section.dataset.leave);
      const fadeWidth = 0.035;

      ScrollTrigger.create({
        trigger: '#scroll-container',
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => {
          const p = self.progress;
          let opacity = 0;

          if (p >= enter - fadeWidth && p <= leave + fadeWidth) {
            if (p < enter) {
              opacity = (p - (enter - fadeWidth)) / fadeWidth;
            } else if (p > leave) {
              opacity = 1 - (p - leave) / fadeWidth;
            } else {
              opacity = 1;
            }
          }

          overlay.style.opacity = String(clamp(opacity, 0, 1));
        },
      });
    });
  }

  function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    const animated = new WeakSet();

    counters.forEach((counter) => {
      ScrollTrigger.create({
        trigger: counter,
        start: 'top 80%',
        once: true,
        onEnter: () => {
          if (animated.has(counter)) {
            return;
          }

          animated.add(counter);
          animateCounter(
            counter,
            parseFloat(counter.dataset.count || '0'),
            counter.dataset.suffix || ''
          );
        },
      });
    });
  }

  function animateCounter(element, target, suffix) {
    const decimals = Number.isInteger(target) ? 0 : String(target).split('.')[1]?.length || 0;
    const state = { value: 0 };

    gsap.to(state, {
      value: target,
      duration: 1.8,
      ease: 'expo.out',
      onUpdate: () => {
        const value = decimals > 0
          ? state.value.toFixed(decimals)
          : Math.round(state.value).toLocaleString('en-US');
        element.textContent = `${value}${suffix}`;
      },
    });
  }

  function initCopyButtons() {
    const buttons = document.querySelectorAll('.copy-trigger');

    buttons.forEach((button) => {
      button.addEventListener('click', async () => {
        const targetId = button.dataset.copyTarget;
        const directText = button.dataset.copyText;
        const text = directText || document.getElementById(targetId)?.textContent || '';
        if (!text) return;

        try {
          await navigator.clipboard.writeText(text.trim());
          const original = button.textContent;
          button.textContent = 'Copied';
          button.classList.add('copied');
          setTimeout(() => {
            button.textContent = original;
            button.classList.remove('copied');
          }, 1400);
        } catch (error) {
          console.error('Copy failed:', error);
        }
      });
    });
  }

  function initHeader() {
    const header = document.getElementById('header');
    let lastScroll = 0;

    function updateHeader() {
      const current = window.scrollY || window.pageYOffset || 0;

      if (current > window.innerHeight * 0.35) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }

      if (current > lastScroll && current > 220) {
        header.classList.add('hidden');
      } else {
        header.classList.remove('hidden');
      }

      lastScroll = current;
    }

    window.addEventListener('scroll', updateHeader, { passive: true });
    updateHeader();
  }

  function debounce(fn, delay) {
    let timer;
    return function debounced(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
