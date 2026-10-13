const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  const old='div[id^=index_loading_div]:before{content:"";background-image:url(/lol-game-data/assets/v1/profile-icons/7.jpg);background-size:cover;width:144px;height:144px;border-radius:50%}div[id^=index_loading_div]:after{content:"Rose"}';
  await page.setContent('<html><head><style>'+old+'</style></head><body><div id="index_loading_div42"></div></body></html>');
  const script=fs.readFileSync('Pengu Loader/plugins/SEXO2-Startup/index.js','utf8');
  await page.addScriptTag({content:script});
  // The signed core may append its original CSS after our plugin.
  await page.addStyleTag({content:old});
  await page.addScriptTag({content:script});
  const css=await page.locator('#index_loading_div42').evaluate(el=>{
   const before=getComputedStyle(el,'::before'),after=getComputedStyle(el,'::after');
   return {name:after.content,image:before.backgroundImage,size:before.backgroundSize,radius:before.borderRadius};
  });
  assert.equal(css.name,'"SEXO2"');assert.ok(css.image.includes('data:image/png;base64,'));
  assert.equal(css.size,'contain');assert.equal(css.radius,'0px');
  assert.equal(await page.locator('#sexo2-startup-style').count(),1);
  console.log('Startup branding: passes without bridge, including late core styles.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
