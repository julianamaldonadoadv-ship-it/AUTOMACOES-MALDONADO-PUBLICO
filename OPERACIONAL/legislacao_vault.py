"""Legislação no vault — CPC (Lei 13.105/2015) e MCR (Bacen) viram notas Obsidian.

    python OPERACIONAL/legislacao_vault.py cpc ~/Downloads/L13105.pdf
    python OPERACIONAL/legislacao_vault.py mcr ~/Downloads/ManualCompleto.pdf

Grava em BASE_CONHECIMENTO/06 - LEGISLACAO/. Reexecutar com um PDF novo (CPC compilado
reimpresso do Planalto, MCR de nova atualização) regera as notas da norma — elas são
artefato, não se editam à mão. Comentário humano vai nas notas-guia (`CPC-Guia-do-Escritorio`,
`MCR-Guia-do-Escritorio`), que este script NÃO sobrescreve se já existirem.

Duas armadilhas que o código trata (não desfazer):

- **CPC compilado traz a redação revogada ao lado da vigente.** No PDF do Planalto o texto
  revogado vem riscado — e o risco é um retângulo de 0,75 pt desenhado por cima, não um
  atributo da fonte. Sem detectar o desenho, o art. 921 sai com dois incisos III e dois § 4º,
  e a peça cita a redação morta. `_riscado()` confere se há traço cruzando o MEIO da linha
  (o sublinhado de link fica na base, e não pode ser confundido com risco).
- **MCR repete cabeçalho de seção em toda página, às vezes no meio do texto extraído.** A
  seção corrente sai do cabeçalho de cada página, não da ordem das páginas.
"""
from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "BASE_CONHECIMENTO" / "06 - LEGISLACAO"
MARCA = "<!-- gerado por OPERACIONAL/legislacao_vault.py — não editar à mão -->"


def _slug(txt: str, maximo: int = 60) -> str:
    s = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s[:maximo].rstrip("-")


def _romano(r: str) -> int:
    val = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total, ant = 0, 0
    for ch in reversed(r):
        v = val.get(ch, 0)
        total = total - v if v < ant else total + v
        ant = max(ant, v)
    return total


# ---------------------------------------------------------------------------- CPC

def _riscado(bbox, tracos) -> bool:
    x0, y0, x1, y1 = bbox
    h = y1 - y0
    meio_ini, meio_fim = y0 + 0.3 * h, y1 - 0.25 * h
    largura = x1 - x0
    if largura <= 0:
        return False
    # O Planalto desenha o risco de uma linha em VÁRIOS segmentos (62-252, 252-279, 279-533).
    # Testar segmento por segmento deixava passar texto revogado (ex.: o antigo parágrafo único
    # do art. 1.030 aparecia dentro do art. 1.029). Soma-se a cobertura de todos os segmentos.
    trechos = sorted((max(x0, r.x0), min(x1, r.x1)) for r in tracos
                     if meio_ini <= (r.y0 + r.y1) / 2 <= meio_fim and min(x1, r.x1) > max(x0, r.x0))
    coberto, fim = 0.0, x0
    for a, b in trechos:
        a = max(a, fim)
        if b > a:
            coberto += b - a
            fim = b
    return coberto / largura >= 0.6


