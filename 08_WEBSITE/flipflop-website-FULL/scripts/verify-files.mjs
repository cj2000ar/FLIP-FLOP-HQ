import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const manifest=JSON.parse(readFileSync(new URL('../MANIFEST.json',import.meta.url),'utf8'));
let checked=0;
for(const file of manifest.files){const data=readFileSync(new URL('../'+file.path,import.meta.url));const hash=createHash('sha256').update(data).digest('hex');if(data.length!==file.bytes||hash!==file.sha256)throw new Error('Changed or missing: '+file.path);checked++;}
console.log('PASS: '+checked+' files match the handoff manifest.');
