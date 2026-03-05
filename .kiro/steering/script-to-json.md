---
inclusion: manual
---

# Script-to-JSON Conversion Guide

This steering file contains the complete rules for converting a raw narration script (.txt) into a structured video_script JSON payload.

## Reference Files
- Schema: #[[file:output/video_script_schema.json]]
- Example output: #[[file:output/asml_script.json]]

## Target Duration: 10-12 Minutes

The final video should be 10-12 minutes long. At ~150 words/minute narration speed, this means:
- Total narration: 1,500-1,800 words across all scenes
- Typical scene count: 25-35 scenes
- Average scene: 40-50 words (~16-20 seconds)

## Data Chart Minimum: 40-50% of Runtime

At least 40-50% of total narration words MUST be in `data_chart` scenes. Charts are the visual backbone — they keep viewers engaged and differentiate the channel from talking-head content. After generating the full script, calculate chart word percentage and add more data_chart scenes if below 40%.

If the input script is shorter than 1,500 words, you MUST expand it:
- Add data_chart scenes with narration that discusses the data (e.g., "Let's look at the numbers...")
- Add comparison scenes where the topic naturally invites A-vs-B analysis
- Add context scenes that deepen the narrative (history, background, implications)
- Keep expansions in the same voice/tone as the original author

If the input script is longer than 1,800 words, trim by:
- Removing repetitive points
- Tightening wordy sentences (without changing meaning)
- Merging scenes that cover the same beat

## Narration Voice & Tone

The narration should sound like Jeremy Clarkson explaining finance and technology — dry wit, dramatic pauses, absurd comparisons, and a sense of barely-contained amazement at how ridiculous the world is. Key traits:

- **Deadpan understatement**: "Their machines cost three hundred and eighty million dollars each. Which is, you know, quite a lot."
- **Absurd analogies**: Compare technical specs to everyday things ("a plasma forty times hotter than the surface of the sun — just to print a microchip")
- **Mock outrage**: "Because an IT bloke accidentally leaked their report early" — treat corporate disasters like pub anecdotes
- **Dramatic build-ups with deflating punchlines**: Build tension then undercut it ("Giants like Canon and Nikon eventually just… gave up. Because they were bored.")
- **Direct address**: Talk TO the viewer like a mate at the pub, not AT them like a lecturer
- **"And on that bombshell..."** energy: End with a punchy, memorable closer

When expanding short scripts, added narration MUST match this voice. No corporate-speak, no textbook language, no "it's important to note that..." filler. If a sentence sounds like it belongs in an annual report, rewrite it until it sounds like something you'd say after two pints.

## Step 1: Read & Split Narration

- Read the .txt file from scripts/input/.
- Split the raw text into scenes of 20-60 words each.
- PRESERVE the author's voice and wording. Do NOT rewrite narration. Only split for pacing.
- Each paragraph break is a natural scene boundary. Within long paragraphs, split at sentence boundaries.
- Count total words after splitting. Adjust to hit the 1,500-1,800 word target.

## Step 1b: Expand with "Second-Order" Engagement Questions

When expanding a short script to hit the 1,500-1,800 word target, use these investor-grade "Second-Order" questions to add depth and keep viewers hooked. Do NOT dump all of them — pick 2-4 that are relevant to the specific company and sprinkle them in where the content is getting too technical or too data-heavy. They act as "pattern interrupts" that re-engage the viewer.

### Placement Rules
- Insert AFTER a dense technical or data section (e.g., after 2-3 consecutive data_chart scenes)
- Use as a transition INTO a new analytical section ("But here's the question most people don't ask...")
- Frame as the narrator's voice, not a textbook — keep the author's tone
- Pair with `fullscreen_statement`, `stock_with_text`, or `quote_block` visual types
- Use `curious` or `skeptical` emotion to signal a shift in energy

### Question Bank (pick randomly, don't reuse across videos)

**Moat & Competitive Dynamics:**
- "If a competitor were handed $10 billion tomorrow, could they replicate this in 3 years?" (If yes, the moat is just a head start, not structural)
- "Does it get cheaper for them to serve the next customer, or do costs rise as they exhaust the easy market?" (Unit economics at scale)
- "If they raised prices 10% tomorrow, would customers leave — or is the product too embedded to quit?" (Switching cost test)

**Management & Capital Allocation:**
- "Are the new dollars they invest earning as much as the old ones, or are returns diminishing?" (Incremental ROIC)
- "Is the CEO's bonus tied to stock price — which can be gamed with buybacks — or to long-term metrics like Free Cash Flow?" (Incentive alignment)
- "Do they buy companies to actually grow, or are they empire-building with expensive acquisitions that lead to write-downs?" (M&A track record)

