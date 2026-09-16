# Maldonado Advogados — Central de Automações

Plataforma de automação jurídica do escritório **Maldonado Advogados**
(Dr. Renan Gomes Maldonado de Jesus — OAB/RO 5769 — Porto Velho/RO).
Nicho: dívida rural bancária.

Três frentes de automação — **Controladoria é a prioridade** deste projeto:

| Squad | O que faz | Comando-chave |
|-------|-----------|---------------|
| **Controladoria** (prioridade) | Captura intimações/publicações via DJEN, classifica providência/tese/prazo, cruza com ADVBOX, oferece criar tarefa | `python OPERACIONAL/main.py triagem --dias 7` |
| **Dívida Rural** | Produção de peça (prorrogação, descaracterização de mora, revisional) — via agente Claude, calibrado pelos 3 modelos reais do escritório | agente `.claude/agents/maldonado-divida-rural.md` |
| **Comercial/Intake** | Lead qualificado no Atende Direito vira cliente + processo no ADVBOX, com pasta no Drive | `python OPERACIONAL/main.py intake --dias 7` |
| **Google Drive** | Estrutura ZEUS do escritorio: localiza/cria a pasta do cliente ([LETRA] > cliente > 4 subpastas) e envia peca/documento pra la | `python OPERACIONAL/main.py drive testar` |
| **Jurimetria** | "Cérebro" do escritório: prognóstico por tese/tribunal, banco de teses (vault Obsidian) | agente `.claude/agents/maldonado-jurimetria.md` |

## Baixar o sistema

Repositório: `https://github.com/<organizacao>/<repositorio>`

```bash
git clone https://github.com/<organizacao>/<repositorio>.git
cd <repositorio>
```

Sem Git instalado? Baixe o ZIP direto em **Code → Download ZIP** na página do repositório acima
e descompacte numa pasta — funciona igual, só não recebe atualizações automáticas depois.

## Instalação rápida

O escritório tem máquinas **Windows e Mac** — use o instalador do seu sistema (ambos fazem a
mesma coisa: criam o ambiente, instalam as dependências e preparam o `config/.env`):

**Windows** — dê duplo clique em `deploy\instalar_windows.bat` (ou rode no terminal):
```bat
deploy\instalar_windows.bat
```

**Mac:**
```bash
chmod +x deploy/instalar_mac.sh
./deploy/instalar_mac.sh
```

### Passo a passo manual (se preferir não usar o instalador)

**Windows (cmd/PowerShell):**
```bat
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
copy config\.env.example config\.env
```

**Mac/Linux (bash/zsh):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env
```

**Depois, nos dois sistemas:**
1. Edite `config/.env` — preencha `ADVBOX_API_TOKEN` e `DJEN_OAB_LISTA` (e, para o intake,
   `ATENDE_DIREITO_BASE_URL` / `ATENDE_DIREITO_API_TOKEN`).
2. Edite `config/equipe.py` — preencha os IDs de usuário do ADVBOX.
3. Teste (só leitura, não cria nada):
   ```
   python OPERACIONAL/main.py triagem --dias 7
   ```

> **Antes de rodar em produção, leia `docs/ONBOARDING.md`** — checklist passo a passo de
> credenciais. As automações rodam de forma segura enquanto algo não estiver configurado
> (nada é criado/alterado sem credencial e sem confirmação manual).

## Estrutura
Ver `CLAUDE.md` para a árvore completa e as regras de cada squad.

## Regra de ouro
A IA **nunca protocola** e **nunca cria/move tarefa sem confirmação explícita**. Toda peça e
toda triagem terminam prontas para revisão da Dra. Juliana / do Dr. Renan.

## Segurança
- Segredos ficam **somente** em `config/.env` (nunca versionado — ver `.gitignore`).
- Nenhuma credencial vem pré-preenchida neste repositório.

---

> **Cópia pública.** Esta é uma versão anonimizada do sistema interno do escritório. Nomes de
> clientes, números de processo de clientes, relatórios de KPI, notas técnicas, avaliações internas
> e materiais de terceiros (metodologias e coletâneas licenciadas) foram retirados ou substituídos
> por identificadores fictícios (`0000000-00.0000.0.00.0000`, "Cliente A"). Nenhuma credencial
> acompanha o código: tudo vem de `config/.env` (ver `config/.env.example`).
