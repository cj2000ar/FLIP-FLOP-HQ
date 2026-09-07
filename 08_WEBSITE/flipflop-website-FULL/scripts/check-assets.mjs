import { readdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=fileURLToPath(new URL('../public/',import.meta.url));
const origin=process.env.HQ_ORIGIN||'http://127.0.0.1:4177';
async function list(dir){const entries=await readdir(dir,{withFileTypes:true});return (await Promise.all(entries.map(e=>e.isDirectory()?list(path.join(dir,e.name)):[path.join(dir,e.name)]))).flat();}
// Check runtime media and credits; the models README documents source geometry.
const files=(await list(root)).filter(file=>/\.(png|jpe?g|svg|webp|woff2|txt)$/i.test(file));
for(const file of files){const route='/'+path.relative(root,file).split(path.sep).join('/');const response=await fetch(new URL(route,origin));assert.equal(response.status,200,route);const actual=Buffer.from(await response.arrayBuffer()),expected=await readFile(file);assert.equal(createHash('sha256').update(actual).digest('hex'),createHash('sha256').update(expected).digest('hex'),route);}
console.log(`PASS: ${files.length} local assets, fonts and compatibility paths served byte-for-byte.`);
