'use client';

import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  Bot,
  Globe,
  LineChart,
  Megaphone,
  MessageSquare,
  PenTool,
  Radar,
  Search,
  Share2,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Wallet,
  Zap,
} from 'lucide-react';
import {
  FloatingIconsHero,
  type FloatingIconsHeroProps,
} from '@/components/ui/floating-icons-hero-section';

function lucideIcon(Icon: LucideIcon): React.FC<React.SVGProps<SVGSVGElement>> {
  return function LucideIconWrapper(props) {
    return <Icon {...props} strokeWidth={1.75} />;
  };
}

const heroIcons: FloatingIconsHeroProps['icons'] = [
  { id: 1, icon: lucideIcon(Sparkles), className: 'top-[10%] left-[10%]' },
  { id: 2, icon: lucideIcon(Bot), className: 'top-[20%] right-[8%]' },
  { id: 3, icon: lucideIcon(Megaphone), className: 'top-[80%] left-[10%]' },
  { id: 4, icon: lucideIcon(Search), className: 'bottom-[10%] right-[10%]' },
  { id: 5, icon: lucideIcon(Share2), className: 'top-[5%] left-[30%]' },
  { id: 6, icon: lucideIcon(LineChart), className: 'top-[5%] right-[30%]' },
  { id: 7, icon: lucideIcon(Target), className: 'bottom-[8%] left-[25%]' },
  { id: 8, icon: lucideIcon(TrendingUp), className: 'top-[40%] left-[15%]' },
  { id: 9, icon: lucideIcon(BarChart3), className: 'top-[75%] right-[25%]' },
  { id: 10, icon: lucideIcon(Zap), className: 'top-[90%] left-[70%]' },
  { id: 11, icon: lucideIcon(PenTool), className: 'top-[50%] right-[5%]' },
  { id: 12, icon: lucideIcon(MessageSquare), className: 'top-[55%] left-[5%]' },
  { id: 13, icon: lucideIcon(Globe), className: 'top-[5%] left-[55%]' },
  { id: 14, icon: lucideIcon(Radar), className: 'bottom-[5%] right-[45%]' },
  { id: 15, icon: lucideIcon(Users), className: 'top-[25%] right-[20%]' },
  { id: 16, icon: lucideIcon(Wallet), className: 'top-[60%] left-[30%]' },
];

export default function HomeFloatingHero() {
  return (
    <div className="home-floating-hero">
      <FloatingIconsHero
        title="Nuxtron: The Autonomous AI Platform For Faster Digital Growth"
        subtitle="Professional-grade platform for AI-powered Social Media, Ads, and SEO operations with production reliability and enterprise controls. Build, launch, and optimize campaigns from one command center with autonomous workflows and live performance intelligence."
        ctaText="Open Dashboard"
        ctaHref="/dashboard"
        icons={heroIcons}
      />
      <div className="hero-cta-row" style={{ marginTop: 16 }}>
        <a className="cta-link" href="/platform">
          Open Platform
        </a>
        <a className="cta-link" href="/crm?tab=enterprise">
          CRM Enterprise Ops
        </a>
        <a className="cta-link" href="/register">
          Start Free Trial
        </a>
        <a className="cta-link" href="/features">
          Explore Features
        </a>
      </div>
    </div>
  );
}
