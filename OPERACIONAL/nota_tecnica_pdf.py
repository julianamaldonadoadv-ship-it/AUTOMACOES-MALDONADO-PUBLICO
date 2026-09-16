"""
=============================================================================
  NOTA TECNICA -> PDF - Maldonado Advogados
=============================================================================

  Converte a nota tecnica de analise de caso (.md) no PDF que a skill
  `descaracterizacao-mora` especifica na secao 10bis ("Formato de entrega"):
  Arial Narrow, cabecalho de secao em laranja (#f6b26b), tabela com cabecalho
  azul (#2e5d9c) e citacao de precedente em verde (#e2efda), preservando a
  identidade visual entre a nota tecnica e a peca.

  Por que nao o md_para_pdf.py: aquele e' o documento de gestao interna
  (Helvetica, faixa bordo). Este segue a paleta do visual law das pecas.

  Por que Chrome e nao pandoc + wkhtmltopdf, que a skill cita: nenhum dos dois
  esta instalado no Mac do escritorio, e cada um puxaria LaTeX ou GTK. O motor
  e' o mesmo do md_para_pdf.py, ja em uso no repositorio.

  Uso:
      python OPERACIONAL/nota_tecnica_pdf.py docs/notas_tecnicas/NOTA_*.md
=============================================================================
"""
import os
import re
import sys
import argparse
import subprocess
import tempfile
from datetime import datetime

try:
    import markdown
except ImportError:  # pragma: no cover
    print('ERRO: falta a biblioteca markdown. Rode:  pip install markdown')
    sys.exit(1)

from md_para_pdf import _achar_chrome, _titulo

ESCRITORIO = os.getenv('ESCRITORIO_NOME', 'Maldonado Advogados')

