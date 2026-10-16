// Next.js route modules may only export HTTP handlers, so the proxy logic and
// its test hooks live in ../gateway.ts.
import { handle } from '../gateway';

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
