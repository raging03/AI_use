import puppeteer from 'puppeteer';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 参数：node screenshot_cards.mjs <html路径> <输出目录> <文章slug>
// slug 用于按日期+名称建子目录，例如：20260515_claude-blackmail
const htmlArg = process.argv[2];
const outArg  = process.argv[3];
const slug    = process.argv[4] || 'article';

const htmlFile = htmlArg ? path.resolve(htmlArg) : path.join(__dirname, '小红书_图文.html');

// 按日期 + slug 建子目录，防止覆盖历史图片
const today     = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
                    .replace(/\//g, '');                        // → "20260515"
const subDir    = `${today}_${slug}`;
const baseOut   = outArg ? path.resolve(outArg) : path.join(__dirname, '小红书图片');
const outputDir = path.join(baseOut, subDir);

if (!fs.existsSync(htmlFile)) {
  console.error(`❌ HTML 文件不存在：${htmlFile}`);
  process.exit(1);
}

fs.mkdirSync(outputDir, { recursive: true });

const browser = await puppeteer.launch({ headless: 'new' });
const page    = await browser.newPage();

// 2x 清晰度，宽 750px（小红书标准宽）
await page.setViewport({ width: 750, height: 1334, deviceScaleFactor: 2 });
await page.goto(`file://${htmlFile}`, { waitUntil: 'networkidle0' });

const cards = await page.$$('.card');
console.log(`找到 ${cards.length} 张卡片`);

const saved = [];
for (let i = 0; i < cards.length; i++) {
  const box      = await cards[i].boundingBox();
  const label    = i === 0 ? 'card_01_封面' : `card_${String(i + 1).padStart(2, '0')}`;
  const filename = path.join(outputDir, `${label}.png`);
  await page.screenshot({
    path: filename,
    clip: { x: box.x, y: box.y, width: box.width, height: box.height },
  });
  saved.push(filename);
  console.log(`✅ ${label}.png`);
}

await browser.close();

console.log(`\n📁 输出目录：${outputDir}`);
console.log(`🎉 共 ${saved.length} 张图片`);
console.log(`📌 封面图：${path.join(outputDir, 'card_01_封面.png')}`);
console.log(`📄 正文图：card_02.png ~ card_0${saved.length}.png`);
