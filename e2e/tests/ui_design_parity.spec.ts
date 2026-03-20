import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { test, type Page } from '@playwright/test';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';

type DiffResult = {
  baselinePath: string;
  diffPixels: number;
  diffRatio: number;
  width: number;
  height: number;
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..', '..');
const DESIGN_ASSETS_DIR = path.join(ROOT, 'doc', '02_Loan-Navigator-AI', 'attached_assets');
const OUTPUT_DIR = path.join(ROOT, 'e2e', 'test-results', 'ui-design-parity');
const UI_PARITY_ENABLED = process.env.UI_PARITY === '1';

function listDesignPngs(): string[] {
  if (!fs.existsSync(DESIGN_ASSETS_DIR)) return [];
  const minWidth = 900;
  const minHeight = 500;
  return fs
    .readdirSync(DESIGN_ASSETS_DIR)
    .filter((f: string) => f.toLowerCase().endsWith('.png'))
    .map((f: string) => path.join(DESIGN_ASSETS_DIR, f))
    .filter((p) => {
      try {
        const img = readPng(p);
        return img.width >= minWidth && img.height >= minHeight;
      } catch {
        return false;
      }
    })
    .sort();
}

function readPng(p: string): PNG {
  const buf = fs.readFileSync(p);
  const img = PNG.sync.read(buf);
  return img;
}

function ensureDir(p: string) {
  fs.mkdirSync(p, { recursive: true });
}

async function ensureLoggedInIfPrompted(page: Page) {
  try {
    await page.getByLabel('Username').waitFor({ state: 'visible', timeout: 800 });
    await page.getByLabel('Username').fill('officer');
    await page.getByLabel('Password').fill('Password123!');
    await page.getByRole('button', { name: 'Sign In' }).click();
  } catch {
    return;
  }
}

async function disableAnimations(page: Page) {
  await page.addStyleTag({
    content: `
      *,
      *::before,
      *::after {
        transition-duration: 0s !important;
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        scroll-behavior: auto !important;
        caret-color: transparent !important;
      }
    `,
  });
}

async function gotoStabilized(page: Page, routePath: string) {
  await page.goto(routePath, { waitUntil: 'domcontentloaded' });
  await ensureLoggedInIfPrompted(page);
  if (page.url().includes('/login')) {
    await page.waitForTimeout(150);
    await ensureLoggedInIfPrompted(page);
  }
  if (!page.url().endsWith(routePath)) {
    await page.goto(routePath, { waitUntil: 'domcontentloaded' });
  }
  await disableAnimations(page);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(250);
}

async function diffAgainstBaselinePng(page: Page, baselinePath: string, routePath: string, outputStem: string): Promise<DiffResult> {
  const baseline = readPng(baselinePath);
  await page.setViewportSize({ width: baseline.width, height: baseline.height });
  await gotoStabilized(page, routePath);
  const actualBuf = await page.screenshot({ fullPage: false, animations: 'disabled', caret: 'hide' });
  const actual = PNG.sync.read(actualBuf);

  const width = Math.min(baseline.width, actual.width);
  const height = Math.min(baseline.height, actual.height);
  const a = new PNG({ width, height });
  const b = new PNG({ width, height });
  PNG.bitblt(actual, a, 0, 0, width, height, 0, 0);
  PNG.bitblt(baseline, b, 0, 0, width, height, 0, 0);

  const diff = new PNG({ width, height });
  const diffPixels = pixelmatch(a.data, b.data, diff.data, width, height, { threshold: 0.1 });
  const diffRatio = diffPixels / (width * height);

  ensureDir(OUTPUT_DIR);
  const baselineCopy = path.join(OUTPUT_DIR, `${outputStem}.baseline.png`);
  const actualOut = path.join(OUTPUT_DIR, `${outputStem}.actual.png`);
  const diffOut = path.join(OUTPUT_DIR, `${outputStem}.diff.png`);

  fs.copyFileSync(baselinePath, baselineCopy);
  fs.writeFileSync(actualOut, actualBuf);
  fs.writeFileSync(diffOut, PNG.sync.write(diff));

  return { baselinePath, diffPixels, diffRatio, width, height };
}

test.describe('UI parity vs design attached_assets', () => {
  const routes: Array<{ key: string; path: string }> = [
    { key: 'borrower', path: '/' },
    { key: 'dashboard', path: '/dashboard' },
    { key: 'pipeline', path: '/pipeline' },
    { key: 'products', path: '/loan-products' },
    { key: 'officer-chat', path: '/officer-chat' },
  ];

  test('compute best baseline match for each route', async ({ page }) => {
    test.skip(!UI_PARITY_ENABLED, 'Set UI_PARITY=1 to run design parity diffs.');
    const baselines = listDesignPngs();
    if (baselines.length === 0) {
      throw new Error(`No design PNGs found at ${DESIGN_ASSETS_DIR}`);
    }

    const summary: Record<string, DiffResult> = {};
    const allScores: Record<string, Array<DiffResult & { baselineName: string }>> = {};
    for (const r of routes) {
      let best: DiffResult | null = null;
      const scores: Array<DiffResult & { baselineName: string }> = [];
      for (const baselinePath of baselines) {
        const stem = `${r.key}.${path.basename(baselinePath, '.png')}`;
        const result = await diffAgainstBaselinePng(page, baselinePath, r.path, stem);
        scores.push({ ...result, baselineName: path.basename(baselinePath) });
        if (!best || result.diffRatio < best.diffRatio) best = result;
      }
      if (!best) throw new Error(`No baseline comparisons produced for route ${r.path}`);
      summary[r.key] = best;
      allScores[r.key] = scores.sort((a, b) => a.diffRatio - b.diffRatio);
    }

    ensureDir(OUTPUT_DIR);
    fs.writeFileSync(path.join(OUTPUT_DIR, 'best-matches.json'), JSON.stringify(summary, null, 2));
    fs.writeFileSync(path.join(OUTPUT_DIR, 'all-scores.json'), JSON.stringify(allScores, null, 2));
    console.log(`UI design parity diffs written to: ${OUTPUT_DIR}`);
  });
});
