const fs = require('fs');
const path = require('path');

function walk(dir, base) {
  const entries = [];
  const files = fs.readdirSync(dir, { withFileTypes: true });
  for (const f of files) {
    const full = path.join(dir, f.name);
    if (f.isDirectory()) {
      entries.push(...walk(full, base));
    } else if (f.isFile()) {
      const rel = path.relative(base, full).split(path.sep).join('/');
      entries.push('./' + rel);
    }
  }
  return entries;
}

module.exports = function() {
  const root = path.join(process.cwd(), 'assets');
  const emojisDir = path.join(root, 'emojis');
  const stickersDir = path.join(root, 'stickers');
  let emojis = [];
  let stickers = [];
  try { if (fs.existsSync(emojisDir)) emojis = walk(emojisDir, process.cwd()); } catch (e) { emojis = []; }
  try { if (fs.existsSync(stickersDir)) stickers = walk(stickersDir, process.cwd()); } catch (e) { stickers = []; }
  return { emojis, stickers };
};