def _linhas_cpc(pdf: Path):
    """Linhas do texto VIGENTE, com contagem do que foi descartado por estar riscado."""
    doc = fitz.open(pdf)
    riscadas = 0
    for pagina in doc:
        tracos = [it[1] for g in pagina.get_drawings() for it in g["items"]
                  if it[0] == "re" and it[1].height < 1.6 and it[1].width > 3]
        for bloco in pagina.get_text("dict")["blocks"]:
            for linha in bloco.get("lines", []):
                partes, houve_risco = [], False
                for sp in linha["spans"]:
                    if sp["font"].startswith(("Times", "FontAwesome")):
                        continue  # cabeçalho/rodapé do navegador e ícones
                    if not sp["text"].strip():
                        partes.append(sp["text"])
                        continue
                    if _riscado(sp["bbox"], tracos):
                        houve_risco = True
                        continue
                    partes.append(sp["text"])
                txt = "".join(partes).replace("\xa0", " ")
                txt = re.sub(r"\s+", " ", txt).strip()
                # Anotação "(Revogado pela Lei ...)" ao lado do texto riscado não é riscada:
                # sobrando só ela na linha, a linha inteira é redação morta.
                if houve_risco and not re.sub(r"\((?:Revogad|Redação|Incluíd|Vide|Vigência)[^)]*\)|Vigência|[\s.;,]",
                                              "", txt):
                    txt = ""
                if houve_risco and not txt:
                    riscadas += 1
                if txt:
                    yield txt
    _linhas_cpc.riscadas = riscadas


_RE_ART = re.compile(r"^Art\.\s*(\d{1,3}(?:\.\d{3})*)\s*(º|o)?((?:-[A-Z])?)\.?\s+(.*)$")
_INICIO_PARAG = re.compile(
    r"^(Art\.\s*\d|§\s*\d|Parágrafo único|[IVXLC]+\s*[-–]\s|[a-z]\)\s|\(Vide|\(Revogad|\(VETADO)")
_ESTRUTURA = re.compile(r"^(PARTE (GERAL|ESPECIAL)|LIVRO (COMPLEMENTAR|[IVX]+)|TÍTULO ([IVX]+|ÚNICO)|"
                        r"CAPÍTULO ([IVX]+|ÚNICO)(-[A-Z])?|Seção ([IVX]+|Única)(-[A-Z])?|Subseção ([IVX]+|Única))\b")


def _estrutura_cpc(pdf: Path):
    """Árvore plana: lista de (tipo, rotulo, nome) e ('art', numero, [paragrafos])."""
    linhas = list(_linhas_cpc(pdf))
    # Pula o preâmbulo (ementa, fórmula de promulgação) até a PARTE GERAL.
    ini = next(i for i, l in enumerate(linhas) if l == "PARTE GERAL")
    itens, i = [], ini
    atual = None
    while i < len(linhas):
        l = linhas[i]
        m_est = _ESTRUTURA.match(l)
        if m_est and len(l) < 60 and not l.endswith((";", ".", ",")):
            rotulo = m_est.group(0)
            resto = l[len(rotulo):].strip(" -–")
            nome = resto
            if not nome and i + 1 < len(linhas) and not _RE_ART.match(linhas[i + 1]) \
                    and not _ESTRUTURA.match(linhas[i + 1]):
                nome = linhas[i + 1]
                i += 1
                # nome em caixa alta pode quebrar em 2 linhas
                while (nome.isupper() and i + 1 < len(linhas) and linhas[i + 1].isupper()
                       and not _ESTRUTURA.match(linhas[i + 1]) and not _RE_ART.match(linhas[i + 1])):
                    nome += " " + linhas[i + 1]
                    i += 1
            atual = None
            itens.append(("est", rotulo, nome))
            i += 1
            continue
        # Linha que é SÓ "(Revogado pela Lei ...)" marca dispositivo revogado por inteiro, cujo texto
        # já saiu por estar riscado. Mantida, ela caía dentro do artigo anterior (as 4 do art. 945
        # apareciam no art. 944).
        if re.fullmatch(r"\(Revogad[oa]s? pel[oa] [^)]*\)", l):
            i += 1
            continue
        m_art = _RE_ART.match(l)
        if m_art:
            num = m_art.group(1) + (m_art.group(2) and "º" or "") + m_art.group(3)
            atual = ["art", num, [l]]
            itens.append(atual)
        elif atual is not None:
            # "§ 1º deste artigo" pode cair no início de linha por quebra do PDF: só abre
            # parágrafo novo se o anterior terminou (pontuação final ou anotação de redação).
            anterior = atual[2][-1].rstrip()
            terminou = anterior.endswith((".", ";", ":", ")", "Vigência", "VETADO"))
            if _INICIO_PARAG.match(l) and terminou:
                atual[2].append(l)
            else:
                atual[2][-1] += " " + l
        i += 1
    return itens


