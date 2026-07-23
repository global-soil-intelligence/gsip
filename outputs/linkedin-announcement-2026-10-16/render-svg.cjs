const sharp = require('/Users/justinhart/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const path = require('node:path');
const source = path.join(__dirname, 'gsip-open-soil-library-linkedin-v1.svg');
const preview = path.join(__dirname, 'gsip-open-soil-library-svg-preview.png');
sharp(source).png().toFile(preview).then(info => {
  console.log(JSON.stringify({preview, width: info.width, height: info.height}));
}).catch(error => { console.error(error.message); process.exitCode = 1; });
