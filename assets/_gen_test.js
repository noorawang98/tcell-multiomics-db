// CI/自检用：在 Node 里跑网页端的脚本生成器，输出给 bash -n 校验（不在页面中加载）
const fs = require('fs');
const path = process.argv[2] || 'site/data/downloads.json';
const out = process.argv[3] || '/tmp/webtest';
const src = fs.readFileSync(path, 'utf8');
const manifest = { downloads: JSON.parse(src) };
const elements = { 'dsh-i18n': { textContent: '{}' }, 'dsh-manifest': { textContent: JSON.stringify(manifest) } };
global.document = {
  documentElement: { dataset: { base: '.' }, lang: 'zh' },
  getElementById: id => elements[id] || null, addEventListener: () => {},
  querySelectorAll: () => [], querySelector: () => null, dispatchEvent: () => {},
  body: { appendChild: () => {} }
};
global.window = {};
global.navigator = { language: 'zh' };
global.localStorage = { getItem: () => null, setItem: () => {} };
global.location = { protocol: 'http:', search: '', href: 'http://localhost/' };
global.history = { replaceState: () => {} };
global.Blob = class { constructor(a) { this.parts = a; } };
global.URL = { createObjectURL: () => '', revokeObjectURL: () => {} };
global.alert = () => {};
global.fetch = () => Promise.reject(new Error('no fetch in node stub'));
eval(fs.readFileSync('site/assets/downloads.js', 'utf8'));
fs.mkdirSync(out, { recursive: true });
const dl = manifest.downloads.datasets;
const geo = Object.keys(dl).filter(a => dl[a].geo.files.length).slice(0, 3);
const sra = Object.keys(dl).filter(a => dl[a].sra.available).slice(0, 2);
fs.writeFileSync(out + '/web_geo.sh', window.DSH_DOWNLOADS.script(geo, 'geo'));
if (sra.length) fs.writeFileSync(out + '/web_sra.sh', window.DSH_DOWNLOADS.script(sra, 'sra'));
console.log('web generator OK · geo=' + geo.join(',') + (sra.length ? ' · sra=' + sra.join(',') : ''));
