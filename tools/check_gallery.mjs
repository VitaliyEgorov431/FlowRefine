/** Real browser acceptance check for a saved offline gallery (no external network). */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const workspace = path.resolve(new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const runtime = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES ||= path.join(runtime, 'node/node_modules');
const helper = 'C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1022.11436/skills/presentations/container_tools/runtime_helpers.mjs';
const {importRuntimeModule} = await import(pathToFileURL(helper).href);
const playwright = await importRuntimeModule('playwright');
const chromium = playwright.chromium || playwright.default?.chromium;
const target = path.resolve(process.argv[2] || 'demo/index.html');
const output = path.resolve(process.argv[3] || 'demo/qa_gallery');
await fs.mkdir(output, {recursive:true});
const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
try {
  const page = await browser.newPage({viewport:{width:1400,height:1000},acceptDownloads:true});
  const errors=[]; page.on('pageerror', error=>errors.push(String(error)));
  await page.goto(pathToFileURL(target).href);
  const options=await page.locator('#task option').count();
  if(!options) throw Error('No task options');
  for(const mode of ['B1','B2','B3']) {
    await page.locator('#mode').selectOption(mode);
    if(!(await page.locator('#before img').count())) throw Error('Initial chart missing');
    if(!(await page.locator('#after img').count())) throw Error('Edited chart missing: '+mode);
  }
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  const downloadPromise=page.waitForEvent('download');
  await page.locator('#after button').filter({hasText:'Download SVG'}).click();
  const download=await downloadPromise;
  const saved=path.join(output,'downloaded_chart.svg');
  await download.saveAs(saved);
  const svg=await fs.readFile(saved,'utf8');
  if(!svg.includes('<svg') || /<script\b/i.test(svg)) throw Error('SVG download invalid');
  await page.locator('#task').selectOption(String(options-1));
  await page.setViewportSize({width:420,height:900});
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  if(errors.length) throw Error(errors.join('\n'));
  console.log(JSON.stringify({tasks:options,modesChecked:3,svgDownload:true,browserErrors:errors,screenshots:output}));
} finally {await browser.close();}
