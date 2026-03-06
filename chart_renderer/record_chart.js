#!/usr/bin/env node
/**
 * Record a cinematic D3.js narrative chart as video frames.
 *
 * Flow:
 *   1. Title on dark background, axes visible
 *   2. Blue line draws progressively (entire chart, all blue)
 *   3. Brief hold — viewer reads the full chart
 *   4. Crash segment transforms: blue → red line + red gradient fill
 *   5. Red flash + shock annotation, hold
 *   6. End-of-line value badge, final hold
 *
 * Usage:
 *   node chart_renderer/record_chart.js <data.json> <output_dir> [fps]
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function main() {
  const dataPath = process.argv[2];
  const outputDir = process.argv[3] || 'output/chart_frames';
  const fps = parseInt(process.argv[4] || '30', 10);

  if (!dataPath) {
    console.error('Usage: node record_chart.js <data.json> [output_dir] [fps]');
    process.exit(1);
  }

  const config = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
  const totalBars = config.ohlc.length;
  const shockIdx = config.shockIdx;
  const closes = config.ohlc.map(b => b.close);

  // Find crash segment boundaries
  let troughIdx = shockIdx;
  for (let i = shockIdx; i < Math.min(shockIdx + 12, totalBars); i++) {
    if (closes[i] <= closes[troughIdx]) troughIdx = i;
  }
  if (troughIdx === shockIdx) troughIdx = Math.min(shockIdx + 1, totalBars - 1);

  let maxDrop = 0;
  for (let i = Math.max(1, shockIdx - 5); i <= shockIdx; i++) {
    const drop = closes[i - 1] - closes[i];
    if (drop > maxDrop) maxDrop = drop;
  }
  const steepThresh = maxDrop * 0.35;
  let cliffStart = shockIdx;
  for (let i = shockIdx; i > Math.max(0, shockIdx - 6); i--) {
    const drop = i > 0 ? closes[i - 1] - closes[i] : 0;
    if (drop >= steepThresh) cliffStart = i;
    else break;
  }
  const peakIdx = Math.max(0, cliffStart - 1);

  console.log(`Crash segment: bars ${peakIdx}–${troughIdx} (of ${totalBars})`);

  // ── Pacing (slower) ──
  const barsPerFrame = 2;                              // 2 bars per frame = steady pace
  const titleHoldFrames    = Math.round(fps * 1.2);    // 1.2s title
  const chartHoldFrames    = Math.round(fps * 1.5);    // 1.5s hold on complete blue chart
  const colorTransFrames   = Math.round(fps * 0.6);    // 0.6s blue→red transition
  const flashFrames        = 5;                         // red flash
  const shockHoldFrames    = Math.round(fps * 2.5);    // 2.5s hold on crash
  const endHoldFrames      = Math.round(fps * 2.5);    // 2.5s final hold

  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Recording ${totalBars} bars @ ${fps}fps (D3 narrative)`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox',
           '--window-size=1920,1080', '--disable-gpu'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

  const htmlPath = path.resolve(__dirname, 'narrative_chart.html');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'domcontentloaded' });

  // ══ PHASE 0: Set up D3 chart — axes, grid, gradients ══
  await page.evaluate((cfg, peakI, troughI) => {
    const closes = cfg.ohlc.map(b => b.close);
    const dates = cfg.ohlc.map(b => b.time);
    const n = closes.length;

    // Title
    document.getElementById('t-title').textContent = cfg.title || cfg.ticker;
    document.getElementById('t-subtitle').textContent = cfg.subtitle || '';
    if (cfg.source) {
      const s = document.getElementById('source');
      s.textContent = `Source: ${cfg.source}`;
      s.style.display = 'block';
    }

    // Dimensions
    const margin = { top: 140, right: 120, bottom: 80, left: 90 };
    const width = 1920 - margin.left - margin.right;
    const height = 1080 - margin.top - margin.bottom;

    const svg = d3.select('#chart');
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const yMin = d3.min(closes) * 0.95;
    const yMax = d3.max(closes) * 1.05;
    const x = d3.scaleLinear().domain([0, n - 1]).range([0, width]);
    const y = d3.scaleLinear().domain([yMin, yMax]).range([height, 0]);

    // Grid
    const yTicks = y.ticks(6);
    yTicks.forEach(tick => {
      g.append('line')
        .attr('x1', 0).attr('x2', width)
        .attr('y1', y(tick)).attr('y2', y(tick))
        .attr('stroke', '#1E293B').attr('stroke-width', 1);
    });

    // Y labels
    yTicks.forEach(tick => {
      g.append('text')
        .attr('x', -14).attr('y', y(tick))
        .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
        .attr('fill', '#64748B').attr('font-size', '14px')
        .attr('font-family', 'Inter, sans-serif')
        .text(`$${tick.toFixed(0)}`);
    });

    // X labels — 5 clean dates
    const months = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec'];
    const xIndices = [0, Math.floor(n*0.25), Math.floor(n*0.5),
                      Math.floor(n*0.75), n-1];
    xIndices.forEach(i => {
      const d = new Date(dates[i]);
      if (isNaN(d)) return;
      g.append('text')
        .attr('x', x(i)).attr('y', height + 30)
        .attr('text-anchor', 'middle')
        .attr('fill', '#64748B').attr('font-size', '14px')
        .attr('font-family', 'Inter, sans-serif')
        .text(`${months[d.getMonth()]} ${d.getDate()}`);
    });

    // Gradients
    const defs = svg.append('defs');

    // Blue gradient
    const grad = defs.append('linearGradient')
      .attr('id', 'areaGrad').attr('x1','0').attr('y1','0').attr('x2','0').attr('y2','1');
    grad.append('stop').attr('offset','0%').attr('stop-color','#2962FF').attr('stop-opacity',0.28);
    grad.append('stop').attr('offset','100%').attr('stop-color','#2962FF').attr('stop-opacity',0.02);

    // Red gradient
    const gradR = defs.append('linearGradient')
      .attr('id', 'areaGradRed').attr('x1','0').attr('y1','0').attr('x2','0').attr('y2','1');
    gradR.append('stop').attr('offset','0%').attr('stop-color','#EF4444').attr('stop-opacity',0.30);
    gradR.append('stop').attr('offset','100%').attr('stop-color','#EF4444').attr('stop-opacity',0.03);

    // Red glow filter
    const filter = defs.append('filter').attr('id', 'redGlow')
      .attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%');
    filter.append('feGaussianBlur').attr('in', 'SourceGraphic')
      .attr('stdDeviation', '6').attr('result', 'blur');
    filter.append('feMerge')
      .selectAll('feMergeNode')
      .data(['blur', 'SourceGraphic'])
      .enter().append('feMergeNode')
      .attr('in', d => d);

    // Blue glow filter
    const blueGlow = defs.append('filter').attr('id', 'blueGlow')
      .attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%');
    blueGlow.append('feGaussianBlur').attr('in', 'SourceGraphic')
      .attr('stdDeviation', '4').attr('result', 'blur');
    blueGlow.append('feMerge')
      .selectAll('feMergeNode')
      .data(['blur', 'SourceGraphic'])
      .enter().append('feMergeNode')
      .attr('in', d => d);

    // Single area + line for the full chart (all blue initially)
    window._fullArea = g.append('path')
      .attr('fill', 'url(#areaGrad)').attr('stroke', 'none');
    window._fullLine = g.append('path')
      .attr('fill', 'none').attr('stroke', '#2962FF')
      .attr('stroke-width', 3.5).attr('stroke-linecap', 'round')
      .attr('filter', 'url(#blueGlow)');

    // Crash overlay — hidden initially, will appear during color transition
    window._crashArea = g.append('path')
      .attr('fill', 'url(#areaGradRed)').attr('stroke', 'none')
      .attr('opacity', 0);
    window._crashLine = g.append('path')
      .attr('fill', 'none').attr('stroke', '#EF4444')
      .attr('stroke-width', 4).attr('stroke-linecap', 'round')
      .attr('filter', 'url(#redGlow)')
      .attr('opacity', 0);

    // Tip dot
    window._tipDot = g.append('circle')
      .attr('r', 5).attr('fill', '#2962FF').attr('opacity', 0);

    // Store
    window._d3 = { g, x, y, closes, width, height, margin,
                   peakIdx: peakI, troughIdx: troughI };
    window._drawnUpTo = 0;
  }, config, peakIdx, troughIdx);

  await new Promise(r => setTimeout(r, 300));

  let frameNum = 0;
  const pad = (n) => String(n).padStart(6, '0');

  async function captureFrames(count) {
    for (let f = 0; f < count; f++) {
      const p = path.join(outputDir, `frame_${pad(frameNum)}.png`);
      await page.screenshot({ path: p, type: 'png' });
      frameNum++;
    }
  }

  // ══ PHASE 1: Title hold ══
  console.log('  Phase 1: Title hold...');
  await captureFrames(titleHoldFrames);

  // ══ PHASE 2: Progressive blue line draw ══
  console.log('  Phase 2: Drawing blue line...');

  let barIdx = 0;
  while (barIdx < totalBars) {
    const endIdx = Math.min(barIdx + barsPerFrame, totalBars);

    await page.evaluate((upTo) => {
      const { x, y, closes, height } = window._d3;

      const line = d3.line()
        .x((d, i) => x(d.idx)).y(d => y(d.val))
        .curve(d3.curveMonotoneX);
      const area = d3.area()
        .x(d => x(d.idx)).y0(height).y1(d => y(d.val))
        .curve(d3.curveMonotoneX);

      const pts = [];
      for (let i = 0; i < upTo; i++) pts.push({ idx: i, val: closes[i] });

      window._fullArea.attr('d', area(pts));
      window._fullLine.attr('d', line(pts));

      // Tip dot
      const tipI = upTo - 1;
      window._tipDot
        .attr('cx', x(tipI)).attr('cy', y(closes[tipI]))
        .attr('opacity', 1);

      window._drawnUpTo = upTo;
    }, endIdx);

    await new Promise(r => setTimeout(r, 8));
    const p = path.join(outputDir, `frame_${pad(frameNum)}.png`);
    await page.screenshot({ path: p, type: 'png' });
    frameNum++;

    barIdx = endIdx;
    if (barIdx % 20 === 0) {
      process.stdout.write(`  ${barIdx}/${totalBars} bars, ${frameNum} frames\r`);
    }
  }

  // Hide tip dot
  await page.evaluate(() => { window._tipDot.attr('opacity', 0); });

  // ══ PHASE 3: Hold on complete blue chart ══
  console.log('\n  Phase 3: Blue chart hold...');
  await captureFrames(chartHoldFrames);

  // ══ PHASE 4: Color transition — crash segment blue → red ══
  console.log('  Phase 4: Crash reveal (blue → red)...');

  // Pre-compute the crash segment path AND split blue paths
  await page.evaluate((peakI, troughI) => {
    const { g, x, y, closes, height } = window._d3;

    const line = d3.line()
      .x(d => x(d.idx)).y(d => y(d.val))
      .curve(d3.curveMonotoneX);
    const area = d3.area()
      .x(d => x(d.idx)).y0(height).y1(d => y(d.val))
      .curve(d3.curveMonotoneX);

    // Crash segment
    const crashPts = [];
    for (let i = peakI; i <= troughI; i++) crashPts.push({ idx: i, val: closes[i] });
    window._crashArea.attr('d', area(crashPts));
    window._crashLine.attr('d', line(crashPts));

    // Pre-crash blue segment (0 to peakIdx inclusive)
    const prePts = [];
    for (let i = 0; i <= peakI; i++) prePts.push({ idx: i, val: closes[i] });
    window._preArea = g.append('path')
      .attr('fill', 'url(#areaGrad)').attr('stroke', 'none')
      .attr('d', area(prePts)).attr('opacity', 0);
    window._preLine = g.append('path')
      .attr('fill', 'none').attr('stroke', '#2962FF')
      .attr('stroke-width', 3.5).attr('stroke-linecap', 'round')
      .attr('filter', 'url(#blueGlow)')
      .attr('d', line(prePts)).attr('opacity', 0);

    // Post-crash blue segment (troughIdx to end)
    const postPts = [];
    for (let i = troughI; i < closes.length; i++) postPts.push({ idx: i, val: closes[i] });
    window._postArea = g.append('path')
      .attr('fill', 'url(#areaGrad)').attr('stroke', 'none')
      .attr('d', area(postPts)).attr('opacity', 0);
    window._postLine = g.append('path')
      .attr('fill', 'none').attr('stroke', '#2962FF')
      .attr('stroke-width', 3.5).attr('stroke-linecap', 'round')
      .attr('filter', 'url(#blueGlow)')
      .attr('d', line(postPts)).attr('opacity', 0);
  }, peakIdx, troughIdx);

  // Animate: fade OUT full blue, fade IN split blue + red crash
  for (let f = 0; f < colorTransFrames; f++) {
    const t = (f + 1) / colorTransFrames;
    const ease = t * t * (3 - 2 * t);

    await page.evaluate((opacity) => {
      // Fade out the single full-blue path
      window._fullArea.attr('opacity', 1 - opacity);
      window._fullLine.attr('opacity', 1 - opacity);
      // Fade in the split blue segments (pre + post crash)
      window._preArea.attr('opacity', opacity);
      window._preLine.attr('opacity', opacity);
      window._postArea.attr('opacity', opacity);
      window._postLine.attr('opacity', opacity);
      // Fade in the red crash overlay
      window._crashArea.attr('opacity', opacity);
      window._crashLine.attr('opacity', opacity);
    }, ease);

    await new Promise(r => setTimeout(r, 10));
    const p = path.join(outputDir, `frame_${pad(frameNum)}.png`);
    await page.screenshot({ path: p, type: 'png' });
    frameNum++;
  }

  // ══ PHASE 5: Red flash + annotation ══
  console.log('  Phase 5: Flash + annotation...');

  await page.evaluate(() => {
    document.getElementById('shock-flash').style.background =
      'rgba(239, 83, 80, 0.18)';
  });
  await captureFrames(flashFrames);
  await page.evaluate(() => {
    document.getElementById('shock-flash').style.background =
      'rgba(239, 83, 80, 0)';
  });

  if (config.shockLabel) {
    await page.evaluate((label, sub) => {
      const ann = document.getElementById('annotation');
      document.getElementById('ann-label').textContent = label;
      if (sub) document.getElementById('ann-sub').textContent = sub;
      ann.style.display = 'block';
      ann.style.top = '25%';
      ann.style.right = '10%';
      ann.style.left = 'auto';
    }, config.shockLabel, config.shockSub || '');
  }

  await captureFrames(shockHoldFrames);

  await page.evaluate(() => {
    document.getElementById('annotation').style.display = 'none';
  });

  // ══ PHASE 6: Value badge + final hold ══
  console.log('  Phase 6: Badge + final hold...');

  const lastClose = closes[closes.length - 1];
  const firstClose = closes[0];
  const isUp = lastClose >= firstClose;

  await page.evaluate((val, up, margin) => {
    const badge = document.getElementById('badge');
    const { x, y, closes } = window._d3;
    const lastIdx = closes.length - 1;

    badge.textContent = `$${val.toFixed(0)}`;
    badge.style.background = up ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)';
    badge.style.color = up ? '#10B981' : '#EF4444';
    badge.style.border = `1px solid ${up ? '#10B981' : '#EF4444'}`;
    badge.style.display = 'block';
    badge.style.left = `${margin.left + x(lastIdx) + 14}px`;
    badge.style.top = `${margin.top + y(val) - 14}px`;
  }, lastClose, isUp, { left: 90, top: 140 });

  await captureFrames(endHoldFrames);

  await browser.close();

  const dur = (frameNum / fps).toFixed(1);
  console.log(`  ✓ ${frameNum} frames (${dur}s @ ${fps}fps)`);
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
