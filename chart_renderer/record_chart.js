#!/usr/bin/env node
/**
 * Record a TradingView Lightweight Charts animation as video frames.
 *
 * Narrative flow (mirrors the simple Manim version):
 *   1. Load ALL data at once → show full chart
 *   2. Hold so viewer reads the chart
 *   3. Smooth zoom into the crash region
 *   4. Red flash + shock annotation
 *   5. Hold on zoomed crash
 *   6. Zoom back out to full chart
 *   7. Final hold, done
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

  // Timing (in frames)
  const fullHoldFrames   = fps * 2;     // 2s — viewer reads full chart
  const zoomInFrames     = fps * 1;     // 1s — smooth zoom into crash
  const flashFrames      = 4;           // quick red flash
  const shockHoldFrames  = Math.round(fps * 2.5); // 2.5s — hold on crash
  const zoomOutFrames    = Math.round(fps * 0.8); // 0.8s — zoom back out
  const endHoldFrames    = fps * 2;     // 2s — final hold

  fs.mkdirSync(outputDir, { recursive: true });

  console.log(`Recording ${totalBars} bars @ ${fps}fps (narrative zoom mode)`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox',
           '--window-size=1920,1080', '--disable-gpu'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

  const htmlPath = path.resolve(__dirname, 'tv_chart.html');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'domcontentloaded' });

  // ══ PHASE 0: Load ALL data at once ══
  await page.evaluate((cfg) => {
    const { ticker, exchange, interval, ohlc, volumes,
            sma9, sma20, bbUpper, bbLower } = cfg;

    document.getElementById('h-ticker').textContent =
      `${ticker} · ${interval} · ${exchange}`;

    const chart = LightweightCharts.createChart(
      document.getElementById('chart'), {
        width: 1920, height: 1080,
        layout: {
          background: { type: 'solid', color: '#131722' },
          textColor: '#D1D4DC',
          fontFamily: 'Inter, -apple-system, sans-serif',
          fontSize: 13,
        },
        grid: {
          vertLines: { color: '#2B2B43', style: 0 },
          horzLines: { color: '#2B2B43', style: 0 },
        },
        crosshair: { mode: 0 },
        rightPriceScale: {
          borderColor: '#363A45',
          scaleMargins: { top: 0.08, bottom: 0.22 },
          autoScale: true,
        },
        timeScale: {
          borderColor: '#363A45',
          timeVisible: false,
          rightOffset: 3,
          barSpacing: 12,
        },
      }
    );

    // Candlestick — load all data
    const candleSeries = chart.addSeries(
      LightweightCharts.CandlestickSeries, {
        upColor: '#26A69A', downColor: '#EF5350',
        borderUpColor: '#26A69A', borderDownColor: '#EF5350',
        wickUpColor: '#26A69A', wickDownColor: '#EF5350',
      }
    );
    candleSeries.setData(ohlc);

    // Volume — load all
    const volumeSeries = chart.addSeries(
      LightweightCharts.HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      }
    );
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });
    volumeSeries.setData(volumes);

    // SMA 9 (orange)
    const sma9Series = chart.addSeries(
      LightweightCharts.LineSeries, {
        color: '#FF9800', lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false, lastValueVisible: false,
      }
    );
    sma9Series.setData(sma9.filter(d => d.value !== null));

    // SMA 20 (blue)
    const sma20Series = chart.addSeries(
      LightweightCharts.LineSeries, {
        color: '#2962FF', lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false, lastValueVisible: false,
      }
    );
    sma20Series.setData(sma20.filter(d => d.value !== null));

    // BB upper
    const bbUpSeries = chart.addSeries(
      LightweightCharts.LineSeries, {
        color: 'rgba(41, 98, 255, 0.4)', lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false, lastValueVisible: false,
      }
    );
    bbUpSeries.setData(bbUpper.filter(d => d.value !== null));

    // BB lower
    const bbLowSeries = chart.addSeries(
      LightweightCharts.LineSeries, {
        color: 'rgba(41, 98, 255, 0.4)', lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false, lastValueVisible: false,
      }
    );
    bbLowSeries.setData(bbLower.filter(d => d.value !== null));

    // Fit all data into view
    chart.timeScale().fitContent();

    // Update OHLC header with last bar
    const last = ohlc[ohlc.length - 1];
    const prev = ohlc.length > 1 ? ohlc[ohlc.length - 2] : last;
    const chg = last.close - prev.close;
    const chgPct = (chg / prev.close * 100);
    const sign = chg >= 0 ? '+' : '';
    const color = chg >= 0 ? '#26A69A' : '#EF5350';
    document.getElementById('h-ohlc').innerHTML =
      `<span style="color:${color}">` +
      `O ${last.open.toFixed(2)} &nbsp; ` +
      `H ${last.high.toFixed(2)} &nbsp; ` +
      `L ${last.low.toFixed(2)} &nbsp; ` +
      `C ${last.close.toFixed(2)} &nbsp; ` +
      `${sign}${chg.toFixed(2)} (${sign}${chgPct.toFixed(2)}%)</span>`;

    // Store refs for zoom animation
    window._chart = chart;
    window._candleSeries = candleSeries;
  }, config);

  // Let chart settle
  await new Promise(r => setTimeout(r, 400));

  let frameNum = 0;
  const pad = (n) => String(n).padStart(6, '0');

  async function captureFrames(count) {
    for (let f = 0; f < count; f++) {
      const framePath = path.join(outputDir, `frame_${pad(frameNum)}.png`);
      await page.screenshot({ path: framePath, type: 'png' });
      frameNum++;
    }
  }

  // ══ PHASE 1: Hold on full chart — viewer reads it ══
  console.log('  Phase 1: Full chart hold...');
  await captureFrames(fullHoldFrames);

  // ══ PHASE 2: Smooth zoom into crash region ══
  // We animate barSpacing from current (~12) up to ~40 and scroll so
  // the shock bar is centered. This creates a smooth "zoom in" effect.
  console.log('  Phase 2: Zoom into crash...');

  const startBarSpacing = 12;
  const endBarSpacing = 40;
  const shockIdx = config.shockIdx;
  const shockTime = config.ohlc[shockIdx].time;

  // Get the visible range info before zoom
  for (let f = 0; f < zoomInFrames; f++) {
    const t = (f + 1) / zoomInFrames; // 0→1 eased
    const ease = t * t * (3 - 2 * t);  // smoothstep
    const spacing = startBarSpacing + (endBarSpacing - startBarSpacing) * ease;

    await page.evaluate((sp, sTime, totalBars, shockI) => {
      window._chart.timeScale().applyOptions({ barSpacing: sp });
      // Scroll so shock bar is roughly centered
      // scrollToPosition takes a bar offset from the right edge
      const visibleBars = Math.floor(1920 / sp);
      const barsFromRight = totalBars - shockI;
      const targetOffset = barsFromRight - Math.floor(visibleBars / 2);
      window._chart.timeScale().scrollToPosition(-targetOffset, false);
    }, spacing, shockTime, totalBars, shockIdx);

    await new Promise(r => setTimeout(r, 15));
    const framePath = path.join(outputDir, `frame_${pad(frameNum)}.png`);
    await page.screenshot({ path: framePath, type: 'png' });
    frameNum++;
  }

  // Update OHLC header to show the shock bar's data
  const shockBar = config.ohlc[shockIdx];
  const prevBar = shockIdx > 0 ? config.ohlc[shockIdx - 1] : shockBar;
  await page.evaluate((bar, prev) => {
    const chg = bar.close - prev.close;
    const chgPct = (chg / prev.close * 100);
    const sign = chg >= 0 ? '+' : '';
    const color = chg >= 0 ? '#26A69A' : '#EF5350';
    document.getElementById('h-ohlc').innerHTML =
      `<span style="color:${color}">` +
      `O ${bar.open.toFixed(2)} &nbsp; ` +
      `H ${bar.high.toFixed(2)} &nbsp; ` +
      `L ${bar.low.toFixed(2)} &nbsp; ` +
      `C ${bar.close.toFixed(2)} &nbsp; ` +
      `${sign}${chg.toFixed(2)} (${sign}${chgPct.toFixed(2)}%)</span>`;
  }, shockBar, prevBar);

  // ══ PHASE 3: Red flash + shock annotation ══
  console.log('  Phase 3: Shock flash + annotation...');

  // Red flash
  await page.evaluate(() => {
    document.getElementById('shock-flash').style.background =
      'rgba(239, 83, 80, 0.25)';
  });
  await captureFrames(flashFrames);

  // Fade flash out
  await page.evaluate(() => {
    document.getElementById('shock-flash').style.background =
      'rgba(239, 83, 80, 0)';
  });

  // Show annotation
  if (config.shockLabel) {
    await page.evaluate((label, sub) => {
      const ann = document.getElementById('annotation');
      document.getElementById('ann-label').textContent = label;
      if (sub) document.getElementById('ann-sub').textContent = sub;
      ann.style.display = 'block';
      ann.style.top = '30%';
      ann.style.right = '15%';
      ann.style.left = 'auto';
    }, config.shockLabel, config.shockSub || '');
  }

  // ══ PHASE 4: Hold on zoomed crash ══
  console.log('  Phase 4: Hold on crash...');
  await captureFrames(shockHoldFrames);

  // Hide annotation
  await page.evaluate(() => {
    document.getElementById('annotation').style.display = 'none';
  });

  // ══ PHASE 5: Zoom back out to full chart ══
  console.log('  Phase 5: Zoom out...');
  for (let f = 0; f < zoomOutFrames; f++) {
    const t = (f + 1) / zoomOutFrames;
    const ease = t * t * (3 - 2 * t);
    const spacing = endBarSpacing + (startBarSpacing - endBarSpacing) * ease;

    await page.evaluate((sp) => {
      window._chart.timeScale().applyOptions({ barSpacing: sp });
      window._chart.timeScale().fitContent();
    }, spacing);

    await new Promise(r => setTimeout(r, 15));
    const framePath = path.join(outputDir, `frame_${pad(frameNum)}.png`);
    await page.screenshot({ path: framePath, type: 'png' });
    frameNum++;
  }

  // Ensure fully fitted
  await page.evaluate(() => {
    window._chart.timeScale().fitContent();
  });
  await new Promise(r => setTimeout(r, 100));

  // ══ PHASE 6: Final hold ══
  console.log('  Phase 6: Final hold...');
  await captureFrames(endHoldFrames);

  await browser.close();

  const totalDuration = (frameNum / fps).toFixed(1);
  console.log(`  ✓ ${frameNum} frames captured (${totalDuration}s @ ${fps}fps)`);
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