**Financial Integrity & Hidden Red Flags:**
- "Is Free Cash Flow consistently lagging behind Net Income? If so, they might be recording sales that haven't turned into cash yet." (Accounting quality)
- "What's the Stock-Based Compensation as a percentage of revenue? Many tech companies look profitable until you realize they're paying employees by printing shares." (Dilution risk)
- "Are there related-party transactions? Is the company renting its HQ from the CEO's brother?" (Governance leaks)

**The Inverse Thesis:**
- "What would have to be true for this company to go bankrupt in 10 years?" (Force a credible death path — if you can't imagine one, you're blinded by confirmation bias)
- "Who is the smartest person shorting this stock, and what's their strongest argument?" (If you can't debunk the bear case, you don't understand the risks)

**Customer & Ecosystem Health:**
- "Does a single customer account for more than 15% of sales? If that whale leaves, does the thesis collapse?" (Revenue concentration)
- "What do ex-employees say on Glassdoor? A toxic culture or departing engineers is a leading indicator that won't show in financials for 18 months." (Culture as signal)

## Step 2: Assign Visual Types

For each scene, choose the visual type that best matches the content:

| Content | Visual Type |
|---------|------------|
| Narrative/intro/outro | `stock_with_text` |
| Single key number | `stock_with_stat` |
| Financial data, trends, comparisons | `data_chart` |
| Stock price over time | `data_chart` (timeseries + Yahoo Finance ticker) |
| Market share / parts of whole | `data_chart` (donut) |
| A vs B comparison | `comparison` |
| List of points/timeline | `bullet_reveal` |
| Expert quote | `stock_quote` or `quote_block` |
| Social media reference | `social_card` |
| Dramatic closer / key takeaway | `fullscreen_statement` |
| Section divider | `section_title` |

### When to insert data_chart scenes
ADD a data_chart whenever the narration mentions:
- Stock prices, market cap, or share performance
- Revenue, sales, or financial metrics
- Market share percentages
- Growth rates or year-over-year comparisons
- Rankings or leaderboards
- Any specific numbers that would be clearer as a visualization

Use Yahoo Finance auto-fetch (ticker/tickers fields) for any publicly traded stock data. Use `value_type: "pct_change"` when comparing stocks at different price levels.

## Step 3: Craft Cinematic Keywords (CRITICAL)

Keywords drive stock footage quality. They must be cinematically crafted for Pexels search.

### Principles
1. Storyboard each scene visually — pick keywords for what the VIEWER should SEE, not abstract concepts.
2. Use a mix of macro (global impact) and micro (intricate technology) visuals.
3. Be specific and cinematic, never generic.

### Keyword Construction Rules

For each scene, think about the visual beats in the narration:

**Location/Establishing shots:**
- Use specific locations: "Netherlands aerial canal", "Amsterdam drone city", "Wall Street building"
- Add modifiers: "aerial", "drone", "timelapse", "night", "cinematic"

**Technology/Manufacturing:**
- "Cleanroom technician semiconductor", "microchip wafer close up"
- "Silicon wafer robotic arm", "semiconductor production line"
- "Vacuum chamber industrial", "precision optic lens"
- "Circuit board macro green", "industrial robot arm"
- Never use company names as keywords — use the product/process instead

**Financial/Market:**
- "Stock market trading screen", "trading chart monitor green red"
- "Bull market sculpture wall street", "stock market recovery chart"
- "Calm investor looking at charts" (only when narration is about investing)

**Energy/Physics:**
- "Solar flare close up", "plasma ball energy glow"
- "Industrial laser pulse beam", "abstract purple energy"

**Global Impact:**
- "World map digital connections", "data center server rack lights"
- "Shipping container port aerial", "traffic timelapse city"
- "Empty city street cinematic" (for "world stopping" moments)

**Consumer Tech:**
- "Smartphone close up hands", "using iPhone screen"
- "Neural network animation", "AI brain visualization"
- "Military drone technology", "futuristic tech display"

### BAD Keywords (NEVER use these)
- "man in office", "business meeting", "woman at computer"
- "technology", "innovation", "digital transformation"
- "success", "teamwork", "future concept"
- Any generic corporate stock photo terms

### Pexels Tips
- If a company name doesn't return results, use the industry: "semiconductor manufacturing", "microchip fabrication"
- Add quality modifiers: "cinematic", "close up", "macro", "aerial", "slow motion"
- Use "dark" or "night" for moody/dramatic scenes
- 2-3 keywords per scene, each keyword phrase should be 2-4 words

## Step 4: Transitions & Emotions

- Vary transitions between scenes. Don't repeat the same one consecutively.
- Good patterns: `fadeblack` between major sections, `smooth*` between related data scenes, `circle*` for reveals, `dissolve` for topic changes.
- Match emotion to narration tone: `analytical` for data, `excited` for surprises, `curious` for questions, `serious` for warnings, `confident` for strong claims.

## Step 5: Output

- Write the JSON to `output/<filename>_video_script.json`
- Move the .txt file to `scripts/input/done/`
- Output ONLY valid JSON matching the VideoScript schema