# Paleta da secao 10ter da skill. A cor e' sempre redundante: o rotulo textual
# carrega a informacao sozinho, porque boa parte dos autos sai monocromatica.
CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
* { box-sizing: border-box; }
body {
  font-family: "Arial Narrow", "Helvetica Neue Condensed", Arial, sans-serif;
  font-size: 10.5pt; line-height: 1.45; color: #1a1a1a; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.cabecalho {
  border-bottom: 2.5pt solid #2e5d9c; padding-bottom: 6pt; margin-bottom: 16pt;
  display: flex; justify-content: space-between; align-items: baseline;
}
.escritorio { font-size: 13pt; font-weight: bold; letter-spacing: .1em; color: #2e5d9c; }
.meta { font-size: 8pt; color: #555; text-align: right; line-height: 1.35; }
h1 { font-size: 17pt; margin: 0 0 14pt; line-height: 1.2; }
h2 {
  background: #f6b26b; color: #4a2c00; font-size: 12pt; font-weight: bold;
  padding: 5pt 8pt; margin: 20pt 0 9pt; border-radius: 2pt;
  page-break-after: avoid; page-break-inside: avoid;
}
h3 { font-size: 11pt; margin: 14pt 0 6pt; color: #2e5d9c; page-break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; }
ul, ol { margin: 0 0 8pt; padding-left: 17pt; }
li { margin-bottom: 3pt; text-align: justify; }
strong { font-weight: bold; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt; font-size: 9.5pt; }
th {
  background: #2e5d9c; color: #fff; text-align: left; font-weight: bold;
  padding: 4pt 6pt; border: .5pt solid #2e5d9c;
}
td { padding: 4pt 6pt; border: .5pt solid #b9c6d8; vertical-align: top; }
tbody tr:nth-child(even) td { background: #f2f5fa; }
/* Quadro de identificacao: sem cabecalho, rotulo na coluna da esquerda. */
.ident table thead { display: none; }
.ident td:first-child { background: #dce6f1; font-weight: bold; width: 27%; }
.ident tbody tr:nth-child(even) td:not(:first-child) { background: #fff; }
/* Precedente: tarja acima do bloco, nunca no lugar dele. A citacao mantem o
   recuo de 4 cm, o italico e a fonte centralizada em negrito + italico. */
blockquote {
  margin: 9pt 0 11pt 4cm; padding: 6pt 9pt; background: #e2efda;
  border-left: 3pt solid #4f7a3a; font-style: italic; font-size: 10pt;
  page-break-inside: avoid;
}
blockquote p { margin: 0 0 4pt; text-align: justify; }
blockquote p:last-child { margin-bottom: 0; }
.fonte { display: block; text-align: center; font-weight: bold; font-style: italic; font-size: 9pt; }
.conclusao, .alerta, .pendencia { padding: 7pt 9pt; margin: 10pt 0 12pt; border-radius: 2pt; page-break-inside: avoid; }
.conclusao { background: #e2efda; border-left: 4pt solid #4f7a3a; }
.alerta { background: #ffe6e6; border-left: 4pt solid #b03030; }
.pendencia { background: #fff2b2; border-left: 4pt solid #bf9000; }
.conclusao p:last-child, .alerta p:last-child, .pendencia p:last-child { margin-bottom: 0; }
hr { border: 0; border-top: .5pt solid #ccc; margin: 14pt 0; }
code { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 8.5pt;
       background: #eef1f5; padding: 0 2pt; border-radius: 2pt; }
em { font-style: italic; }
.rodape { margin-top: 20pt; padding-top: 6pt; border-top: .5pt solid #ccc;
          font-size: 8pt; color: #666; text-align: center; }
"""


def md_para_html(md_texto, titulo):
    """Markdown -> HTML autocontido, com a paleta do visual law da skill."""
    # As caixas (.conclusao/.alerta/.pendencia/.ident) tem markdown dentro;
    # o md_in_html so processa o conteudo se a tag pedir markdown="1".
    md_texto = re.sub(r'<div class="(conclusao|alerta|pendencia|ident)">',
                      r'<div class="\1" markdown="1">', md_texto)

    corpo = markdown.markdown(
        md_texto,
        extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list', 'md_in_html'])

    # O <h1> do .md sobe para o cabecalho, para nao repetir na primeira pagina.
    corpo = re.sub(r'<h1>.*?</h1>', '', corpo, count=1, flags=re.S)

    gerado = datetime.now().strftime('%d/%m/%Y')
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{titulo}</title><style>{CSS}</style></head>
<body>
  <div class="cabecalho">
    <div class="escritorio">{ESCRITORIO}</div>
    <div class="meta">Nota Tecnica de Analise de Caso<br>Documento interno &middot; {gerado}</div>
  </div>
  <h1>{titulo}</h1>
  {corpo}
  <div class="rodape">{ESCRITORIO}: uso interno. Analise previa; nao e' peca processual.</div>
</body></html>"""


def converter(caminho_md, pasta_saida=None):
    chrome = _achar_chrome()
    if not chrome:
        raise RuntimeError('Google Chrome nao encontrado - sem motor de PDF.')

    md_texto = open(caminho_md, encoding='utf-8').read()
    base = os.path.splitext(os.path.basename(caminho_md))[0]
    titulo = _titulo(md_texto, base.replace('_', ' ').title())
    html = md_para_html(md_texto, titulo)

    pasta = pasta_saida or os.path.dirname(os.path.abspath(caminho_md))
    os.makedirs(pasta, exist_ok=True)
    pdf = os.path.join(pasta, base + '.pdf')

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
    ap = argparse.ArgumentParser(
        description='Converte a nota tecnica (.md) no PDF da secao 10bis da skill')
    ap.add_argument('arquivos', nargs='+', help='Arquivos .md')
    ap.add_argument('--saida', help='Pasta de destino (padrao: a mesma do .md)')
    args = ap.parse_args()

    for caminho in args.arquivos:
        if not os.path.exists(caminho):
            print(f'  [X] nao encontrado: {caminho}')
            continue
        try:
            pdf = converter(caminho, args.saida)
            print(f'  [ok] {os.path.basename(pdf)}  ({os.path.getsize(pdf)/1024:.0f} KB)')
        except Exception as erro:
            print(f'  [X] {os.path.basename(caminho)}: {erro}')


if __name__ == '__main__':
    main()
