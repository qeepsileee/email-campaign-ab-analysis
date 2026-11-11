import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const root=process.cwd();
const envText=await fs.readFile(path.join(root,'bi/.env'),'utf8');
const password=envText.split('\n').find(line=>line.startsWith('ADMIN_PASSWORD=')).slice('ADMIN_PASSWORD='.length);
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1600,height:1180},deviceScaleFactor:1});
const chartResponses=[];
page.on('response',async response=>{
  if(response.url().includes('/api/v1/chart/data')&&response.request().method()==='POST'){
    try {chartResponses.push({status:response.status(),body:await response.json()});} catch {}
  }
});
try {
await page.goto('http://localhost:8088/login/',{waitUntil:'networkidle'});
await page.locator('#username').fill('student');
await page.locator('#password').fill(password);
await page.locator('input[type=submit],button[type=submit]').first().click();
await page.goto('http://localhost:8088/superset/dashboard/hillstrom-email-experiment/',{waitUntil:'networkidle',timeout:90000});
await page.getByText('Purchase conversion',{exact:true}).first().waitFor({timeout:60000});
await page.waitForFunction(()=>document.querySelectorAll('canvas').length>=3,null,{timeout:60000});
await page.waitForTimeout(2500);
if(chartResponses.length<4)throw new Error(`Only ${chartResponses.length} chart queries completed`);
for(const response of chartResponses){
  if(response.status!==200)throw new Error(`Chart HTTP status ${response.status}: ${JSON.stringify(response.body)}`);
  for(const result of response.body.result??[]){
    if(result.error||result.status==='failed')throw new Error(JSON.stringify(result));
  }
}
console.log(`Dashboard rendered successfully; ${chartResponses.length} chart queries passed.`);
} finally {
await fs.mkdir(path.join(root,'reports/figures'),{recursive:true});
await page.screenshot({path:path.join(root,'reports/figures/superset_dashboard.png'),fullPage:true});
await browser.close();
}
