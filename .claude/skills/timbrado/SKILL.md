---
name: timbrado
description: Papel timbrado oficial do Maldonado Advogados e o padrão de formatação de peça do escritório. Use SEMPRE que for gerar qualquer peça, petição, ofício ou minuta em .docx para o escritório — carrega o timbrado correto (faixa 2026), as margens, a fonte e as regras de título/jurisprudência já confirmadas pela Dra. Juliana.
---

# Timbrado e formatação de peça — Maldonado Advogados

## Regra

Toda peça sai sobre `DOCS_MODELOS/timbrado_modelo.docx`. **Nunca** montar peça a partir de
documento em branco, nem a partir de arquivo antigo do Drive com "timbrado" no nome — o Drive
tem 44 desses, quase todos obsoletos.

```python
from docx import Document
doc = Document('DOCS_MODELOS/timbrado_modelo.docx')   # já vem com faixa, margens e fonte
```

O modelo já traz cabeçalho, margens, fonte e entrelinha corretos. O corpo vem vazio: é só
escrever. Se precisar reaproveitar outro `.docx` como base, apague os parágrafos do corpo
(`p._element.getparent().remove(p._element)`) — nunca o cabeçalho.

## Faixa do timbrado (versão 2026)

A faixa é montada por `OPERACIONAL/gerar_timbrado.py` a partir de duas peças de arte e de
**uma lista de dados**:

- `assets/timbrado-2026-friso.png` (1682×76) — friso preto/dourado, largura total;
- `assets/timbrado-2026-logo-recortada.png` (720×278) — a logo MALDONADO ADVOGADOS, à esquerda
  (a `timbrado-2026-logo.png` original sem o branco à direita, que tomava 4,6 cm da faixa);
- o quadro de advogados, **em texto**, lido de `config/equipe.py` → `ADVOGADOS_TIMBRADO`.

A arte vem da peça real `0000024-31.2026.8.22.0001 - Cliente AF x Sicoob - Apelação V6`,
protocolada em **08/09/2026**. O que mudou desde então é só o quadro de nomes, que deixou de ser
imagem: no `.jpeg` original (`assets/timbrado-maldonado-2026.jpeg`, mantido como referência) ele
estava rasterizado, e por isso incluir advogado exigia editar imagem — em 8 nomes a arte já não
comportava mais ninguém. Em texto, incluir advogado é uma linha de dado, e nome e OAB ficam
pesquisáveis e copiáveis no PJe.

Quadro de advogados que consta da faixa (**11 nomes**, atualizado em 16/09/2026). Na faixa sai
**o Dr. Renan primeiro e os demais em ordem alfabética** (a ordem é aplicada pelo gerador, não pela
lista), em **uma coluna** alinhada à direita, Arial 9 pt, preto e negrito. Para a letra caber, o
**cabeçalho cresceu** (Dra. Juliana, 16/09/2026; duas colunas foram testadas e recusadas):

| Advogado(a) | OAB |
|---|---|
| Renan Maldonado | OAB/RO 5.769 |
| Eliane Miranda | OAB/RO 7.904 |
| Arilson Cruz Lopes | OAB/RO 9.982 |
| Bruno Vinícius | OAB/RO 13.021 |
| Felipe Souza | OAB/RJ 244.309 |
| Mailson Monteiro | OAB/RO 14.501 |
| Matheus Ramos | OAB/RJ 262.255 |
| Taynara Scatolin | OAB/MT 30.109 |
| Heloisa Antunes | OAB/DF 76.621 |
| Agenor Rufino | OAB/PE 62.751 |
| Ana Sheila Garcez | OAB/RO 16.126 |

> **A OAB do Dr. Agenor é de Pernambuco**, não de Rondônia (conferida em 19 publicações do
> DJEN). Supor "OAB/RO" pelo escritório ser de Porto Velho põe número de outro advogado no papel.

Fora do quadro, por decisão da GJ: **Bruna Vicente** (OAB/TO 9.013), retirada em 11/09/2026 —
sair do timbrado não a tira dos processos em que é advogada constituída; e **Josué Kalebe**,
que entra quando a GJ confirmar a OAB (`ADVOGADOS_SEM_OAB`). A **Dra. Ana Sheila** entrou em
16/09/2026 com a OAB/RO 16.126 informada pela GJ (ainda sem publicação no DJEN). **OAB nunca é
preenchida por suposição.**

> **Carlos Oliveira (OAB/RO 7.486) NÃO consta mais.** O timbrado antigo
> (`Timbrado - nova logo.docx`, 2024, no Drive) ainda o lista e não tem cinco dos advogados
> acima — **está obsoleto, não usar.** Isso resolve a divergência que estava aberta em
> `BASE_CONHECIMENTO/05 - FORMATACAO/Timbrado-Oficial.md`.

### Incluir ou tirar advogado da faixa

Editar `config/equipe.py` → `ADVOGADOS_TIMBRADO` e rodar:

```
python OPERACIONAL/gerar_timbrado.py       # regera DOCS_MODELOS/timbrado_modelo.docx
```

