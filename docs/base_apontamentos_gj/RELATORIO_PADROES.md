# O que a Gerência Jurídica devolve nas peças — jun/jul/ago 2026

> Levantamento pedido pela **Dra. Juliana Ferreira Gusmão de Lara** em 10/09/2026.
> Fonte: ADVBOX (somente leitura). Período: 01/06/2026 a 31/08/2026.
> Reproduzir: `python OPERACIONAL/main.py apontamentos --de 2026-06-01 --ate 2026-08-31 --csv base.csv`

---

## 1. O volume que passa pela Gerência Jurídica

Tarefas **CONFERIR/REVISAR PETIÇÃO** (tag `2596525`) concluídas no período:

| Mês | Tarefas concluídas na tag | Concluídas **pela Dra. Juliana** |
|---|---:|---:|
| Junho | 226 | 10 |
| Julho | 415 | 178 |
| Agosto | 411 | 201 |

O salto de junho para julho não é sazonalidade: é a **entrada da Gerência Jurídica no fluxo
de revisão prévia**. Em junho a tag existia, mas a peça não passava sistematicamente pela GJ.
De julho em diante, ~190 peças/mês são submetidas a uma única pessoa antes do protocolo.

**Esse é o gargalo real.** Não é o volume de peças — é o volume de peças que só ficam prontas
depois que uma pessoa lê cada uma e escreve o que corrigir.

---

## 2. Como a devolutiva foi localizada (e por que não era óbvio)

O `GET /posts` da ADVBOX devolve o texto da tarefa, mas **não devolve quem escreveu** — só os
convidados. E dentro da tag CONFERIR/REVISAR PETIÇÃO o texto é sempre do **advogado submetendo**
("Submeto à análise da Gerência Jurídica..."): das 238 tarefas dessa tag cuja autoria foi
possível conferir, **nenhuma** foi escrita pela Dra. Juliana.

O retorno dela está em **outros registros**, e o único endpoint que expõe o autor é
`GET /history/{lawsuit_id}`. Foram lidos os históricos dos **380 processos** que tiveram peça
submetida no período. As devolutivas da GJ saem espalhadas por seis tags:

| Tag usada na devolutiva | Devolutivas |
|---|---:|
| AGENDAMENTO | 44 |
| COMENTÁRIO | 39 |
| PEÇA ENVIADA PARA AJUSTES | 20 |
| ANÁLISE - NÍVEL 01 | 11 |
| PRESTAR ESCLARECIMENTOS | 7 |
| PEÇA APROVADA PARA PROTOCOLO | 6 |

A tag que *deveria* concentrar o retorno — `PEÇA ENVIADA PARA AJUSTES` — responde por **16%**.
Quem quiser auditar a devolutiva olhando só essa tag enxerga um sexto do trabalho da GJ.

**Total: 125 devolutivas com conteúdo técnico → 291 apontamentos sobre a peça.**

### Limite conhecido deste levantamento

`GET /history` devolve **no máximo ~20 itens por processo e não pagina** (testados `limit`,
`offset`, `page`, `skip`, `start`, `per_page`, `date_start` — todos ignorados, conferido em
10/09/2026). Em processo muito movimentado, os registros mais antigos ficam fora do alcance.

Consequência prática: **junho está subestimado** (24 apontamentos) e julho/agosto estão
razoavelmente cobertos. Os números abaixo são **piso, não total** — nunca leia um mês baixo
como "não houve apontamento".

---

## 3. Ranking — o que a Gerência Jurídica mais corrige

### Por família

| # | Família | Apontamentos | Peso |
|---|---|---:|---:|
| 1 | **Fundamentação** | 57 | 27% |
| 2 | **Tese e enquadramento** | 55 | 26% |
| 3 | **Prova e documentos** | 40 | 19% |
| 4 | **Pedidos** | 27 | 13% |
| 5 | **Fatos e dados do caso** | 22 | 10% |
| 6 | **Forma e estratégia** | 6 | 3% |
| 7 | **Entrega/projeto ao cliente** | 5 | 2% |

*(79 apontamentos ficaram como "revisar manualmente" — a classificação é heurística de
palavra-chave, palpite e não laudo. É nesse conjunto que costuma estar o apontamento com redação
nova, que merece virar categoria.)*

### Por categoria — os 10 primeiros

| # | Categoria | Nº | Exemplo real da devolutiva |
|---|---|---:|---|
| 1 | **Dispositivo legal-chave ausente** | 29 | *"o item 7.2 argumenta bem narrativamente que a queda da arroba não é risco ordinário, mas nunca ancora isso nos arts. 317 e 478, CC"* |
| 2 | **Tese/argumento cabível não explorado** | 29 | *"o Banco declarou nada mais ter a produzir... A peça não usa esse fato. Isso é munição direta para o art. 341, CPC"* |
| 3 | **Fatos incontroversos / ônus da prova não trabalhados** | 22 | *"Inserir seção autônoma 'Dos Fatos Incontroversos' — listar um a um os fatos não impugnados especificamente pelo Banco"* |
| 4 | **Tese principal mal hierarquizada** | 13 | *"a petição está inteiramente focada na Tutela de Urgência... sugiro reestruturar para ter a Tutela de Evidência como tese principal"* |
| 5 | **Pedido genérico** | 11 | *"a tutela de urgência está genérica, individualizar o perigo de dano e probabilidade do direito ao caso concreto"* |
| 6 | **Pedido da inicial não enfrentado / tópico faltante** | 11 | *"Decisão-surpresa — ausente, precisa de subitem próprio"* |
| 7 | **Precedente local/interno não citado** | 10 | *"A minuta não cita, em nenhum ponto, a sentença do processo 0000000-00.0000.0.00.0000... é o precedente mais forte disponível"* |
| 8 | **Documento essencial ausente** | 10 | *"Acionar com urgência o setor de documentos... qualquer registro informal do pedido de alongamento — um único documento desses pesa mais que horas de depoimento"* |
| 9 | **Erro factual (ID, número, data, valor)** | 8 | *"a manifestação menciona 'decisão de ID [X]', mas nos autos do agravo a decisão consta como ID [Y]"* |
| 10 | **Contradição interna: moldura × pedido** | 8 | *"a Seção 1 declara que a ação 'não é revisional' e que 'não se pede recálculo', mas o pedido de mérito pede exatamente recálculo"* |

