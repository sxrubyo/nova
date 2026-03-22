(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  const CONFIG = {
    VIDEO_SPEED: 1,
    PRODUCT_END: 0.55,
  };

  const STATE = {
    video: null,
    currentTime: 0,
    targetTime: 0,
    loaded: false,
    rafId: null,
    lenis: null,
    visualScale: 1,
    visualOpacity: 1,
    visualBlur: 0,
  };

  function init() {
    setupVideo();
    preloadVideo();
  }

  function setupVideo() {
    STATE.video = document.getElementById('product-video');
    if (!STATE.video) {
      console.error('Video element not found');
      return;
    }

    STATE.video.addEventListener('loadeddata', onVideoLoaded);
    STATE.video.addEventListener('error', onVideoError);

    window.addEventListener('resize', debounce(handleResize, 150));
  }

  function handleResize() {
    ScrollTrigger.refresh();
  }

  function preloadVideo() {
    const loaderFill = document.getElementById('loader-fill');
    const loaderPercent = document.getElementById('loader-percent');

    if (STATE.video.readyState >= 3) {
      onVideoLoaded();
      return;
    }

    const checkProgress = setInterval(() => {
      const buffered = STATE.video.buffered.length > 0 ? STATE.video.buffered.end(0) : 0;
      const duration = STATE.video.duration || 1;
      const pct = Math.min(Math.round((buffered / duration) * 100), 100);

      loaderFill.style.width = `${pct}%`;
      loaderPercent.textContent = `${pct}%`;

      if (pct >= 100 || STATE.video.readyState >= 3) {
        clearInterval(checkProgress);
      }
    }, 100);
  }

  function onVideoLoaded() {
    STATE.loaded = true;
    STATE.video.currentTime = 0;

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

  function onVideoError(error) {
    console.error('Video load error:', error);
    document.getElementById('loader').classList.add('loaded');
  }

  function startRenderLoop() {
    function tick() {
      const duration = STATE.video.duration || 1;
      const maxTime = duration * 0.95;

      const delta = STATE.targetTime - STATE.currentTime;

      if (Math.abs(delta) > 0.001) {
        STATE.currentTime += delta * 0.18;
      } else {
        STATE.currentTime = STATE.targetTime;
      }

      const clampedTime = clamp(STATE.currentTime, 0, maxTime);

      if (STATE.video && !STATE.video.paused) {
        STATE.video.currentTime = clampedTime;
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
    const container = document.getElementById('video-container');

    ScrollTrigger.create({
      trigger: container,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        const pageProgress = self.progress;
        const progress = Math.min(pageProgress / 0.68, 1);
        const duration = STATE.video.duration || 1;
        const targetTime = progress * duration * 0.95 * CONFIG.VIDEO_SPEED;
        STATE.targetTime = clamp(targetTime, 0, duration * 0.95);
        updateCanvasPresence(pageProgress, progress);
      },
    });

    initSectionAnimations();
    initDarkOverlay();
  }

  function initSectionAnimations() {
    const sections = document.querySelectorAll('.scroll-section');
    const container = document.getElementById('video-container');

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
    const video = document.getElementById('product-video');

    ScrollTrigger.create({
      trigger: '#video-container',
      start: 'top bottom',
      end: 'top top',
      scrub: true,
      onUpdate: (self) => {
        const progress = self.progress;
        gsap.set(hero, {
          opacity: 1 - progress,
          scale: 1 - progress * 0.05,
        });
        video.style.clipPath = `circle(${progress * 75}% at 50% 50%)`;
      },
    });
  }

  function updateCanvasPresence(pageProgress, productProgress) {
    const video = document.getElementById('product-video');
    const enterScale = window.innerWidth < 768
      ? 1.08 - productProgress * 0.04
      : 1.1 - productProgress * 0.06;
    const exit = clamp((pageProgress - 0.58) / 0.16, 0, 1);

    STATE.visualScale = Math.max(window.innerWidth < 768 ? 1.02 : 1.04, enterScale);
    STATE.visualOpacity = 1 - exit;
    STATE.visualBlur = exit * 12;

    gsap.set(video, {
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
        trigger: '#video-container',
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
