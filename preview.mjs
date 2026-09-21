// npm install --no-save playwright; npx playwright install chromium
// node scripts/preview.mjs /absolute/path/to/meridian-schedule
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const base=path.resolve(process.argv[2]||'.');
const options={headless:true};
if(process.env.CHROMIUM_PATH){options.executablePath=process.env.CHROMIUM_PATH;options.args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'];}
const browser=await chromium.launch(options);
const page=await browser.newPage({viewport:{width:1500,height:1050},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(path.join(base,'outputs/dashboard.html')).href);
await page.screenshot({path:path.join(base,'outputs/dashboard_overview.png'),fullPage:true});
await page.getByRole('button',{name:'Schedule',exact:true}).click();
await page.locator('#phase').selectOption('Software');await page.locator('#path').selectOption('Critical');
const rows=await page.locator('#schedule-table tbody tr').count();if(!rows)throw Error('Filtered schedule is empty');
await page.screenshot({path:path.join(base,'outputs/dashboard_schedule.png'),fullPage:true});
await page.locator('#search').fill('NO_MATCH_EXPECTED');if(await page.locator('#schedule-table tbody tr').count()!==0)throw Error('Search filter failed');
await page.getByRole('button',{name:'Risks',exact:true}).click();await page.screenshot({path:path.join(base,'outputs/dashboard_risks.png'),fullPage:true});
await page.getByRole('button',{name:'Health',exact:true}).click();if(await page.locator('table').first().locator('tbody tr').count()!==14)throw Error('Health count');
await page.getByRole('button',{name:'Resources',exact:true}).click();if(await page.locator('table').first().locator('tbody tr').count()!==6)throw Error('Resource pool count');
await page.getByRole('button',{name:'Changes',exact:true}).click();if(!await page.getByText('CR-001',{exact:true}).first().isVisible())throw Error('Changes missing');
await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Overview',exact:true}).click();await page.screenshot({path:path.join(base,'outputs/dashboard_mobile.png'),fullPage:true});
await browser.close();if(errors.length)throw Error(errors.join('\n'));
await fs.writeFile(path.join(base,'outputs/browser_checks.json'),JSON.stringify({page_errors:errors,filtered_software_critical_rows:rows,checks:['six navigation tabs','phase and critical filters','empty search','14 health rows','six resource pools','change visibility','mobile preview']},null,2));console.log('Browser checks passed');
