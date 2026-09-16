"""
=============================================================================
  MARKDOWN -> PDF - Maldonado Advogados
=============================================================================

  Converte os relatorios internos do projeto (.md) em PDF apresentavel, para
  circular no escritorio sem depender de quem tem editor de Markdown.

  Nao usa o timbrado de peca: isto e' documento interno de gestao, nao peticao.
  Peca continua saindo pela skill `timbrado` (DOCS_MODELOS/timbrado_modelo.docx).

  Motor: Google Chrome em modo headless (--print-to-pdf). Escolhido porque ja
  esta instalado no Mac do escritorio - pandoc, wkhtmltopdf e weasyprint nao
  estao, e cada um deles puxaria LaTeX ou GTK.

  Uso:
      python OPERACIONAL/md_para_pdf.py docs/base_apontamentos_gj/*.md
      python OPERACIONAL/md_para_pdf.py arquivo.md --saida pasta/
=============================================================================
"""
import os
import re
import sys
import shutil
import argparse
import subprocess
import tempfile
from datetime import datetime

try:
    import markdown
except ImportError:  # pragma: no cover
    print('ERRO: falta a biblioteca markdown. Rode:  pip install markdown')
    sys.exit(1)


CHROME_CAMINHOS = (
    # macOS (Mac do escritorio)
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    # Linux (VPS Hostinger) - o pacote `chromium` do Debian/Ubuntu instala em
    # /usr/bin/chromium; o Chrome oficial, em /usr/bin/google-chrome-stable.
    # Sem um destes, `kpi --pdf` falha no servidor (o .md sai, o .pdf nao).
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
    'google-chrome-stable', 'google-chrome', 'chromium-browser', 'chromium', 'chrome',
)

ESCRITORIO = os.getenv('ESCRITORIO_NOME', 'Maldonado Advogados')

