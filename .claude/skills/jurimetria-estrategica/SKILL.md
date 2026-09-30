---
name: jurimetria-estrategica
description: Usa a base de julgados do DJEN (jurimetria) para construir a peça pensando no foro e no STJ. Use SEMPRE antes de redigir mandamental, cautelar, inicial, contestação de embargos ou recurso em dívida rural (alongamento, descaracterização da mora, mora c/c assistência técnica, revisional). Traz o que a vara de origem já decidiu na tese, o que mais derruba a tese naquele tribunal (para neutralizar com prova), os acórdãos favoráveis e contrários mais recentes, e os óbices que barram o REsp no STJ (Súmula 7, 5, 211, 283/284) para a inicial já nascer prequestionada. Entra junto com a skill da tese e com `timbrado`/`inicial-anexos`, nunca no lugar delas.
---

# Jurimetria estratégica — a peça construída para o foro e para o STJ

## Regra

Toda peça de dívida rural do escritório é redigida **depois** do briefing de jurimetria do foro
e da tese. O objetivo é aumentar a chance de êxito com dado real: o que aquele juízo e aquele
tribunal já decidiram, por que a tese costuma cair ali e o que impede o caso de chegar ao STJ.

```
python OPERACIONAL/main.py jurimetria --tese alongamento --comarca Ariquemes --md
python OPERACIONAL/main.py jurimetria --tese mora --processo 7001234-56.2026.8.22.0002 --md   # comarca pelo nº CNJ
python OPERACIONAL/main.py jurimetria --tese alongamento --comarca "Porto Velho" --peca recurso
python OPERACIONAL/main.py jurimetria --tese mora-assistencia --tribunal TRF1 --comarca "Porto Velho"
```

Teses: `alongamento`, `mora`, `mora-assistencia`, `revisional` (as mesmas de `inicial-anexos`).
**A tese vem da advogada ou do agente da tese, nunca do briefing.** Ambígua, para e pergunta.

## Como cada parte do briefing entra na peça

| Seção do briefing | O que fazer na peça |
|---|---|
| **1. Juízo de origem** — taxa da vara, juízes, decisões favoráveis da própria vara | Decisão favorável do **mesmo juízo** em caso análogo é o precedente mais persuasivo que existe: abrir o inteiro teor, conferir que o caso é mesmo análogo e citar com número do processo. Vara com taxa baixa em liminar → reforçar o perigo de dano concreto e considerar cautelar antecedente. |
| **2. O que derruba a tese** — sinais com diferença positiva entre derrotas e vitórias | Cada sinal vira **prova na inicial**, não parágrafo de argumento. "Laudo unilateral" → laudo com ART, visita técnica e dados de terceiros (Emater, clima, preço). "Dilação probatória" → documento que dispense instrução para a tutela. "Sem pedido prévio" → requerimento protocolado, ou a tese da desnecessidade (skill `alongamento-divida-rural`). "Recursos de fundo (FNO)" → enfrentar a regra do fundo desde a inicial. |
| **3. Segundo grau** — gabinetes, acórdãos favoráveis e contrários recentes | Citar os favoráveis **conferidos no inteiro teor** (ementário em `07 - JURIMETRIA/EMENTARIO/`). Os contrários recentes são os que o juiz vai usar: a peça faz a **distinção antes**. A distribuição no 2º grau é livre: não escrever para um gabinete específico. |
| **4. STJ** — óbices mais frequentes e checklist | A inicial já nasce pronta para o REsp: dispositivos de **lei federal** nomeados (a Súmula 298 sozinha não abre REsp), fato decisivo **provado por documento** (Súmula 7), todos os fundamentos autônomos enfrentados (Súmula 283), pedido de manifestação expressa e ED se a decisão silenciar (arts. 1.022 e 1.025). |

## Guard-rails (inegociáveis)

1. **Perfil de juiz nunca entra na peça.** Nada de "este juízo costuma indeferir". Na peça entram
   prova, fundamento e precedente. O briefing é bastidor.
2. **Precedente só com inteiro teor conferido.** A base é leitura automática do DJEN (acerto de
   ~95% na amostra de 17/09/2026, não 100%). Ementa transcrita numa decisão do STJ pode ser do TJ
   de origem: nunca citar como STJ.
3. **Taxa com menos de 10 atos não é tendência.** O briefing marca "amostra insuficiente"; não
   transformar em argumento nem em prognóstico com casas decimais.
4. **Jurimetria não é métrica do escritório.** A base lê decisões de todas as partes; o KPI dos
   nossos casos fica em `01 - MAGISTRADOS` e `docs/kpi_exito/`. Não misturar números.
5. **Peça nunca traz fato desfavorável** (regra do escritório), nem para rebater: a distinção dos
   acórdãos contrários é feita pela tese e pela prova do nosso caso, sem narrar o ponto fraco.
6. **Não escolhe juiz nem direciona distribuição.** Comarca com várias varas: a peça tem de
   funcionar em todas.

## Base e cobertura

- Base: `_trabalho/jurisprudencia/base_julgados.sqlite` (`python OPERACIONAL/main.py base status`).
- Tribunais coletados: TJRO (set/2024 a set/2026), TRF1 (2º grau inteiro + varas de Rondônia), STJ
  quando coletado. Tribunal fora da base: o briefing avisa, e a busca ao vivo continua disponível
  (`python OPERACIONAL/main.py jurisprudencia "termo" --tribunal TJMT`).
- O DJEN só tem volume a partir de 2024: precedente anterior vem de `jurisprudencia-rural` e dos
  precedentes da skill da tese.
- Atualizar antes de peça importante: `python OPERACIONAL/main.py base coletar` (incremental).
