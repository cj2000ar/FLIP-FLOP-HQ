import assert from 'node:assert/strict';

// Exercise the built or published response, including the assets its HTML names.
const origin = process.env.HQ_ORIGIN || 'http://127.0.0.1:4177';
const headers = process.env.HQ_CHECK_TOKEN
  ? { 'OAI-Sites-Authorization': `Bearer ${process.env.HQ_CHECK_TOKEN}` }
  : {};
for (const route of ['/', '/demo']) {
  const response = await fetch(new URL(route, origin), {
    headers,
    redirect: 'error',
  });
  assert.equal(response.status, 200, `${route}: document status`);
  const html = await response.text();
  const policy = response.headers.get('cache-control') || '';
  assert.match(
    policy,
    /no-store/,
    `${route}: stale HTML must not survive a deployment`,
  );
  assert(
    html.includes('trade-simulator'),
    `${route}: current interactive experience`,
  );
  if (route === '/') {
    assert(html.includes('earth-intro-mark'), 'Current logo introduction');
    assert(
      !html.includes('src="/saturn-trading.png"'),
      'Old loading artwork is absent',
    );
    for (const section of ['producto', 'requisitos', 'reparto', 'acceso']) {
      assert(html.includes(`id="${section}"`), `Section ${section}`);
    }
  }
  const paths = [
    ...new Set(
      [...html.matchAll(/(?:href|src)="([^"?#]+\.(?:css|js))[^"\s]*"/g)]
        .map((match) => match[1])
        .filter((path) => path.startsWith('/') && !path.startsWith('//')),
    ),
  ];
  assert(
    paths.some((path) => path.endsWith('.css')),
    'Stylesheet is referenced',
  );
  const results = await Promise.all(
    paths.map(async (path) => {
      const asset = await fetch(new URL(path, origin), {
        headers,
        redirect: 'error',
      });
      const type = asset.headers.get('content-type') || '';
      await asset.arrayBuffer();
      assert.equal(asset.status, 200, `Missing current asset: ${path}`);
      assert.match(
        type,
        path.endsWith('.css') ? /text\/css/ : /javascript/,
        `Asset type: ${path}`,
      );
      return path;
    }),
  );
  console.log(
    `PASS ${route}: current document, no-store, ${results.length} working CSS/JS assets.`,
  );
}
