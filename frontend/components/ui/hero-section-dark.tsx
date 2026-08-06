"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";

/**
 * HeroSection — FarmUI-style retro-grid hero with animated conic CTA.
 *
 * Adapted from the launchui/farmui component. All purple/pink from the
 * original source has been replaced with the Nuxtron warm brand palette
 * (orange #FF4800, teal #0B3D40, amber #FFCF5E) per brand guidelines.
 *
 * Renders on a cream canvas (#FBF9F4). The RetroGrid floor + radial glow
 * + animated conic-border CTA + dashboard screenshot below form the hero.
 */
interface HeroSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: {
    regular: string;
    gradient: string;
  };
  description?: string;
  ctaText?: string;
  ctaHref?: string;
  bottomImage?: {
    light: string;
    dark: string;
  };
  gridOptions?: {
    angle?: number;
    cellSize?: number;
    opacity?: number;
    lightLineColor?: string;
    darkLineColor?: string;
  };
}

const RetroGrid = ({
  angle = 65,
  cellSize = 60,
  opacity = 0.5,
  lightLineColor = "#E4DCC9",
  darkLineColor = "#E4DCC9",
}: {
  angle?: number;
  cellSize?: number;
  opacity?: number;
  lightLineColor?: string;
  darkLineColor?: string;
}) => {
  const gridStyles = {
    "--grid-angle": `${angle}deg`,
    "--cell-size": `${cellSize}px`,
    "--opacity": opacity,
    "--light-line": lightLineColor,
    "--dark-line": darkLineColor,
  } as React.CSSProperties;

  return (
    <div
      className={cn(
        "pointer-events-none absolute size-full overflow-hidden [perspective:200px]",
        `opacity-[var(--opacity)]`,
      )}
      style={gridStyles}
    >
      <div className="absolute inset-0 [transform:rotateX(var(--grid-angle))]">
        <div className="animate-grid [background-image:linear-gradient(to_right,var(--light-line)_1px,transparent_0),linear-gradient(to_bottom,var(--light-line)_1px,transparent_0)] [background-repeat:repeat] [background-size:var(--cell-size)_var(--cell-size)] [height:300vh] [inset:0%_0px] [margin-left:-200%] [transform-origin:100%_0_0] [width:600vw] dark:[background-image:linear-gradient(to_right,var(--dark-line)_1px,transparent_0),linear-gradient(to_bottom,var(--dark-line)_1px,transparent_0)]" />
      </div>
      {/* Fade grid into the cream canvas at the top */}
      <div className="absolute inset-0 bg-gradient-to-t from-transparent to-[#FBF9F4] to-90%" />
    </div>
  );
};

const HeroSection = React.forwardRef<HTMLDivElement, HeroSectionProps>(
  (
    {
      className,
      title = "Build products for everyone",
      subtitle = {
        regular: "Designing your projects faster with ",
        gradient: "the largest figma UI kit.",
      },
      description = "Sed ut perspiciatis unde omnis iste natus voluptatem accusantium doloremque, totam rem aperiam, eaque ipsa quae.",
      ctaText = "Browse courses",
      ctaHref = "#",
      bottomImage = {
        light: "https://farmui.vercel.app/dashboard-light.png",
        dark: "https://farmui.vercel.app/dashboard.png",
      },
      gridOptions,
      ...props
    },
    ref,
  ) => {
    return (
      <div className={cn("relative", className)} ref={ref} {...props}>
        {/* Radial glow — was purple, now warm teal→orange */}
        <div className="absolute top-0 z-[0] h-screen w-screen bg-[#FF4800]/10 dark:bg-[#FF4800]/10 bg-[radial-gradient(ellipse_20%_80%_at_50%_-20%,rgba(11,61,64,0.18),rgba(255,255,255,0))] dark:bg-[radial-gradient(ellipse_20%_80%_at_50%_-20%,rgba(255,72,0,0.25),rgba(255,255,255,0))]" />
        <section className="relative max-w-full mx-auto z-1">
          <RetroGrid {...gridOptions} />
          <div className="max-w-screen-xl z-10 mx-auto px-4 py-28 gap-12 md:px-8">
            <div className="space-y-5 max-w-3xl leading-0 lg:leading-5 mx-auto text-center">
              {/* Eyebrow pill */}
              <h1 className="text-sm text-[#5A6A7A] dark:text-gray-400 group font-sans mx-auto px-5 py-2 bg-gradient-to-tr from-[#EFE9DC]/40 via-[#FFD4C4]/30 to-transparent border-[2px] border-black/5 dark:border-white/5 rounded-3xl w-fit">
                {title}
                <ChevronRight className="inline w-4 h-4 ml-2 group-hover:translate-x-1 duration-300" />
              </h1>

              {/* Headline — gradient text uses warm orange→amber (was purple→pink) */}
              <h2 className="text-4xl tracking-tighter font-sans bg-clip-text text-transparent mx-auto md:text-6xl bg-[linear-gradient(180deg,_#1F1F1F_0%,_rgba(31,_31,_31,_0.75)_100%)] dark:bg-[linear-gradient(180deg,_#FFF_0%,_rgba(255,_255,_255,_0.00)_202.08%)]">
                {subtitle.regular}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF4800] to-[#FFCF5E] dark:from-[#FF7A59] dark:to-[#FFCF5E]">
                  {subtitle.gradient}
                </span>
              </h2>

              <p className="max-w-2xl mx-auto text-[#5A6A7A] dark:text-gray-300">
                {description}
              </p>

              {/* Animated conic-border CTA — was purple #E2CBFF/#393BB2, now orange/teal */}
              <div className="items-center justify-center gap-x-3 space-y-3 sm:flex sm:space-y-0">
                <span className="relative inline-block overflow-hidden rounded-full p-[1.5px]">
                  <span className="absolute inset-[-1000%] animate-[spin_2s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#FFCF5E_0%,#0B3D40_50%,#FFCF5E_100%)]" />
                  <div className="inline-flex h-full w-full cursor-pointer items-center justify-center rounded-full bg-[#FBF9F4] dark:bg-gray-950 text-xs font-medium backdrop-blur-3xl">
                    <a
                      href={ctaHref}
                      className="inline-flex rounded-full text-center group items-center w-full justify-center bg-gradient-to-tr from-[#EFE9DC]/30 via-[#FF7A59]/30 to-transparent dark:from-zinc-300/5 dark:via-[#FF4800]/20 text-[#1F1F1F] dark:text-white border-input border-[1px] hover:bg-gradient-to-tr hover:from-[#EFE9DC]/40 hover:via-[#FF7A59]/40 hover:to-transparent dark:hover:from-zinc-300/10 dark:hover:via-[#FF4800]/30 transition-all sm:w-auto py-4 px-10"
                    >
                      {ctaText}
                    </a>
                  </div>
                </span>
              </div>
            </div>

            {/* Dashboard screenshot */}
            {bottomImage && (
              <div className="mt-32 mx-10 relative z-10">
                <img
                  src={bottomImage.light}
                  className="w-full shadow-lg rounded-lg border border-[#E4DCC9] dark:hidden"
                  alt="Dashboard preview"
                />
                <img
                  src={bottomImage.dark}
                  className="hidden w-full shadow-lg rounded-lg border border-gray-800 dark:block"
                  alt="Dashboard preview"
                />
              </div>
            )}
          </div>
        </section>
      </div>
    );
  },
);
HeroSection.displayName = "HeroSection";

export { HeroSection };
