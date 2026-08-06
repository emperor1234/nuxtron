'use client';

import * as React from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import {
  BarChart3,
  Bot,
  Megaphone,
  Search,
  Share2,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

/**
 * Aceternity-inspired hero with a 3D parallax dashboard card.
 * Pointer movement tilts the scene on the X/Y axes (perspective transform),
 * while floating glyph chips drift at varying depths for a layered 3D feel.
 * Dependency-free: framer-motion (already installed) + CSS 3D transforms.
 */

const floatChips = [
  { Icon: Sparkles, label: 'AI Content', x: '-18%', y: '-12%', depth: 60, delay: 0 },
  { Icon: Megaphone, label: 'Autonomous Ads', x: '78%', y: '-6%', depth: 90, delay: 0.4 },
  { Icon: Search, label: 'SEO Engine', x: '82%', y: '64%', depth: 70, delay: 0.8 },
  { Icon: Share2, label: 'Social Ops', x: '-14%', y: '58%', depth: 100, delay: 1.2 },
  { Icon: TrendingUp, label: '+312% ROI', x: '90%', y: '30%', depth: 50, delay: 0.6 },
];

export default function AxHero() {
  const ref = React.useRef<HTMLDivElement>(null);
  const mx = useMotionValue(0.5);
  const my = useMotionValue(0.5);
  const rx = useSpring(useTransform(my, [0, 1], [10, -10]), { stiffness: 120, damping: 18 });
  const ry = useSpring(useTransform(mx, [0, 1], [-14, 14]), { stiffness: 120, damping: 18 });

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    mx.set(px);
    my.set(py);
    el.style.setProperty('--mx', `${px * 100}%`);
    el.style.setProperty('--my', `${py * 100}%`);
  }
  function onLeave() {
    mx.set(0.5);
    my.set(0.5);
  }

  return (
    <section className="ax-hero" aria-label="Nuxtron platform hero">
      <div className="ax-glow-ring" style={{ width: 520, height: 520, left: '50%', top: '-160px', marginLeft: -260 }} />

      <div className="ax-hero-copy">
        <span className="ax-eyebrow">Autonomous AI Growth Platform</span>
        <h1 className="ax-hero-title">
          One command center for{' '}
          <span className="gradient-text">Social, Ads &amp; SEO</span> on autopilot
        </h1>
        <p className="ax-hero-sub">
          Build, launch, and optimize campaigns with AI-native generation, advanced editing, and
          live performance intelligence — production-grade reliability with enterprise controls.
        </p>
        <div className="ax-hero-actions">
          <a className="ax-btn" href="/dashboard">
            Open Dashboard
          </a>
          <a className="ax-btn-ghost" href="/features">
            Explore Features
          </a>
        </div>
        <div className="ax-hero-trust" aria-label="Trusted by teams">
          <span>Trusted by growth teams at startups, agencies &amp; enterprises</span>
        </div>
      </div>

      <div
        ref={ref}
        className="ax-hero-stage ax-spotlight"
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        aria-hidden="true"
      >
        <motion.div
          className="ax-hero-card"
          style={{ rotateX: rx, rotateY: ry, transformPerspective: 1100 }}
        >
          <div className="ax-hero-card-bar">
            <span /> <span /> <span />
            <em>nuxtron · command center</em>
          </div>
          <div className="ax-hero-card-body">
            <div className="ax-hero-stat">
              <Bot size={18} />
              <strong>4 agents</strong>
              <small>running autonomously</small>
            </div>
            <div className="ax-hero-chart" role="img" aria-label="Performance trend going up">
              {[34, 52, 41, 68, 58, 82, 74, 96].map((h, i) => (
                <motion.span
                  key={i}
                  style={{ height: `${h}%` }}
                  initial={{ scaleY: 0 }}
                  animate={{ scaleY: 1 }}
                  transition={{ delay: 0.2 + i * 0.08, type: 'spring', stiffness: 120 }}
                />
              ))}
            </div>
            <div className="ax-hero-rowgrid">
              <div className="ax-hero-mini"><BarChart3 size={16} /> Reach<b>1.2M</b></div>
              <div className="ax-hero-mini"><TrendingUp size={16} /> CTR<b>6.4%</b></div>
              <div className="ax-hero-mini"><Search size={16} /> Keywords<b>+418</b></div>
            </div>
          </div>
        </motion.div>

        {floatChips.map(({ Icon, label, x, y, depth, delay }, i) => (
          <motion.div
            key={i}
            className="ax-hero-chip"
            style={{ left: x, top: y, translateZ: depth }}
            animate={{ y: [0, -14, 0] }}
            transition={{ duration: 4 + i * 0.5, repeat: Infinity, ease: 'easeInOut', delay }}
          >
            <Icon size={16} />
            <span>{label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
