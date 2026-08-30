'use client';

import { Partytown } from '@builder.io/partytown/react';

interface PartytownWrapperProps {
  forward?: string[];
  nonce?: string;
}

export function PartytownWrapper({ forward = [], nonce }: PartytownWrapperProps) {
  return <Partytown forward={forward} nonce={nonce} />;
}