def _num_art(num: str) -> tuple:
    base = int(re.sub(r"\D", "", num.split("-")[0]))
    suf = num.split("-")[1] if "-" in num else ""
    return base, suf


def gerar_cpc(pdf: Path) -> dict:
    itens = _estrutura_cpc(pdf)
    pasta = DESTINO / "CPC"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "_original").mkdir(exist_ok=True)
    shutil.copy2(pdf, pasta / "_original" / "L13105-compilado.pdf")

    niveis = {"TÍTULO": "##", "CAPÍTULO": "###", "Seção": "####", "Subseção": "#####"}
    notas, parte, corrente = [], "", None
    mapa_art = {}
    for it in itens:
        if it[0] == "est":
            _, rot, nome = it
            if rot.startswith("PARTE"):
                parte = "PG" if "GERAL" in rot else "PE"
                continue
            if rot.startswith("LIVRO"):
                cod = "LC" if "COMPLEMENTAR" in rot else f"L{_romano(rot.split()[1])}"
                arquivo = f"CPC-{parte}-{cod}-{_slug(nome.title(), 50)}"
                corrente = {"arquivo": arquivo, "titulo": f"{rot} — {nome}",
                            "parte": "Parte Geral" if parte == "PG" else "Parte Especial",
                            "corpo": [], "arts": []}
                notas.append(corrente)
                continue
            nivel = next(v for k, v in niveis.items() if rot.startswith(k))
            corrente["corpo"].append(f"\n{nivel} {rot} — {nome}\n" if nome else f"\n{nivel} {rot}\n")
        else:
            _, num, pars = it
            if corrente is None:
                continue
            titulo = f"Art. {num}"
            if titulo in mapa_art:  # redação vigente repetida (risco não detectado) — acusa
                titulo += " (repetido — conferir no PDF)"
            mapa_art[f"Art. {num}"] = corrente["arquivo"]
            corrente["arts"].append(num)
            # A anotação de revogação pode quebrar em duas linhas no PDF ("(Revogado pela Lei nº 13.256, de"
            # + "2016)"), escapando do filtro por linha: filtra-se também o parágrafo já montado.
            pars = [p for p in pars if not re.fullmatch(r"\(Revogad[oa]s? pel[oa] [^)]*\)", p.strip())]
            corpo = "\n\n".join(pars)
            corrente["corpo"].append(f"\n###### {titulo}\n\n{corpo}\n")

    hoje = date.today().isoformat()
    for n in notas:
        prim, ult = n["arts"][0], n["arts"][-1]
        cab = (f"---\ntipo: legislacao\nnorma: \"CPC — Lei 13.105/2015 (texto compilado)\"\n"
               f"parte: \"{n['parte']}\"\nartigos: \"{prim} a {ult}\"\nfonte: \"planalto.gov.br — PDF impresso em 12/09/2026\"\n"
               f"gerado_em: {hoje}\n---\n{MARCA}\n\n# CPC · {n['titulo']}\n\n"
               f"Arts. **{prim} a {ult}** · {n['parte']} · voltar a [[CPC-00-Indice]]\n\n"
               "> Só a **redação vigente**: o texto riscado no compilado do Planalto foi retirado. "
               "As anotações *(Redação dada pela Lei…)* ficam, porque dizem desde quando a redação vale. "
               "Citação em peça se confere contra o [PDF original](_original/L13105-compilado.pdf).\n")
        (pasta / f"{n['arquivo']}.md").write_text(cab + "".join(n["corpo"]), encoding="utf-8")

    linhas = [f"---\ntipo: indice-legislacao\nnorma: \"CPC — Lei 13.105/2015\"\ngerado_em: {hoje}\n---\n{MARCA}\n",
              "# CPC — Lei nº 13.105, de 16 de março de 2015\n",
              "Texto **compilado** do Planalto, impresso em 12/09/2026 — já com a Lei 15.484/2026 "
              "(relevância no recurso especial, art. 1.035-A) e a Lei 15.109/2025. "
              f"**{len(mapa_art)} artigos**, em {len(notas)} notas por Livro. "
              "Como citar um artigo em outra nota: `[[CPC-PE-L3-...#Art. 1.023]]` — a tabela abaixo diz o arquivo.\n",
              "Ver também: [[CPC-Guia-do-Escritorio]] (os artigos que o escritório usa todo dia) · [[_PAINEL-LEGISLACAO]]\n",
              "| Livro | Artigos | Nota |", "|---|---|---|"]
    for n in notas:
        linhas.append(f"| {n['parte']} · {n['titulo']} | {n['arts'][0]} a {n['arts'][-1]} | [[{n['arquivo']}]] |")
    (pasta / "CPC-00-Indice.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    return {"notas": notas, "mapa": mapa_art, "riscadas": getattr(_linhas_cpc, "riscadas", 0)}


# ---------------------------------------------------------------------------- MCR

_RE_CAB_SECAO = re.compile(r"CAPÍTULO\s*:\s*(.+?)\s*-\s*(\d+)\s*\n\s*SEÇÃO\s*\n?\s*:\s*(.+?)\s*-\s*(\d+)\s*\n", re.S)
_RE_ATUALIZ = re.compile(r"Atualização MCR nº (\d+), de ([^\n]+?)\s*\n")
_RE_ITEM = re.compile(r"^(\d+(?:-[A-Z])?)\s+-\s+(.*)$")
_RE_SUB = re.compile(r"^([a-z]\)|[IVXL]+\s+-\s)")


_RE_CONSOLIDACAO = re.compile(r"^\s*Resolução CMN nº [\d.]+, de \d{1,2} de \w+ de \d{4}\s*$", re.M)


def _limpar_pagina_mcr(txt: str) -> str:
    txt = _RE_CAB_SECAO.sub("\n", txt)
    # Rodapé de seção consolidada por resolução (instrução 7-a do MCR) — sai do corpo,
    # vai para a linha de versão da seção.
    txt = _RE_CONSOLIDACAO.sub("", txt)
    txt = re.sub(r"_{10,}", "", txt)
    txt = _RE_ATUALIZ.sub("\n", txt)
    txt = re.sub(r"TÍTULO\s*\n\s*:\s*CRÉDITO RURAL\s*\n\s*\d+\s*\n", "\n", txt)
    linhas = [l.rstrip() for l in txt.splitlines()]
    while linhas and not linhas[-1].strip():
        linhas.pop()
    if linhas and re.fullmatch(r"\s*\d+\s*", linhas[-1]):
        linhas.pop()  # número da página
    return "\n".join(linhas)


def _paragrafos_mcr(texto: str) -> list[str]:
    pars: list[str] = []
    for l in texto.splitlines():
        s = re.sub(r"\s+", " ", l).strip()
        if not s:
            continue
        if s == "(*)":
            if pars:
                pars[-1] += " **(\\*)**"
            continue
        if _RE_ITEM.match(s) or _RE_SUB.match(s) or not pars:
            pars.append(s)
        else:
            pars[-1] += " " + s
    return pars


def gerar_mcr(pdf: Path) -> dict:
    doc = fitz.open(pdf)
    pasta = DESTINO / "MCR"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "_original").mkdir(exist_ok=True)
    shutil.copy2(pdf, pasta / "_original" / "MCR-completo.pdf")

    atualiz = sorted({(int(n), d) for n, d in _RE_ATUALIZ.findall("\n".join(p.get_text() for p in doc))})
    ultima = atualiz[-1]

    secoes: dict[tuple, dict] = {}
    preliminar, documentos = [], []
    anomalias, anterior = [], None
    for i, pag in enumerate(doc):
        bruto = pag.get_text()
        m = _RE_CAB_SECAO.search(bruto)
        if m:
            chave = (int(m.group(2)), int(m.group(4)))
            # O próprio PDF do Bacen tem cabeçalho errado (pág. 83 diz Seção 6 sendo a 4-9;
            # págs. 274-275 dizem 11 sendo a 12-12). O manual é ordenado: seção que "volta"
            # dentro do mesmo capítulo é continuação da anterior, não retorno.
            if anterior and chave[0] == anterior[0] and chave[1] < anterior[1]:
                anomalias.append((i + 1, f"{chave[0]}-{chave[1]}", f"{anterior[0]}-{anterior[1]}"))
                chave = anterior
            anterior = chave
            s = secoes.setdefault(chave, {"cap": m.group(1).strip(), "sec": re.sub(r"\s+", " ", m.group(3)).strip(),
                                          "paginas": [], "texto": [], "atualiz": set()})
            s["paginas"].append(i + 1)
            s["texto"].append(_limpar_pagina_mcr(bruto))
            s["atualiz"].update(n for n, _ in _RE_ATUALIZ.findall(bruto))
            s.setdefault("consolid", set()).update(x.strip() for x in _RE_CONSOLIDACAO.findall(bruto))
        elif "MCR - DOCUMENTO" in bruto or i + 1 > 250:
            documentos.append((i + 1, _limpar_pagina_mcr(bruto)))
        else:
            preliminar.append((i + 1, _limpar_pagina_mcr(bruto)))

    hoje = date.today().isoformat()
    caps: dict[int, list] = {}
    for (c, s), dados in sorted(secoes.items()):
        caps.setdefault(c, []).append((s, dados))

    itens_idx = {}
    for c, lista in caps.items():
        nome_cap = lista[0][1]["cap"]
        arquivo = f"MCR-{c:02d}-{_slug(nome_cap, 55)}"
        partes = [f"---\ntipo: legislacao\nnorma: \"Manual de Crédito Rural (MCR) — Bacen\"\ncapitulo: {c}\n"
                  f"atualizacao: \"MCR nº {ultima[0]}, de {ultima[1]}\"\ngerado_em: {hoje}\n---\n{MARCA}\n\n"
                  f"# MCR · Capítulo {c} — {nome_cap}\n\n"
                  f"Voltar a [[MCR-00-Indice]] · Citação: **MCR {c}-seção-item** (ex.: MCR 2-6-4, alínea \"b\").\n\n"
                  "> **(\\*)** marca o item alterado na última atualização daquela seção (instrução 9 do próprio MCR). "
                  "Texto extraído do PDF oficial: citação em peça se confere contra o "
                  "[PDF original](_original/MCR-completo.pdf), na página indicada em cada seção.\n"]
        for s, dados in lista:
            pags = dados["paginas"]
            if dados["atualiz"]:
                versao = f"seção atualizada até o MCR nº {max(dados['atualiz'], key=int)}"
            elif dados.get("consolid"):
                versao = "seção consolidada pela " + " / ".join(sorted(dados["consolid"]))
            else:
                versao = "versão da seção não indicada no rodapé"
            partes.append(f"\n## Seção {s} — {dados['sec']}\n\n"
                          f"*PDF pág. {pags[0]}{'–' + str(pags[-1]) if len(pags) > 1 else ''} · {versao}*\n")
            ultimo = 0.0
            for p in _paragrafos_mcr("\n".join(dados["texto"])):
                mi = _RE_ITEM.match(p)
                if mi:
                    n = mi.group(1)
                    ordem = float(n.split("-")[0]) + (0.5 if "-" in n else 0)
                # Item só vira título se a numeração avança. As tabelas do Cap. 7 numeram
                # linha como "1 - ", "2 - " a cada bloco — sem isto, "MCR 7-6-1" sairia 28 vezes.
                if mi and ordem > ultimo:
                    ultimo = ordem
                    ref = f"MCR {c}-{s}-{mi.group(1)}"
                    itens_idx[ref] = arquivo
                    partes.append(f"\n#### {ref}\n\n{p}\n")
                elif _RE_SUB.match(p):
                    partes.append(f"\n- {p}\n")
                else:
                    partes.append(f"\n{p}\n")
        (pasta / f"{arquivo}.md").write_text("".join(partes), encoding="utf-8")
        caps[c] = (arquivo, nome_cap, lista)

    def _bruto(nome, titulo, paginas):
        corpo = "\n".join(f"\n<!-- PDF pág. {p} -->\n{t}" for p, t in paginas)
        (pasta / f"{nome}.md").write_text(
            f"---\ntipo: legislacao\nnorma: \"MCR — {titulo}\"\ngerado_em: {hoje}\n---\n{MARCA}\n\n# MCR · {titulo}\n\n"
            "Voltar a [[MCR-00-Indice]]. Texto corrido do PDF (tabelas e formulários perdem o alinhamento — "
            "para ler formulário, abrir o [PDF original](_original/MCR-completo.pdf)).\n\n```text\n" + corpo + "\n```\n",
            encoding="utf-8")

    _bruto("MCR-90-Instrucoes-e-Normas", "Instruções, índice e normas codificadas / não codificadas", preliminar)
    _bruto("MCR-91-Documentos", "Documentos (Sicor, Proagro, exigibilidades)", documentos)

    idx = [f"---\ntipo: indice-legislacao\nnorma: \"Manual de Crédito Rural (MCR)\"\n"
           f"atualizacao: \"MCR nº {ultima[0]}, de {ultima[1]}\"\ngerado_em: {hoje}\n---\n{MARCA}\n",
           "# Manual de Crédito Rural (MCR) — Banco Central do Brasil\n",
           f"Versão incorporada: **Atualização MCR nº {ultima[0]}, de {ultima[1]}** "
           f"({len(doc)} páginas, {len(secoes)} seções, {len(itens_idx)} itens numerados). "
           "Citar um item em outra nota: `[[MCR-02-Condicoes-Basicas#MCR 2-6-4]]`.\n",
           "Ver também: [[MCR-Guia-do-Escritorio]] (os itens que as teses usam) · [[_PAINEL-LEGISLACAO]]\n",
           "> O MCR muda várias vezes por ano (Plano Safra, resoluções do CMN). Esta é **uma foto**: "
           "o item citado em peça deve ser o **vigente na data do fato** (contratação, vencimento, pedido de "
           "prorrogação) — e o texto da época pode não ser o desta versão.\n",
           "| Capítulo | Seções | Nota |", "|---|---|---|"]
    for c in sorted(k for k in caps):
        arquivo, nome_cap, lista = caps[c]
        secs = " · ".join(f"{s} {d['sec']}" for s, d in lista)
        idx.append(f"| **{c}** — {nome_cap} | {secs} | [[{arquivo}]] |")
    idx.append("| — | Instruções, índice, normas codificadas e não codificadas | [[MCR-90-Instrucoes-e-Normas]] |")
    idx.append("| — | Documentos 1 a 9 (Sicor, Proagro, exigibilidades) | [[MCR-91-Documentos]] |")
    (pasta / "MCR-00-Indice.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    return {"secoes": len(secoes), "itens": itens_idx, "ultima": ultima, "anomalias": anomalias,
            "caps": {c: caps[c][0] for c in caps}}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("cpc", "mcr"):
        sys.exit(__doc__)
    alvo = Path(sys.argv[2]).expanduser()
    if sys.argv[1] == "cpc":
        r = gerar_cpc(alvo)
        print(f"CPC: {len(r['mapa'])} artigos em {len(r['notas'])} notas · {r['riscadas']} linhas riscadas descartadas")
    else:
        r = gerar_mcr(alvo)
        print(f"MCR nº {r['ultima'][0]}: {r['secoes']} seções, {len(r['itens'])} itens")
        for pag, diz, vale in r["anomalias"]:
            print(f"  cabeçalho errado no PDF: pág. {pag} diz Seção {diz}, tratada como {vale}")
