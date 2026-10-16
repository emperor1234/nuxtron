"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { apiSend } from "@/app/lib/platform-api";
import { resolveSessionTenant } from "@/app/lib/api-client";
import { ButtonLink, Callout, LoadingState, Page, PageHeader } from "../../../../../_ui/kit";

type Outcome = { state: "working" } | { state: "done" } | { state: "failed"; message: string };

function Completing() {
  const params = useParams<{ network: string }>();
  const search = useSearchParams();
  const [outcome, setOutcome] = useState<Outcome>({ state: "working" });

  useEffect(() => {
    let active = true;
    const network = (params?.network || "").trim();
    const code = (search.get("code") || "").trim();
    const state = (search.get("state") || "").trim();
    const providerError = (search.get("error") || "").trim();

    async function complete() {
      if (!network) return fail("The sign-in address is missing the network name.");
      if (providerError) return fail(`The network returned an error: ${providerError}.`);
      if (!code || !state) return fail("The network did not return the sign-in code. Start the connection again.");
      try {
        await apiSend(`/social/oauth/${encodeURIComponent(network)}/callback`, "POST", { code, state }, resolveSessionTenant());
        if (!active) return;
        setOutcome({ state: "done" });
        setTimeout(() => globalThis.location.assign("/studio/social-studio/accounts"), 900);
      } catch (error) {
        fail(error instanceof Error ? error.message : "The connection could not be completed.");
      }
    }
    function fail(message: string) {
      if (active) setOutcome({ state: "failed", message });
    }
    void complete();
    return () => {
      active = false;
    };
  }, [params, search]);

  return (
    <Page width="narrow">
      <PageHeader title="Connecting your account" subtitle="Finishing the sign-in with the network." />
      {outcome.state === "working" ? <LoadingState label="Connecting" /> : null}
      {outcome.state === "done" ? <Callout tone="success" title="Account connected">Taking you to Connected Accounts…</Callout> : null}
      {outcome.state === "failed" ? (
        <>
          <Callout tone="danger" title="The account was not connected">{outcome.message}</Callout>
          <div><ButtonLink href="/studio/social-studio/accounts" variant="primary">Back to Connected Accounts</ButtonLink></div>
        </>
      ) : null}
    </Page>
  );
}

export default function SocialOAuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingState label="Connecting" />}>
      <Completing />
    </Suspense>
  );
}
