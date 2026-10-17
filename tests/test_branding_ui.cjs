const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('Pengu Loader/plugins/ROSE-I18n/index.js','utf8');
test('brand catalog labels, preserve attribution and dynamic user fields',()=>{
 const window={};
 const strings={'Rose settings':'Configurações do Rose','Selected {name} in Rose':'Selecionado {name} no Rose','Based on Rose':'Baseado em Rose'};
 vm.runInNewContext(source,{window,localStorage:{getItem:()=>JSON.stringify({strings,language:'pt_BR'})},setTimeout:()=>0,console});
 assert.equal(window.RoseI18n.t('Rose settings'),'Configurações do SEXO2');
 assert.equal(window.RoseI18n.t('Selected {name} in Rose',{name:'Rose - nome pessoal'}),'Selecionado Rose - nome pessoal no SEXO2');
 assert.equal(window.RoseI18n.tAny('Rose settings'),'Configurações do SEXO2');
 assert.equal(window.RoseI18n.t('Based on Rose'),'Baseado em Rose');
 assert.equal(window.RoseI18n.tAny('Meu mod Rose particular'),'Meu mod Rose particular');
});