# Identidade sobria: documento de gestao interna, leitura em tela e impressao.
# Tabela com cabecalho em fundo escuro e zebra clara - a base tem muita tabela
# de ranking e sem zebra a leitura em A4 se perde.
CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 10.5pt; line-height: 1.55; color: #1a1a1a; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.cabecalho {
  border-bottom: 2.5pt solid #7a1f2b; padding-bottom: 7pt; margin-bottom: 20pt;
  display: flex; justify-content: space-between; align-items: baseline;
}
.cabecalho .escritorio {
  font-size: 12pt; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: #7a1f2b;
}
.cabecalho .meta { font-size: 8pt; color: #6b6b6b; text-align: right; }

h1 {
  font-size: 17pt; line-height: 1.25; margin: 0 0 4pt; color: #111;
  font-weight: 700; letter-spacing: -.01em;
}
h2 {
  font-size: 12.5pt; margin: 22pt 0 7pt; padding-bottom: 4pt; color: #7a1f2b;
  border-bottom: .75pt solid #ddd; font-weight: 700;
  page-break-after: avoid; break-after: avoid;
}
h3 { font-size: 10.5pt; margin: 14pt 0 5pt; font-weight: 700;
     page-break-after: avoid; break-after: avoid; }
p { margin: 0 0 8pt; text-align: justify; }
a { color: #7a1f2b; text-decoration: none; }
strong { font-weight: 700; }
em { color: #444; }

blockquote {
  margin: 12pt 0; padding: 8pt 12pt; background: #f6f4f2;
  border-left: 3pt solid #c9a227; font-size: 9.5pt; color: #3a3a3a;
}
blockquote p { margin: 0 0 5pt; }
blockquote p:last-child { margin: 0; }

/* Tabela longa PODE quebrar entre paginas - o que nao pode partir e' a linha.
   Sem isso, uma tabela de 10 linhas empurra a pagina inteira e deixa meia folha em branco. */
table {
  border-collapse: collapse; width: 100%; margin: 10pt 0 14pt; font-size: 9pt;
}
tr { page-break-inside: avoid; break-inside: avoid; }
thead { display: table-header-group; }
th {
  background: #7a1f2b; color: #fff; text-align: left; font-weight: 600;
  padding: 5pt 7pt; border: .5pt solid #7a1f2b;
}
td { padding: 5pt 7pt; border: .5pt solid #d8d8d8; vertical-align: top; }
tr:nth-child(even) td { background: #faf9f8; }

ul, ol { margin: 0 0 9pt; padding-left: 17pt; }
li { margin-bottom: 4pt; text-align: justify; }

/* Checklist: o "- [ ]" do Markdown vira caixa de verdade, para imprimir e usar */
li.tarefa { list-style: none; margin-left: -14pt; padding-left: 17pt;
            position: relative; page-break-inside: avoid; break-inside: avoid; }
li.tarefa::before {
  content: ""; position: absolute; left: 0; top: 2.5pt;
  width: 8.5pt; height: 8.5pt; border: .9pt solid #7a1f2b; border-radius: 1.5pt;
}

code {
  font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 8.5pt;
  background: #f1efed; padding: 1pt 3.5pt; border-radius: 2pt; color: #7a1f2b;
}
pre {
  background: #f6f4f2; border-left: 2.5pt solid #c9a227; padding: 8pt 10pt;
  font-size: 8.5pt; overflow-x: auto; page-break-inside: avoid; break-inside: avoid;
}
pre code { background: none; padding: 0; color: #1a1a1a; }

hr { border: none; border-top: .5pt solid #ddd; margin: 18pt 0; }

.rodape {
  margin-top: 26pt; padding-top: 7pt; border-top: .5pt solid #ddd;
  font-size: 7.5pt; color: #8a8a8a; text-align: center;
}
"""


# Estilo alternativo: NOTA TECNICA juridica.
# A skill `descaracterizacao-mora` (secao 10bis) exige que a nota tecnica saia com os
# mesmos marcadores visuais da peca, para haver identidade entre os dois documentos:
# cabecalho de secao em laranja (#f6b26b), cabecalho de tabela em azul (#2e5d9c) e
# citacao favoravel em verde (#e2efda). Entra como sobrecarga do CSS base, nao como
# folha separada, para o documento de gestao continuar saindo no bordo do escritorio.
CSS_NOTA_TECNICA = """
.cabecalho { border-bottom-color: #2e5d9c; }
.cabecalho .escritorio { color: #2e5d9c; }
h2 {
  background: #f6b26b; color: #1a1a1a; border-bottom: none;
  padding: 5pt 8pt; margin: 20pt 0 9pt; border-radius: 2pt;
}
h3 { color: #2e5d9c; }
a, code { color: #2e5d9c; }
th { background: #2e5d9c; border-color: #2e5d9c; }
blockquote { background: #ffe6e6; border-left-color: #c00000; color: #3a3a3a; }
pre { border-left-color: #2e5d9c; }
li.tarefa::before { border-color: #2e5d9c; }
"""

ESTILOS = {'gestao': '', 'nota-tecnica': CSS_NOTA_TECNICA}


def _achar_chrome():
    for caminho in CHROME_CAMINHOS:
        if os.path.isfile(caminho):
            return caminho
        achado = shutil.which(caminho)
        if achado:
            return achado
    return None


def _titulo(md_texto, fallback):
    for linha in md_texto.split('\n'):
        if linha.startswith('# '):
            return linha[2:].strip()
    return fallback


def md_para_html(md_texto, titulo, estilo='gestao'):
    """Markdown -> HTML completo e autocontido (o Chrome imprime o arquivo local)."""
    # "- [ ] item" nao e' sintaxe do markdown padrao: marca antes, estiliza depois.
    md_texto = re.sub(r'(?m)^(\s*)-\s\[\s\]\s+', r'\1- @@TAREFA@@', md_texto)
    md_texto = re.sub(r'(?m)^(\s*)-\s\[[xX]\]\s+', r'\1- @@TAREFA_OK@@', md_texto)

    corpo = markdown.markdown(
        md_texto, extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'])

    corpo = corpo.replace('<li>@@TAREFA@@', '<li class="tarefa">')
    corpo = corpo.replace('<li>@@TAREFA_OK@@', '<li class="tarefa">')
    corpo = corpo.replace('<li class="tarefa"><p>', '<li class="tarefa">')

    # O <h1> do .md sobe para o cabecalho, para nao repetir na primeira pagina.
    corpo = re.sub(r'<h1>.*?</h1>', '', corpo, count=1, flags=re.S)

    gerado = datetime.now().strftime('%d/%m/%Y')
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{titulo}</title><style>{CSS}{ESTILOS.get(estilo, '')}</style></head>
<body>
  <div class="cabecalho">
    <div class="escritorio">{ESCRITORIO}</div>
    <div class="meta">Gerência Jurídica<br>Documento interno · {gerado}</div>
  </div>
  <h1>{titulo}</h1>
  {corpo}
  <div class="rodape">{ESCRITORIO} — uso interno. Contém dados de processos e de equipe.</div>
</body></html>"""


def converter(caminho_md, pasta_saida=None, estilo='gestao'):
    chrome = _achar_chrome()
    if not chrome:
        raise RuntimeError('Google Chrome nao encontrado - sem motor de PDF.')

    md_texto = open(caminho_md, encoding='utf-8').read()
    base = os.path.splitext(os.path.basename(caminho_md))[0]
    titulo = _titulo(md_texto, base.replace('_', ' ').title())
    html = md_para_html(md_texto, titulo, estilo)

    pasta = pasta_saida or os.path.dirname(os.path.abspath(caminho_md))
    os.makedirs(pasta, exist_ok=True)
    pdf = os.path.join(pasta, base + '.pdf')

    # O HTML vai para arquivo temporario: data: URL estoura e o Chrome
    # precisa de file:// para aplicar @page corretamente.
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False,
                                     encoding='utf-8') as tmp:
        tmp.write(html)
        tmp_html = tmp.name
    try:
        subprocess.run(
            [chrome, '--headless', '--disable-gpu', '--no-pdf-header-footer',
             '--no-sandbox', f'--print-to-pdf={pdf}', f'file://{tmp_html}'],
            check=True, capture_output=True, timeout=120)
    finally:
        os.unlink(tmp_html)

    if not os.path.exists(pdf):
        raise RuntimeError(f'Chrome nao gerou {pdf}')
    return pdf


def main():
    ap = argparse.ArgumentParser(description='Converte relatorios .md do projeto em PDF')
    ap.add_argument('arquivos', nargs='+', help='Arquivos .md')
    ap.add_argument('--saida', help='Pasta de destino (padrao: a mesma do .md)')
    ap.add_argument('--estilo', choices=sorted(ESTILOS), default='gestao',
                    help='gestao (padrao) ou nota-tecnica (paleta de visual law da peca)')
    args = ap.parse_args()

    for caminho in args.arquivos:
        if not os.path.exists(caminho):
            print(f'  [X] nao encontrado: {caminho}')
            continue
        try:
            pdf = converter(caminho, args.saida, args.estilo)
            tamanho = os.path.getsize(pdf) / 1024
            print(f'  [ok] {os.path.basename(pdf)}  ({tamanho:.0f} KB)')
        except Exception as erro:
            print(f'  [X] {os.path.basename(caminho)}: {erro}')


if __name__ == '__main__':
    main()