---

## 4. Os cinco pontos de maior impacto (leitura qualitativa)

O ranking por frequência não é o mesmo que o ranking por gravidade. Na leitura das 125 devolutivas,
cinco padrões aparecem repetidamente **e custam caro quando passam**:

**1. Contradição entre a moldura declaratória e o pedido.**
A peça declara "não é revisional / não se pede recálculo" e depois pede recálculo, excesso de
execução e restituição. Não é erro de redação: entrega ao banco o argumento de que a ação é
revisional disfarçada, e o Tema 28 tem tratamento distinto para cada moldura.

**2. Pedir perícia onde a matéria é documental.**
Erro metodológico do escritório, não do advogado isolado. A tese central da descaracterização
de mora é **confronto documental** (Quadro Resumo × ficha gráfica). Pedir perícia sobre a
capitalização faz duas coisas ruins, nas palavras da própria devolutiva: *"(i) admite
implicitamente que a matéria não é só documental, o que fecha a porta para tutela de evidência
(art. 311, II exige prova comprovável apenas documentalmente); (ii) atrasa desnecessariamente
o que poderia ser resolvido agora."*

**3. Fato incontroverso tratado como fato a provar.**
Quando o banco não impugna especificamente, o fato está provado (art. 341, CPC) — e a peça
continua pedindo prova dele. A GJ resume a diferença: *"é a diferença entre dizer 'a CEF não
rebateu, logo precisamos de prova' e dizer 'a CEF não rebateu, logo o fato já está provado —
pode julgar'. A segunda linha é mais forte e mais rápida para o cliente."*

**4. Erro factual em ID, data ou número de operação.**
Aparece em 8 devolutivas: ID de decisão trocado, data de publicação que torna a tempestividade
logicamente impossível, numeração de cédula divergente dentro da mesma peça. É o erro mais
barato de evitar e o que destrói credibilidade mais rápido perante o juízo.

**5. Tese que não resiste à premissa contrária.**
A peça argumenta "a fonte do recurso não foi esclarecida" — e cai se a Câmara aceitar a premissa
da sentença. A orientação da GJ: *"precisa liderar com a tese que resiste mesmo que a Câmara
aceite que são recursos próprios."*

---

## 5. Distribuição pela equipe

A contagem por advogado foi feita no levantamento interno e **não é reproduzida aqui**: não é
ranking de qualidade (quem produz mais peça recebe mais devolutiva, e a devolutiva longa da GJ
costuma ser sinal de caso complexo, não de peça ruim), e o tom do manual é preventivo, sem
contagem por pessoa.

Leitura útil, em termos agregados: as devolutivas se distribuem por vários destinatários, e os dois
padrões dominantes se repetem entre advogados diferentes (**dispositivo legal-chave ausente** e
**fatos incontroversos não trabalhados**). Erro que atravessa a equipe inteira é erro de **método**,
não de pessoa — corrige-se no modelo de peça e no checklist, não em devolutiva individual.

---

## 6. O que ficou de fora da base de peça

Além dos 291 apontamentos sobre a peça, a Dra. Juliana escreveu **53 cobranças de fluxo** no
mesmo período, nos mesmos registros:

- despacho com o magistrado não agendado após o protocolo (7);
- tag/KPI lançada errada ou não lançada (6);
- prazo D-3 descumprido / perda de prazo (3);
- habilitação, procuração ou contrato não juntado (2);
- gestão: financeiro, sucesso do cliente, rescisão, premiação (27);
- orientação de conduta (sustentação oral não pode ser dispensada sem alinhamento com a GJ).

Está na base marcado como `FLUXO/CONTROLADORIA`, fora do ranking de peça. É volume real da
Gerência Jurídica e merece tratamento próprio — mas não é erro de peça e não entra no checklist
do advogado.

---

## 7. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `base_apontamentos_gj_2026-06_a_2026-08.csv` | 374 linhas — uma por (apontamento × categoria). **Não publicado** (contém dado de cliente e processo) |
| `devolutivas_gj_2026-06_a_2026-08.csv` | 125 linhas — uma por devolutiva. **Não publicado** (mesmo motivo) |
| `CHECKLIST_AUTORREVISAO.md` | O checklist que sai deste levantamento |
| `OPERACIONAL/apontamentos_gj.py` | Coleta + classificação, reproduzível mês a mês |
