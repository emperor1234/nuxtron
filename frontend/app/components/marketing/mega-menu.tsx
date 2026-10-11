"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import type { Route } from "next";
import * as NavigationMenu from "@radix-ui/react-navigation-menu";
import { ArrowRight, ChevronDown } from "lucide-react";
import {
  COMPANY_GROUP,
  FREE_TOOLS_GROUP,
  MARKETING_GROUP,
  PLATFORM_SHARED_LINKS,
  PRICING_LINK,
  RESOURCES_GROUP,
  SEO_GROUP,
  SOLUTIONS_GROUP,
  type FeaturedPost,
  type SiteLink,
  type SiteLinkGroup,
} from "./site-links";

/**
 * Desktop navigation. Radix NavigationMenu supplies hover intent, click to
 * toggle, Escape and outside-click to close, and arrow-key movement between
 * triggers; we supply the panels. Panels enter from the trigger at
 * scale(0.97) + fade over 200ms var(--ease-out) (see marketing.css,
 * .mk-mega-panel); reduced motion keeps the fade only.
 */
export function MegaMenu({ featuredPost }: { featuredPost: FeaturedPost | null }) {
  return (
    <NavigationMenu.Root className="mk-mega" aria-label="Main" delayDuration={120}>
      <NavigationMenu.List className="mk-mega-list">
        <MenuItem label="Platform">
          <div className="mk-mega-grid" data-columns="3">
            <Group group={SEO_GROUP} />
            <Group group={MARKETING_GROUP} />
            <div className="mk-mega-group">
              <p className="mk-mega-title">Across both products</p>
              <ul className="mk-mega-links">
                {PLATFORM_SHARED_LINKS.map((link) => (
                  <MenuLink key={link.href} link={link} />
                ))}
              </ul>
            </div>
          </div>
        </MenuItem>

        <MenuItem label="Solutions">
          <div className="mk-mega-grid" data-columns="2">
            <Group group={SOLUTIONS_GROUP} columns={2} />
          </div>
        </MenuItem>

        <MenuItem label="Free tools">
          <div className="mk-mega-grid" data-columns="1">
            <Group group={FREE_TOOLS_GROUP} />
          </div>
        </MenuItem>

        <MenuItem label="Resources">
          <div className="mk-mega-grid" data-columns="2">
            <Group group={RESOURCES_GROUP} />
            {featuredPost ? <FeaturedCard post={featuredPost} /> : null}
          </div>
        </MenuItem>

        <NavigationMenu.Item>
          <NavigationMenu.Link asChild>
            <Link href={PRICING_LINK.href as Route} className="mk-mega-trigger">
              {PRICING_LINK.label}
            </Link>
          </NavigationMenu.Link>
        </NavigationMenu.Item>

        <MenuItem label="Company">
          <div className="mk-mega-grid" data-columns="1">
            <Group group={COMPANY_GROUP} />
          </div>
        </MenuItem>
      </NavigationMenu.List>
    </NavigationMenu.Root>
  );
}

function MenuItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <NavigationMenu.Item className="mk-mega-item">
      <NavigationMenu.Trigger className="mk-mega-trigger">
        {label}
        <ChevronDown size={14} aria-hidden="true" className="mk-mega-chevron" />
      </NavigationMenu.Trigger>
      <NavigationMenu.Content className="mk-mega-panel">{children}</NavigationMenu.Content>
    </NavigationMenu.Item>
  );
}

function Group({ group, columns = 1 }: { group: SiteLinkGroup; columns?: 1 | 2 }) {
  return (
    <div className="mk-mega-group">
      <p className="mk-mega-title">{group.title}</p>
      {group.caption ? <p className="mk-mega-caption">{group.caption}</p> : null}
      <ul className="mk-mega-links" data-columns={columns}>
        {group.links.map((link) => (
          <MenuLink key={`${group.id}:${link.href}:${link.label}`} link={link} />
        ))}
      </ul>
    </div>
  );
}

function MenuLink({ link }: { link: SiteLink }) {
  const Icon = link.icon;
  return (
    <li>
      <NavigationMenu.Link asChild>
        <Link href={link.href as Route} className="mk-mega-link">
          {Icon ? (
            <span className="mk-mega-icon" aria-hidden="true">
              <Icon size={16} strokeWidth={1.7} />
            </span>
          ) : null}
          <span>
            <span className="mk-mega-label">{link.label}</span>
            {link.description ? <span className="mk-mega-desc">{link.description}</span> : null}
          </span>
        </Link>
      </NavigationMenu.Link>
    </li>
  );
}

function FeaturedCard({ post }: { post: FeaturedPost }) {
  return (
    <NavigationMenu.Link asChild>
      <Link href={`/blog/${post.slug}` as Route} className="mk-mega-featured">
        <span className="mk-mega-featured-kicker">Latest · {post.category}</span>
        <span className="mk-mega-featured-title">{post.title}</span>
        <span className="mk-mega-featured-desc">{post.description}</span>
        <span className="mk-mega-featured-cta">
          Read · {post.readMinutes} min <ArrowRight size={14} aria-hidden="true" />
        </span>
      </Link>
    </NavigationMenu.Link>
  );
}
