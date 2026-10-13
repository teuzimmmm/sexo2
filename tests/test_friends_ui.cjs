const test=require('node:test'),assert=require('node:assert/strict');
const {memberStatus,profileSelections}=require('../Pengu Loader/plugins/ROSE-Amigos/index.js');
test('status never claims injection success and separates other lobbies',()=>{
 assert.equal(memberStatus({connected:true,sameLobby:false}),'Em outro lobby');
 assert.equal(memberStatus({connected:true,sameLobby:true,supportsTools:false}),'Atualize o SEXO2 deste participante');
 assert.equal(memberStatus({connected:true,sameLobby:true,supportsTools:true,ready:true,skinReceived:true}),'Pronto · escolha recebida');
});
test('profile submission validates selected IDs against current catalog',()=>{
 const champions=[{championId:11,selectedSkinId:11001,skins:[{skinId:11001,name:'Arcane'},{skinId:11002,name:'Project'}]}];
 assert.deepEqual(profileSelections(champions,{11:11002}),{11:{skinId:11002,name:'Project'}});
 assert.deepEqual(profileSelections(champions,{11:22002}),{});
});
