---
language: typescript
extensions: [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
---

# TypeScript / JavaScript rules

Defer style nits to `eslint`/`prettier`/`tsc` when configured.

## Signals

- Flag `console.log`/`debugger` in prod paths; unjustified `@ts-ignore`/`eslint-disable`
- Flag `any`, `eval`/`new Function` with dynamic input, `var` in new code

## Types

- REQUIRED: `any` where `unknown` + narrow works; `!` without guard; missing export return types
- Flag `as` where guards/unions fit; non-exhaustive union `switch`; unconstrained generics
- Flag `strict: false` or disabled strict flags on new projects; type-widening to silence errors

## Security

- BLOCKER: `innerHTML`/`outerHTML`/`document.write` or `dangerouslySetInnerHTML` + user data
- Flag JWT without verify; auth cookies without `httpOnly`/`secure`; `postMessage` without origin check

## Async, resources, perf

- REQUIRED: floating promises
- Flag `async` in `forEach`; `Promise.all` vs `allSettled`; missing handler error paths
- Flag uncleared timers/listeners; streams/DB not closed on error
- Flag chained array passes, repeated DOM queries in loops, hot-path JSON parse/stringify, serial `await` in independent loops

## Idioms

- Prefer `const`, `?.`, `??`, discriminated unions, named exports; flag `==` vs `===`

## React (`.tsx`, `**/components/**`)

- Flag `any` props/events; `useEffect` without cleanup or deps; untyped nullable `useState`

## Node (`**/api/**`, `**/routes/**`, `**/middleware/**`, `**/handlers/**`)

- Flag unvalidated body/query; sync FS/CPU on large inputs without streaming; inconsistent error responses
