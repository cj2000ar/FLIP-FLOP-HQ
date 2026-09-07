import { spawnSync } from 'node:child_process';
const files=['check-auto-chart.cjs','check-trade-simulation.cjs','check-website.cjs','check-language-store.cjs','check-motion.cjs','check-world.cjs'];
for (const file of files) { const r=spawnSync(process.execPath,['tests/'+file],{stdio:'inherit'});if(r.status!==0) process.exit(r.status||1); }
