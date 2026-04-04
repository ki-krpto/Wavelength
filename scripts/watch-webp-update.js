#!/usr/bin/env node
/**
 * Watch for new webp images and update ruffleGames.json
 * Run this in background while assets are downloading
 */

const fs = require('fs');
const path = require('path');

const baseDir = 'C:/Users/aj/Documents/Wavelength/assets/games';
const webpDir = path.join(baseDir, 'webp');
const gamesFile = 'C:/Users/aj/Documents/Wavelength/_data/ruffleGames.json';

let lastWebpCount = 0;
let lastUpdateCount = 0;

function getWebpMap() {
  const webpFiles = fs.readdirSync(webpDir)
    .filter(f => f.endsWith('.webp') && fs.statSync(path.join(webpDir, f)).size > 0);
  
  const map = {};
  webpFiles.forEach(f => {
    const baseName = path.parse(f).name.toLowerCase();
    map[baseName] = 'webp/' + f;
  });
  return map;
}

function updateGames() {
  const webpMap = getWebpMap();
  const currentCount = Object.keys(webpMap).length;
  
  // Only update if new images were added
  if (currentCount === lastWebpCount) return;
  
  console.log(`[${new Date().toLocaleTimeString()}] Found ${currentCount} webp images (${currentCount - lastWebpCount} new)`);
  lastWebpCount = currentCount;
  
  // Update JSON
  const games = JSON.parse(fs.readFileSync(gamesFile, 'utf8'));
  let updated = 0;
  
  for (const game of games) {
    const slug = game.slug.replace(/\//g, '-').toLowerCase();
    
    if (webpMap[slug] && game.thumbnail !== webpMap[slug]) {
      game.thumbnail = webpMap[slug];
      updated++;
    }
  }
  
  if (updated > 0) {
    fs.writeFileSync(gamesFile, JSON.stringify(games, null, 2) + '\n');
    console.log(`[${new Date().toLocaleTimeString()}] Updated ${updated} games`);
    lastUpdateCount += updated;
  }
}

console.log('Starting background updater...');
console.log(`Watching: ${webpDir}`);
console.log(`Updating: ${gamesFile}`);
console.log('Press Ctrl+C to stop\n');

// Initial scan
updateGames();

// Check every 5 seconds for new images
setInterval(updateGames, 5000);
