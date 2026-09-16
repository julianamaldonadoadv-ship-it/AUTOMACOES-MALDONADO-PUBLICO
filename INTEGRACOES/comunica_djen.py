# -*- coding: utf-8 -*-
"""
Integracao com a API Comunica / DJEN (PJe - CNJ)
=================================================
Consulta as comunicacoes processuais eletronicas (intimacoes e publicacoes)
do Diario de Justica Eletronico Nacional. Fonte oficial e gratuita.

Uso principal: acompanhar processos do escritorio (por OAB) - por
exemplo, cliente que defende a Caixa Economica Federal.

Endpoint (producao):
    https://comunicaapi.pje.jus.br/api/v1/comunicacao

Doc oficial (Swagger): https://app.swaggerhub.com/apis-docs/cnj/pcp/1.0.0

Parametros aceitos pela API (os mais uteis):
    numeroOab, ufOab            -> filtra pela OAB do advogado destinatario
    nomeParte                   -> filtra por nome de uma das partes
    numeroProcesso              -> numero unico (so digitos)
    siglaTribunal               -> ex.: TRF1, TJSP, TRT2
    dataDisponibilizacaoInicio  -> YYYY-MM-DD
    dataDisponibilizacaoFim     -> YYYY-MM-DD
    meio                        -> D (diario) / E (eletronico)
    pagina, itensPorPagina      -> paginacao (max 100 por pagina)

CLI:
    py INTEGRACOES/comunica_djen.py --oab 123456 --uf SP --dias 7
    py INTEGRACOES/comunica_djen.py --oab 123456 --uf SP --dias 7 --salvar pub.json
    py INTEGRACOES/comunica_djen.py --parte "CAIXA ECONOMICA FEDERAL" --tribunal TRF3 --dias 3
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta

import requests

BASE_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Maldonado-Controladoria/1.0",
    "Accept": "application/json",
}
MAX_ITENS_POR_PAGINA = 100
MAX_TENTATIVAS = 10  # a API oscila muito: alterna entre "ocupado" e count:0 fantasma


def _requisitar(params, exigir_dados=False):
    """
    Faz uma chamada com retry/backoff.

    A API Comunica e instavel: para a MESMA consulta ela alterna, de forma
    aleatoria, entre tres respostas:
      - HTTP 200 com status:error "sistema muito ocupado"
      - HTTP 200 com status:success mas count:0 e items:[] (falso-vazio)
      - HTTP 200 com status:success e os dados corretos
    As duas primeiras sao apenas "estou ocupada" disfarcadas. Por isso, quando
    'exigir_dados=True' (1a pagina), tratamos o falso-vazio como retentavel.
    """
    tentativa = 0
    espera = 2.0
    while True:
        tentativa += 1
        motivo = None
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            dados = resp.json()
        except (requests.RequestException, ValueError) as e:
            dados, motivo = None, f"rede/parse ({e})"
        else:
            if dados.get("status") == "error" and "ocupado" in dados.get("message", "").lower():
                motivo = "ocupado"
            elif exigir_dados and not (dados.get("items") or []):
                motivo = "falso-vazio (count 0)"

        if motivo is None:
            return dados

        if tentativa >= MAX_TENTATIVAS:
            if dados is not None and dados.get("status") != "error":
                # Esgotou as tentativas de 1a pagina sempre vazio: aceita como vazio real.
                return dados
            raise RuntimeError(f"API Comunica indisponivel apos {tentativa} tentativas ({motivo}).")

        time.sleep(espera)
        espera = min(espera * 1.6, 20)


def consultar(
    oab_numero=None,
    oab_uf=None,
    nome_parte=None,
    numero_processo=None,
    sigla_tribunal=None,
    data_inicio=None,
    data_fim=None,
    meio=None,
    limite=None,
):
    """
    Consulta comunicacoes com paginacao automatica.

    Datas: str 'YYYY-MM-DD' ou objeto date. Se omitidas, usa o dia de hoje.
    Retorna lista de dicts (cada item = uma comunicacao).
    """
    if isinstance(data_inicio, date):
        data_inicio = data_inicio.isoformat()
    if isinstance(data_fim, date):
        data_fim = data_fim.isoformat()

    hoje = date.today().isoformat()
    data_inicio = data_inicio or hoje
    data_fim = data_fim or hoje

    base_params = {
        "dataDisponibilizacaoInicio": data_inicio,
        "dataDisponibilizacaoFim": data_fim,
        "itensPorPagina": MAX_ITENS_POR_PAGINA,
    }
    if oab_numero:
        base_params["numeroOab"] = str(oab_numero)
    if oab_uf:
        base_params["ufOab"] = oab_uf.upper()
    if nome_parte:
        base_params["nomeParte"] = nome_parte
    if numero_processo:
        base_params["numeroProcesso"] = "".join(filter(str.isdigit, numero_processo))
    if sigla_tribunal:
        base_params["siglaTribunal"] = sigla_tribunal.upper()
    if meio:
        base_params["meio"] = meio.upper()

    itens = []
    pagina = 1
    total = None
    while True:
        params = dict(base_params, pagina=pagina)
        # Na 1a pagina exigimos dados (para nao aceitar o falso-vazio da API).
        # Nas demais, o vazio e legitimo: significa fim da paginacao.
        dados = _requisitar(params, exigir_dados=(pagina == 1))

        if total is None:
            total = dados.get("count", 0)
        lote = dados.get("items") or []
        if not lote:
            break

        itens.extend(lote)

        if limite and len(itens) >= limite:
            itens = itens[:limite]
            break
        if len(itens) >= total:
            break
        pagina += 1
        time.sleep(0.4)  # respeita o rate limit

    return itens


def resumir(item):
    """Extrai os campos essenciais de uma comunicacao para relatorio."""
    advs = []
    for a in item.get("destinatarioadvogados") or []:
        adv = a.get("advogado", {})
        oab = f"{adv.get('numero_oab', '')}/{adv.get('uf_oab', '')}".strip("/")
        advs.append(f"{adv.get('nome', '')} (OAB {oab})")
    # O DJEN marca o polo de cada parte em `destinatarios[].polo` ("A" ativo /
    # "P" passivo). E' o unico lugar em que essa informacao vem estruturada - o
    # texto da publicacao varia por tribunal e o TJPR, por exemplo, publica so a
    # ementa, sem qualificar as partes. Quem precisa saber de que lado o
    # escritorio esta (apuracao de KPI) usa `partes_polo`, nao o texto.
    destinatarios = item.get("destinatarios") or []
    partes = [d.get("nome", "") for d in destinatarios]
    partes_polo = [{"nome": d.get("nome", ""), "polo": d.get("polo")}
                   for d in destinatarios]
    return {
        "id": item.get("id"),
        "data": item.get("data_disponibilizacao"),
        "tribunal": item.get("siglaTribunal"),
        "orgao": item.get("nomeOrgao"),
        "tipo": item.get("tipoComunicacao"),
        "classe": item.get("nomeClasse"),
        "processo": item.get("numeroprocessocommascara") or item.get("numero_processo"),
        "partes": partes,
        "partes_polo": partes_polo,
        "advogados": advs,
        "link": item.get("link"),
        "texto": (item.get("texto") or "").strip(),
    }


def _imprimir(resumos):
    if not resumos:
        print("Nenhuma comunicacao encontrada no periodo/filtro informado.")
        return
    print(f"\n{'='*70}\n{len(resumos)} comunicacao(oes) encontrada(s)\n{'='*70}")
    for r in resumos:
        print(f"\n[{r['data']}] {r['tribunal']} - {r['tipo']}")
        print(f"  Processo: {r['processo']}  ({r['classe']})")
        print(f"  Orgao:    {r['orgao']}")
        if r["advogados"]:
            print(f"  Advs:     {'; '.join(r['advogados'])}")
        print(f"  Link:     {r['link']}")
        trecho = r["texto"][:280].replace("\n", " ")
        print(f"  Trecho:   {trecho}...")


def main():
    # Windows: console usa cp1252 por padrao e quebra acentos vindos do JSON UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Consulta publicacoes/intimacoes no DJEN (API Comunica CNJ)")
    ap.add_argument("--oab", help="Numero da OAB do advogado do cliente")
    ap.add_argument("--uf", help="UF da OAB (ex.: SP)")
    ap.add_argument("--parte", help="Nome de uma das partes (ex.: CAIXA ECONOMICA FEDERAL)")
    ap.add_argument("--processo", help="Numero unico do processo")
    ap.add_argument("--tribunal", help="Sigla do tribunal (ex.: TRF3, TJSP)")
    ap.add_argument("--dias", type=int, default=1, help="Ultimos N dias (padrao: 1 = hoje)")
    ap.add_argument("--inicio", help="Data inicio YYYY-MM-DD (sobrepoe --dias)")
    ap.add_argument("--fim", help="Data fim YYYY-MM-DD")
    ap.add_argument("--limite", type=int, help="Limite de itens")
    ap.add_argument("--salvar", help="Salva o JSON completo no caminho informado")
    args = ap.parse_args()

    if not any([args.oab, args.parte, args.processo]):
        ap.error("Informe ao menos um filtro: --oab (com --uf), --parte ou --processo")

    if args.inicio:
        inicio, fim = args.inicio, (args.fim or date.today().isoformat())
    else:
        fim = args.fim or date.today().isoformat()
        inicio = (datetime.fromisoformat(fim).date() - timedelta(days=args.dias - 1)).isoformat()

    print(f"Consultando DJEN de {inicio} a {fim}...")
    itens = consultar(
        oab_numero=args.oab,
        oab_uf=args.uf,
        nome_parte=args.parte,
        numero_processo=args.processo,
        sigla_tribunal=args.tribunal,
        data_inicio=inicio,
        data_fim=fim,
        limite=args.limite,
    )
    resumos = [resumir(i) for i in itens]
    _imprimir(resumos)

    if args.salvar:
        with open(args.salvar, "w", encoding="utf-8") as f:
            json.dump({"consulta": vars(args), "total": len(itens), "itens": itens}, f, ensure_ascii=False, indent=2)
        print(f"\nSalvo: {args.salvar}")


if __name__ == "__main__":
    main()
