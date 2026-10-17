# Host nativo isolado

Candidato de laboratório para substituir o motor de desenho, sem Electron,
Overwolf ou Game Bar. **Não é um overlay instalável no LoL.** Não há DLL,
injetor ou mecanismo de abertura do processo de outro aplicativo.

O hudhook instala um hook DX11 somente no executável deste host. Dear ImGui
desenha as projeções recebidas por stdin; nenhum HTTP, dado LCU ou arquivo de
usuário é acessado. `inject` está desabilitado. O motor não é ativado pelo SEXO2
normal. F8 recolhe/expande, F9 muda o cartão e a janela permite rolar o texto.

Em Windows, com Rust/C++ Build Tools instalados:

```powershell
cargo test --manifest-path native/overlay-host/Cargo.toml --locked
cargo build --manifest-path native/overlay-host/Cargo.toml --release --locked
python scripts/native_overlay_probe.py --host native/overlay-host/target/release/sexo2-overlay-host.exe
```

O teste usa dados sintéticos, valida callback de desenho e expiração e encerra
o filho com timeout. O resultado declara `leagueValidated: false`; não valida
pixels, tela cheia, integração com Vanguard nem consumo no computador do usuário.
Não gerar novo instalador com este host como se fosse a correção do jogo.

O recurso de injeção da dependência deve continuar desabilitado. Usar outra via
no jogo exige primeiro demonstrar compatibilidade e respeitar controles de acesso.
Licenças: [THIRD_PARTY.md](THIRD_PARTY.md). Contratos e etapas pendentes:
[OVERLAY_MOTOR.md](../../docs/OVERLAY_MOTOR.md).
