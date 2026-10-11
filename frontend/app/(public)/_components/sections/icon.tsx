import {
  Bot,
  CalendarDays,
  ChartColumn,
  FileText,
  Inbox,
  Link2,
  MapPin,
  Megaphone,
  Search,
  Share2,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import type { SectionIcon } from "../../_content/types";

const ICONS: Readonly<Record<SectionIcon, LucideIcon>> = {
  search: Search,
  sparkles: Sparkles,
  chart: ChartColumn,
  "map-pin": MapPin,
  "file-text": FileText,
  share: Share2,
  calendar: CalendarDays,
  users: Users,
  workflow: Workflow,
  shield: ShieldCheck,
  megaphone: Megaphone,
  inbox: Inbox,
  bot: Bot,
  link: Link2,
};

/** Renders a content-model icon name as a decorative lucide glyph. */
export function SectionIconGlyph({
  name,
  size = 20,
  className,
}: {
  name: SectionIcon;
  size?: number;
  className?: string;
}) {
  const Icon = ICONS[name];
  return <Icon size={size} strokeWidth={1.6} aria-hidden="true" className={className} />;
}
