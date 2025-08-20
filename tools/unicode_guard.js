const fs=require('fs'),path=require('path');
const BIDI=/[\u202A-\u202E\u2066-\u2069]/, ZW=/[\u200B-\u200F\uFEFF]/;
const exts=new Set(['.js','.jsx','.ts','.tsx','.json','.md','.yml','.yaml','.css','.html']);
function walk(d,o=[]){for(const e of fs.readdirSync(d,{withFileTypes:true})){if(e.name.startsWith('.git'))continue;const p=path.join(d,e.name);e.isDirectory()?walk(p,o):o.push(p);}return o;}
const root=process.argv[2]||'.', files=walk(root);let bad=[];
for(const f of files){const ext=path.extname(f).toLowerCase();if(!exts.has(ext))continue;const s=fs.readFileSync(f,'utf8');if(BIDI.test(s)||ZW.test(s))bad.push(f);}
if(bad.length){console.error('Unicode guard failed; remove bidi/zero-width from files:');for(const f of bad)console.error('  -',f);process.exit(1);}else{console.log('Unicode guard passed.');}