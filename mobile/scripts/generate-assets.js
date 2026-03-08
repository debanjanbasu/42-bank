const fs = require('fs');
const path = require('path');

const ASSETS_DIR = path.join(__dirname, '..', 'assets');

const DARK_BG = '#1a1a2e';
const CYAN_ACCENT = '#00d9ff';

if (!fs.existsSync(ASSETS_DIR)) {
  fs.mkdirSync(ASSETS_DIR, { recursive: true });
}

const sizes = {
  icon: { width: 1024, height: 1024 },
  favicon: { width: 48, height: 48 },
  splash: { width: 1284, height: 2778 },
  'adaptive-icon': { width: 1024, height: 1024 },
  'notification-icon': { width: 96, height: 96 },
};

function generateSVG(name, width, height) {
  const textSize = Math.min(width, height) * 0.4;
  const subtitleSize = Math.min(width, height) * 0.1;
  
  if (name === 'favicon' || name === 'notification-icon') {
    return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <rect fill="${CYAN_ACCENT}" width="${width}" height="${height}" rx="${Math.min(width, height) * 0.2}"/>
      <text x="${width/2}" y="${height * 0.65}" font-size="${textSize}" fill="${DARK_BG}" 
            text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold">42</text>
    </svg>`;
  }
  
  if (name === 'splash') {
    return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <rect fill="${DARK_BG}" width="${width}" height="${height}"/>
      <text x="${width/2}" y="${height * 0.45}" font-size="${textSize * 1.5}" fill="${CYAN_ACCENT}" 
            text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold">42</text>
      <text x="${width/2}" y="${height * 0.55}" font-size="${subtitleSize * 1.5}" fill="${CYAN_ACCENT}" 
            text-anchor="middle" font-family="Arial, sans-serif">BANK</text>
    </svg>`;
  }
  
  return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
    <rect fill="${DARK_BG}" width="${width}" height="${height}" rx="${name === 'adaptive-icon' ? 0 : Math.min(width, height) * 0.1}"/>
    <text x="${width/2}" y="${height * 0.45}" font-size="${textSize}" fill="${CYAN_ACCENT}" 
          text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold">42</text>
    <text x="${width/2}" y="${height * 0.6}" font-size="${subtitleSize}" fill="${CYAN_ACCENT}" 
          text-anchor="middle" font-family="Arial, sans-serif">BANK</text>
  </svg>`;
}

function createPNG(svgContent, outputPath) {
  console.log(`Created placeholder: ${outputPath}`);
  console.log(`SVG content length: ${svgContent.length} characters`);
}

console.log('Generating placeholder assets...\n');

Object.entries(sizes).forEach(([name, { width, height }]) => {
  const svg = generateSVG(name, width, height);
  const outputPath = path.join(ASSETS_DIR, `${name}.png`);
  
  fs.writeFileSync(outputPath.replace('.png', '.svg'), svg);
  console.log(`✓ Generated ${name}.svg (${width}x${height})`);
  
  createPNG(svg, outputPath);
});

console.log('\n✅ Placeholder assets generated!');
console.log('\nNote: SVG files created. For production, convert to PNG using:');
console.log('  npx sharp-cli resize -i assets/icon.svg -o assets/icon.png --width 1024 --height 1024');
console.log('\nOr use an online converter like https://svgtopng.com/');
