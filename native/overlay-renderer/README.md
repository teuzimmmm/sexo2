# Renderer do SEXO2

DLL própria do processo SEXO2: Direct3D 11 com suporte BGRA, swapchain de composição
DXGI, árvore DirectComposition e texto Direct2D/DirectWrite. Não contém hooks,
acesso a processos do jogo, servidor, browser, loop próprio ou rede.

Compilar com `python scripts/build_overlay_renderer.py` em Windows x64 com MSVC
Build Tools e Windows SDK. Usa somente bibliotecas do Windows SDK e CRT estático;
sem DLL adicional de runtime Visual C++. O source segue a licença do repositório.

A ABI C `s2_create(HWND, void**)`, `s2_draw(state, width, height, header, body,
footer)`, `s2_driver(state)` e `s2_destroy(state)` deve ser usada na thread de UI
que possui o HWND. `s2_create` rejeita HWND de outros processos. Os textos UTF-16
são limitados a 8192 unidades por campo. Dimensões: 240–840 por 40–1140 pixels.
Erros retornam HRESULT; COM e todos os recursos GPU pertencem ao objeto e são
liberados antes de destruir a janela. Tenta hardware, depois WARP explicitamente.

`sexo2/overlay/win32.py` fornece ciclo de vida, posição, foco, hotkeys e
ocultação. `composition.py` carrega a DLL por caminho fixo do pacote com busca
de dependências restrita à pasta da DLL e System32. O renderer não conhece LCU,
contas, partidas ou dados LoLalytics: recebe somente texto de apresentação.

A composição externa é destinada a janela/sem bordas. Testes de pixels e z-order
usam janelas sintéticas em Windows; não comprovam funcionamento em LoL/Vanguard
nem suporte à tela cheia exclusiva. O laboratório hudhook é outro componente,
sem relação com essa DLL de produção.
