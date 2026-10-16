"use client";

import { apiGet } from "@/app/lib/platform-api";
import { Page, PageHeader } from "../../_ui/kit";
import { SectionForm, type SectionField } from "../../_ui/section-form";
import { ResourceView, useResource } from "../../_ui/use-resource";

type Profile = Record<string, unknown>;

const TONES = ["professional", "friendly", "casual", "bold", "playful", "authoritative"].map((value) => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) }));
const FIELDS: SectionField[] = [
  { key: "business_name", label: "Business name", required: true, max: 120 },
  { key: "industry", label: "Industry", max: 80 },
  { key: "website", label: "Website", type: "url", max: 200 },
  { key: "description", label: "What you do", type: "textarea", max: 600 },
  { key: "tone", label: "Tone of voice", type: "select", options: TONES },
  { key: "timezone", label: "Time zone", hint: "For example Europe/London. Used when you plan posts.", max: 60 },
  { key: "keywords", label: "Keywords", type: "list", hint: "One per line." },
  { key: "hashtags", label: "Hashtags", type: "list", hint: "One per line." },
  { key: "logo_url", label: "Logo URL", type: "url" },
  { key: "logo_dark_url", label: "Logo URL for dark backgrounds", type: "url" },
];

export default function BrandProfilePage() {
  const resource = useResource<Profile>(async (tenant) => (await apiGet<{ brand_profile: Profile }>("/social/brand-profile", tenant)).brand_profile, []);
  return (
    <Page width="narrow">
      <PageHeader title="Brand Profile" subtitle="The business details Social Studio uses when it plans and writes posts." />
      <ResourceView resource={resource}>
        {(profile) => <SectionForm title="Your business" endpoint="/social/brand-profile" method="PUT" initial={profile} base={profile} fields={FIELDS} onSaved={resource.reload} />}
      </ResourceView>
    </Page>
  );
}
