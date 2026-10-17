# Referências e dependências

- hudhook, Andrea Venuta, MIT, commit
  `72e1cc062c35df847b703e5507b82eb21d80d82c`:
  <https://github.com/veeenu/hudhook>.
  O host usa a API pública e a estrutura dos exemplos/testes DX11 como referência.
- imgui-rs / Dear ImGui, MIT, dependências transitivas de hudhook.
- MinHook, licença BSD de duas cláusulas, dependência transitiva de hudhook.
- windows-rs, Microsoft, MIT ou Apache-2.0.
- serde e serde_json, MIT ou Apache-2.0.
- base64, MIT ou Apache-2.0, no helper de OCR.
- Medidas dos recortes de títulos: Sygnano/aram-mayhem-tracker, MIT, commit
  `7c28471bf5b511e545d8d1c38b63707157edb134`; aviso completo em
  `licenses/sygnano.txt`. Não foi incorporado seu aplicativo Tauri, modelo OCR
  ou serviço estatístico.

A licença MIT do hudhook é reproduzida em `licenses/hudhook.txt`. Distribuição
futura de binários deve incluir também os avisos completos das dependências
resolvidas no Cargo.lock. Este protótipo não faz parte do instalador.
