# Flip Flop HQ — complete website handoff

This package contains the marketing website, its illustrative demo, full source, brand assets, Earth textures, locally bundled fonts, six language dictionaries, video and development history.

```sh
npm ci
npm run dev
```

Requires Node.js 22.13+ and npm. Open the local URL printed by the server. Run `npm run typecheck`, `npm test`, then `npm run build`. `npm start -- --port 4177` starts the local Cloudflare Worker emulator; `npm run test:delivery` checks it. Neither command deploys.

The project uses React, TypeScript, Vinext/Vite, Three.js and a Cloudflare Worker build. Assets and fonts are included; dependencies are restored from package-lock.json.

The actual NinjaTrader trading engine is not part of this repository. Charts use synthetic prices. The request form prepares a mailto draft; it does not send email on the user's behalf. See the Spanish README, HANDOFF.md, deploy-notes.md and docs/ for the complete technical and design handoff.
