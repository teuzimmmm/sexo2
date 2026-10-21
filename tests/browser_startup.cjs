const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  const old='div[id^=index_loading_div]:before{content:"";background-image:url(/lol-game-data/assets/v1/profile-icons/7.jpg);background-size:cover;width:144px;height:144px;border-radius:50%}div[id^=index_loading_div]:after{content:"Rose"}';
  await page.setContent('<html><head><style>'+old+'</style></head><body><div id="index_loading_div42"></div></body></html>');
  await page.evaluate(()=>{window.__sexo2AberturaOn=true;});
  const script=fs.readFileSync('Pengu Loader/plugins/SEXO2-Startup/index.js','utf8');
  await page.addScriptTag({content:script});
  // The signed core may append its original CSS after our plugin.
  await page.addStyleTag({content:old});
  await page.addScriptTag({content:script});
  const css=await page.locator('#index_loading_div42').evaluate(el=>{
   const before=getComputedStyle(el,'::before'),after=getComputedStyle(el,'::after');
   return {bg:getComputedStyle(el).backgroundColor,before:before.content,after:after.content};
  });
  // The client's own branding is gone; the opening overlay (#0d0e10) replaces it, once.
  assert.equal(css.bg,'rgb(13, 14, 16)');assert.equal(css.after,'none');assert.equal(css.before,'none');
  assert.equal(await page.locator('#sexo2-startup-style').count(),1);
  assert.equal(await page.locator('#sexo2-abertura').count(),1);
  assert.equal(await page.locator('#sexo2-abertura .g').count(),5);
  console.log('Startup opening: mounts once over the loading div, without bridge, including late core styles.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
