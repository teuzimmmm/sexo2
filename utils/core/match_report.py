#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Registro estruturado de uma tentativa de aplicar skin.

POR QUE ISTO EXISTE

O log do Rose é um fluxo de linhas de várias threads ao mesmo tempo. Dá para
descobrir o que houve, mas só lendo tudo e reconstruindo a ordem na cabeça. Foi
exatamente o que aconteceu com a skin 11116 em 24/09: sobrou "forte associação,
não prova" porque ninguém tinha, num lugar só, a linha do tempo de *uma*
tentativa — quando a preparação começou, quando o processo do jogo apareceu,
quanto tempo viveu, quando sumiu, com que código a ferramenta saiu.

Este módulo resolve isso sem mexer no log existente. Cada tentativa vira:

1. **uma linha de resumo** no log normal, legível de relance:

       [MATCH] skin=11116 resultado=126 (processo do LoL não foi observado)
       preparo=7.26s total=52.1s tentativas=1 jogo=nunca-visto avisos=GAME_NOT_SEEN

2. **um arquivo JSON** em `logs/matches/`, com a linha do tempo completa. É o
   que permite comparar dez partidas e dizer "sempre que a skin é 16.18 o
   processo morre em 40 s" — ou seja, passar de associação para evidência.

REGRAS DE OURO

- Nunca levanta exceção. Diagnóstico que derruba o programa que ele deveria
  diagnosticar é pior do que diagnóstico nenhum. Tudo aqui é best-effort.
- Não muda comportamento. Só observa.
- Não guarda nada identificável além do que já vai para o log do Rose.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.core.logging import get_logger

log = get_logger()

#: Quantos relatórios manter em disco. O suficiente para comparar uma sessão
#: inteira de jogo sem virar depósito.
MAX_RELATORIOS = 60


class MatchReport:
    """Coleta eventos de uma tentativa e entrega um resumo no fim."""

    def __init__(self, skins: Optional[List[str]] = None):
        self.skins = list(skins or [])
        self.iniciado_em = time.monotonic()
        self.iniciado_relogio = datetime.now()
        self.eventos: List[Dict[str, Any]] = []
        self.avisos: List[str] = []
        self.tentativas = 0
        self.preparo_s: Optional[float] = None
        self._lock = threading.Lock()
        self._jogo_visto_em: Optional[float] = None
        self._jogo_perdido_em: Optional[float] = None
        self._pids: List[int] = []
        self._encerrado = False

    # -- coleta ------------------------------------------------------------

    def evento(self, nome: str, **dados: Any) -> None:
        """Anota um acontecimento com o instante relativo ao início."""
        try:
            with self._lock:
                self.eventos.append({
                    "t": round(time.monotonic() - self.iniciado_em, 3),
                    "evento": nome,
                    **dados,
                })
        except Exception:
            pass

    def aviso(self, codigo: str) -> None:
        """Anota que um diagnóstico foi mostrado ao usuário."""
        try:
            with self._lock:
                if codigo not in self.avisos:
                    self.avisos.append(codigo)
            self.evento("aviso", codigo=codigo)
        except Exception:
            pass

    def jogo_visto(self, pids) -> None:
        try:
            novos = [p for p in pids if p not in self._pids]
            if not novos:
                return
            with self._lock:
                self._pids.extend(novos)
                if self._jogo_visto_em is None:
                    self._jogo_visto_em = time.monotonic()
            self.evento("jogo_visto", pids=novos)
        except Exception:
            pass

    def jogo_perdido(self) -> None:
        try:
            with self._lock:
                if self._jogo_perdido_em is None:
                    self._jogo_perdido_em = time.monotonic()
            self.evento("jogo_perdido", vida_s=self.vida_do_jogo_s)
        except Exception:
            pass

    def nova_tentativa(self, numero: int) -> None:
        self.tentativas = numero
        self.evento("tentativa", numero=numero)

    # -- leitura -----------------------------------------------------------

    @property
    def vida_do_jogo_s(self) -> Optional[float]:
        """Quanto tempo o processo do LoL existiu, se deu para observar."""
        if self._jogo_visto_em is None:
            return None
        fim = self._jogo_perdido_em or time.monotonic()
        return round(fim - self._jogo_visto_em, 1)

    @property
    def _estado_do_jogo(self) -> str:
        if self._jogo_visto_em is None:
            return "nunca-visto"
        if self._jogo_perdido_em is not None:
            return f"perdido-apos-{self.vida_do_jogo_s}s"
        return f"vivo-por-{self.vida_do_jogo_s}s"

    # -- encerramento ------------------------------------------------------

    def encerrar(self, codigo: int, descricao: str = "") -> None:
        """Escreve a linha de resumo e o arquivo JSON. Seguro chamar uma vez só."""
        try:
            if self._encerrado:
                return
            self._encerrado = True
            total = round(time.monotonic() - self.iniciado_em, 1)
            preparo = f"{self.preparo_s:.2f}s" if self.preparo_s is not None else "n/d"
            skins = ",".join(self.skins) or "n/d"
            avisos = ",".join(self.avisos) or "nenhum"
            log.info(
                "[MATCH] skin=%s resultado=%s (%s) preparo=%s total=%ss "
                "tentativas=%d jogo=%s avisos=%s",
                skins, codigo, descricao or "sem descrição", preparo, total,
                self.tentativas, self._estado_do_jogo, avisos,
            )
            self._gravar(codigo, descricao, total)
        except Exception as exc:
            log.debug("[MATCH] Não consegui encerrar o relatório: %s", exc)

    def como_dicionario(self, codigo: int, descricao: str, total: float) -> Dict[str, Any]:
        return {
            "inicio": self.iniciado_relogio.isoformat(timespec="seconds"),
            "skins": self.skins,
            "resultado": codigo,
            "resultado_descricao": descricao,
            "preparo_s": self.preparo_s,
            "total_s": total,
            "tentativas": self.tentativas,
            "jogo": {
                "estado": self._estado_do_jogo,
                "pids": self._pids,
                "vida_s": self.vida_do_jogo_s,
            },
            "avisos": self.avisos,
            "linha_do_tempo": self.eventos,
        }

    def _gravar(self, codigo: int, descricao: str, total: float) -> None:
        try:
            from utils.core.paths import get_user_data_dir
            pasta = get_user_data_dir() / "logs" / "matches"
            pasta.mkdir(parents=True, exist_ok=True)
            etiqueta = (self.skins[0] if self.skins else "sem-skin").replace("/", "_")[:40]
            nome = f"{self.iniciado_relogio:%Y%m%d-%H%M%S}-{etiqueta}.json"
            caminho = pasta / nome
            caminho.write_text(
                json.dumps(self.como_dicionario(codigo, descricao, total),
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._podar(pasta)
        except Exception as exc:
            log.debug("[MATCH] Não consegui gravar o relatório: %s", exc)

    @staticmethod
    def _podar(pasta) -> None:
        """Mantém só os relatórios mais recentes."""
        try:
            arquivos = sorted(pasta.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for velho in arquivos[MAX_RELATORIOS:]:
                velho.unlink(missing_ok=True)
        except Exception:
            pass


class NullMatchReport(MatchReport):
    """Relatório que não registra nada — para caminhos que não querem custo."""

    def evento(self, nome: str, **dados: Any) -> None:
        pass

    def encerrar(self, codigo: int, descricao: str = "") -> None:
        pass
