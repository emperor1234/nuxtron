declare module '@builder.io/partytown/react' {
  import type { JSX } from 'react';

  export type PartytownProps = {
    debug?: boolean;
    forward?: string[];
    lib?: string;
    // Present in the actual runtime (react/index.mjs destructures and sets
    // it on the bootstrap <script>'s nonce attribute) but missing from
    // this hand-written shim — needed to satisfy a nonce'd CSP.
    nonce?: string;
  };

  export function Partytown(props: PartytownProps): JSX.Element;
}
