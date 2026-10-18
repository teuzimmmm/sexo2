#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Códigos de retorno de `OverlayManager.mk_run_overlay`.

POR QUE ESTE ARQUIVO EXISTE (não apague achando que é redundante):

O Rose oficial só distinguia 0 (deu certo) de qualquer-outra-coisa (falhou).
O Teste 0.3 acrescentou situações em que a aplicação da skin termina sem
sucesso mas TAMBÉM sem erro: o usuário pediu parada de emergência, ou o
limite de segurança liberou o LoL antes de a skin ficar pronta. Nos dois
casos o Rose se comportou exatamente como deveria.

Sem este módulo, `inject_skin` tratava esses retornos como falha e disparava
um aviso "Injection failed" por cima do diagnóstico honesto da bandeja — ou
seja, o recurso de parada de emergência acusava a si mesmo de ter quebrado.

A regra é: `EXPECTED_STOPS` são desfechos deliberados. Eles continuam
retornando False para o chamador (a skin de fato não está ativa), mas não
geram alarme de erro. Quem precisa avisar o usuário nesses casos é o
diagnóstico da bandeja, que já tem o contexto certo.
"""

# Sucesso: overlay rodou durante a partida.
OK = 0

# Falhas reais da ferramenta de skin.
BUILD_TIMEOUT = 124  # mkoverlay estourou o tempo de preparação
MISSING_PREREQUISITE = 127  # pasta do LoL ou mod-tools.exe ausente

# Desfechos deliberados — o Rose agiu como planejado.
SAFETY_RELEASE = 125  # limite de pausa atingido; LoL liberado sem skin
GAME_NEVER_SEEN = 126  # ferramenta terminou sem o processo do jogo aparecer
EMERGENCY_STOP = 130  # usuário pediu "Parar Rose nesta partida"

#: Retornos que NÃO devem gerar alarme de erro ao usuário.
EXPECTED_STOPS = frozenset({SAFETY_RELEASE, GAME_NEVER_SEEN, EMERGENCY_STOP})

#: Texto curto para o log, por código. Serve para o log dizer o que houve
#: em vez de repetir "failed" para tudo.
DESCRIPTIONS = {
    OK: "overlay concluído",
    BUILD_TIMEOUT: "tempo esgotado ao preparar a skin",
    MISSING_PREREQUISITE: "pré-requisito ausente (pasta do LoL ou mod-tools)",
    SAFETY_RELEASE: "LoL liberado pelo limite de segurança antes da skin",
    GAME_NEVER_SEEN: "processo do LoL não foi observado",
    EMERGENCY_STOP: "parada de emergência pedida nesta partida",
}


def is_expected_stop(code: int) -> bool:
    """True quando o código representa um encerramento deliberado, não um erro."""
    return code in EXPECTED_STOPS


def describe(code: int) -> str:
    """Descrição curta para log; devolve o próprio código se for desconhecido."""
    return DESCRIPTIONS.get(code, f"código {code}")