O mesmo comando regera o **modelo para os advogados**
(`DOCS_MODELOS/TIMBRADO MALDONADO ADVOGADOS 2026.docx` e `.dotx`): a mesma faixa, com as regras
desta skill como estilos do Word ("Maldonado Título", "Maldonado Jurisprudência", "Maldonado
Assinatura"...) e um esqueleto de peça com os campos em amarelo. É o arquivo que se distribui à
equipe; o `timbrado_modelo.docx` continua sendo a folha em branco da automação.

O `.docx` é **artefato**: não editar à mão. Depois de regerar o timbrado, regerar também os dois
modelos de peça, que o embutem:

```
python OPERACIONAL/gerar_modelo_declaratoria.py
python OPERACIONAL/gerar_modelo_alongamento.py
```

**A margem superior é calculada para 12 nomes** (`CAPACIDADE_QUADRO`), não para os de hoje:
com 11 pt de entrelinha o quadro reservado tem 4,66 cm, e incluir advogado até o 12º não desloca
uma linha do corpo. O 13º exige subir a capacidade, e a margem acompanha sozinha.
`gerar_timbrado.py` **falha com erro** em vez de estourar em silêncio — o estouro só apareceria
no protocolo, e empurraria o corpo de toda peça para baixo.

## Geometria (medida na peça real, não inventada)

| Item | Valor |
|---|---|
| Página | A4 — 21,0 × 29,7 cm |
| Faixa do timbrado | começa em y **1,27 cm**, largura **20,83 cm** (borda a borda); friso 0,94 cm + quadro de nomes |
| Margem superior (início do corpo) | **7,37 cm** desde 16/09/2026 (era 5,33 cm, a medida da peça de 08/09/2026, quando a faixa acabava na logo) |
| Margem esquerda | **2,54 cm** |
| Margem direita | **2,44 cm** |
| Margem inferior | **2,5 cm** |
| Rodapé | **vazio** — a peça real não tem rodapé |

A faixa fica no cabeçalho com **recuo negativo** igual às margens (`left_indent = -2.54 cm`,
`right_indent = -2.44 cm`). Sem isso ela é confinada à área entre margens e sai estreita e
descentralizada — foi exatamente esse o erro do timbrado antigo.

## Formatação do corpo

- **Arial Narrow 12 pt** — confirmado na peça real de 08/09/2026. (O vault registrava duas
  famílias convivendo, Times New Roman e Arial Narrow; a produção atual é Arial Narrow.)
- **Justificado**, entrelinha **1,5**.
- **Centralizado** só em: título da ação, endereçamento e bloco de assinatura.
- Citações e tabelas em **10 pt**, entrelinha 1,15.

### Regras confirmadas pela Dra. Juliana (08/09/2026)

1. **TÍTULOS em negrito**, caixa alta, na margem esquerda, numerados em romano (I, II, III…).
2. **Jurisprudência com recuo à direita e em itálico** — bloco deslocado ~4 cm além da margem
   do corpo, texto todo em itálico, 10 pt; a identificação da fonte ("STJ, Súmula 297")
   centralizada, em **negrito + itálico**.

### Regra confirmada pelo Dr. Renan / Dra. Juliana (14/09/2026)

3. **Sem travessão (— ou –) na peça.** O excesso de travessões denuncia texto gerado por IA e
   tira credibilidade da petição. Vale para corpo, títulos, legendas, quadros e identificação de
   fonte. Trocar por vírgula, dois-pontos, parênteses ou frase nova. Hífen de palavra composta e
   de número de processo segue normal. Antes de entregar, a contagem de "—" e "–" no documento
   tem de ser **zero**.

### Quadro de identificação do processo (opcional)

As peças recentes abrem com uma tabela de 2 colunas, cabeçalho em fundo âmbar/laranja, com
`Processo n.` / `Apelante` / `Apelado` (ou equivalente). Útil em recurso; dispensável em
petição simples.

### Assinatura

```
[NOME EM CAIXA ALTA — com "MALDONADO" e o sobrenome principal sublinhados]
OAB/RO [número]
```

Centralizado. As peças reais trazem **dois** advogados assinando (o Dr. Renan e o advogado que
produziu).

Segundos subscritores já conferidos (nome forense e OAB tirados das publicações do DJEN):

| Advogado(a) | Nome na assinatura | OAB | Na faixa do timbrado? |
|---|---|---|---|
| Dra. Taynara Scatolin (ADVBOX 288544) | TAYNARA SCATOLIN GONÇALVES DA SILVA | OAB/MT 30.109/O | **Sim**, desde 11/09/2026 |
| Dra. Heloisa Antunes (ADVBOX 288554) | HELOISA GARCIA ANTUNES | OAB/DF 76.621 | **Sim**, desde 11/09/2026 |
| Dr. Agenor (ADVBOX 262240) | AGENOR RUFINO DE MELO NETO | OAB/PE 62.751 (não é OAB/RO; conferido em 19 publicações do DJEN, 15/09/2026) | **Sim**, desde 15/09/2026 |

O **nome na assinatura é o nome forense completo**, que é mais longo que o da faixa (a faixa
abrevia, por espaço): na faixa lê-se "Taynara Scatolin", na assinatura "TAYNARA SCATOLIN
GONÇALVES DA SILVA". A OAB é a mesma nos dois lugares.

Na dúvida sobre o segundo nome, assine só com o **Dr. Renan Gomes Maldonado de Jesus,
OAB/RO 5769**, e sinalize a pendência.

## Nome do arquivo entregue

```
[NOME DO CLIENTE] - [AÇÃO] - PRONTA PARA REVISÃO.docx
```

## Guard-rail

Peça gerada sai **sempre pronta para revisão**, nunca protocolada. Trechos que dependem de
documento que você não leu (petição inicial, contrato, laudo) vão como placeholder
**destacado em amarelo** (`WD_COLOR_INDEX.YELLOW`) — nunca preenchidos por suposição.
