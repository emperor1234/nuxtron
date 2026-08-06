declare module '@builder.io/partytown/react' {
  import type { JSX } from 'react';

  export type PartytownProps = {
    debug?: boolean;
    forward?: string[];
    lib?: string;
  };

  export function Partytown(props: PartytownProps): JSX.Element;
}
