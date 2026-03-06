#!/usr/bin/env node
/**
 * Quick debug: load chart with all data at once, take screenshots to verify
 * that candles actually render. Also tests progressive update() approach.
 */
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function main() {
  const dataPath = process.argv[2] || 'output/chart_frames/chart_data.json';
  const config = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));

  console.log(`Loaded ${config.ohlc.length} bars`);
  console.log(`  First: ${config.ohlc[0].time}  Last: ${config.ohlc[config.ohlc.length - 1].time}`);
  console.log(`  Shock idx: ${config.shockIdx} (${config.ohlc[config.shockIdx]?.time})`);

  // Check for duplicate dates
  const dates = config.ohlc.map(b => b.time);
  const unique = new Set(dates);
  if (dates.length !== unique.size) {
    console.error(`  ✗ DUPLICATE DATES: ${dates.length} total, ${unique.size} unique`);
    // Find duplicates
    const seen = {};
    dates.forEach((d, i) => {
      if (seen[d] !== undefined) console.error(`    dup: "${d}" at index ${seen[d]} and ${i}`);
      seen[d] = i;
    });
  } else {
    console.log(`  ✓ All ${dates.length} dates unique`);
  }

  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  const htmlPath = path.resolve(__dirname, 'tv_chart.html');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'domcontentloaded' });

  // ── Test 1: Load ALL data at once (bulk setData) ──
  console.log('\n[Test 1] Bulk setData — all candles at once...');
  await page.evaluate((cfg) => {
    const chart = LightweightCharts.createChart(document.getElementById('chart'), {
      width: 1920, height: 1080,
      layout: {
        background: { type: 'solid', color: '#131722' },
        textColor: '#D1D4DC',
        fontFamily: 'Inter, -apple-system, sans-serif',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      rightPriceScale: { borderColor: '#363A45' },
      timeScale: { borderColor: '#363A45', barSpacing: 10 },
    });

    const cs = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: '#26A69A', downColor: '#EF5350',
      borderUpColor: '#26A69A', borderDownColor: '#EF5350',
      wickUpColor: '#26A69A', wickDownColor: '#EF5350',
    });
    cs.setData(cfg.ohlc);

    const vs = chart.addSeries(LightweightCharts.HistogramSeries, {
      priceFormat: { type: 'volume' }, priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vs.setData(cfg.volumes);

    const sma9s = chart.addSeries(LightweightCharts.LineSeries, {
      color: '#FF9800', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    });
    sma9s.setData(cfg.sma9.filter(d => d.value !== null));

    const sma20s = chart.addSeries(LightweightCharts.LineSeries, {
      color: '#2962FF', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    });
    sma20s.setData(cfg.sma20.filter(d => d.value !== null));

    const bbu = chart.addSeries(LightweightCharts.LineSeries, {
      color: 'rgba(41,98,255,0.4)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    });
    bbu.setData(cfg.bbUpper.filter(d => d.value !== null));

    const bbl = chart.addSeries(LightweightCharts.LineSeries, {
      color: 'rgba(41,98,255,0.4)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    });
    bbl.setData(cfg.bbLower.filter(d => d.value !== null));

    chart.timeScale().fitContent();
    window._chart = chart;
  }, config);

  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: 'output/debug_chart_full.png', type: 'png' });
  console.log('  ✓ Saved output/debug_chart_full.png');

  // ── Test 2: Progressive update() — add 30 bars one by one ──
  console.log('\n[Test 2] Progressive update() — first 30 bars...');

  // Navigate fresh page
  const page2 = await browser.newPage();
  await page2.setViewport({ width: 1920, height: 1080 });
  await page2.goto(`file://${htmlPath}`, { waitUntil: 'domcontentloaded' });

  // Create empty chart
  await page2.evaluate(() => {
    const chart = LightweightCharts.createChart(document.getElementById('chart'), {
      width: 1920, height: 1080,
      layout: {
        background: { type: 'solid', color: '#131722' },
        textColor: '#D1D4DC',
        fontFamily: 'Inter, -apple-system, sans-serif',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      rightPriceScale: { borderColor: '#363A45' },
      timeScale: { borderColor: '#363A45', barSpacing: 12, rightOffset: 5 },
    });

    window._chart2 = chart;
    window._cs2 = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: '#26A69A', downColor: '#EF5350',
      borderUpColor: '#26A69A', borderDownColor: '#EF5350',
      wickUpColor: '#26A69A', wickDownColor: '#EF5350',
    });
    window._vs2 = chart.addSeries(LightweightCharts.HistogramSeries, {
      priceFormat: { type: 'volume' }, priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
  });

  // Add bars one by one
  for (let i = 0; i < Math.min(30, config.ohlc.length); i++) {
    await page2.evaluate((bar, vol) => {
      window._cs2.update(bar);
      if (vol) window._vs2.update(vol);
      window._chart2.timeScale().scrollToPosition(2, false);
    }, config.ohlc[i], config.volumes[i]);
    await new Promise(r => setTimeout(r, 30));
  }

  await new Promise(r => setTimeout(r, 300));
  await page2.screenshot({ path: 'output/debug_chart_progressive_30.png', type: 'png' });
  console.log('  ✓ Saved output/debug_chart_progressive_30.png');

  // ── Test 3: Screenshot at shock point ──
  console.log('\n[Test 3] Progressive update() — up to shock bar...');
  for (let i = 30; i <= Math.min(config.shockIdx, config.ohlc.length - 1); i++) {
    await page2.evaluate((bar, vol) => {
      window._cs2.update(bar);
      if (vol) window._vs2.update(vol);
      window._chart2.timeScale().scrollToPosition(2, false);
    }, config.ohlc[i], config.volumes[i]);
  }
  await new Promise(r => setTimeout(r, 300));
  await page2.screenshot({ path: 'output/debug_chart_at_shock.png', type: 'png' });
  console.log('  ✓ Saved output/debug_chart_at_shock.png');

  await browser.close();
  console.log('\nDone. Check output/debug_chart_*.png files.');
}

main().catch(e => { console.error(e); process.exit(1); });
