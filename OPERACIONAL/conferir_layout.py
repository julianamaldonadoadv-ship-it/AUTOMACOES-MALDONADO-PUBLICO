# -*- coding: utf-8 -*-
"""
Conferencia visual da peca (POP-CJ-003-B, etapa 8)
===================================================

Antes de entregar, a peca tem que ser OLHADA renderizada — nao basta o .docx
"estar certo" no codigo. Foi assim que apareceram, na peca de um cliente
(08/09/2026), o endereçamento justificado (devia ser centralizado) e o excesso
de espaço no topo.

Como nao ha LibreOffice nesta maquina, o caminho e o mesmo do POP:

    sobe uma copia temporaria convertida em Google Docs
        -> files().export_media(mimeType='application/pdf')
        -> renderiza as paginas com PyMuPDF
        -> APAGA a copia temporaria (sempre, mesmo em erro)

A copia temporaria vai para a raiz do Drive e vive segundos. Nada e' gravado
na ZEUS por este modulo.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))

from googleapiclient.http import MediaFileUpload

MIME_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def renderizar(drive_service, caminho_docx, saida_dir=None, dpi=110, paginas=3):
    """Renderiza o .docx em PNG (uma imagem por pagina) para conferencia visual.

    Devolve a lista de arquivos PNG gerados. A copia no Drive e' sempre
    removida no final — inclusive se a exportacao falhar.
    """
    import fitz  # PyMuPDF

    saida_dir = saida_dir or os.path.join(os.path.dirname(caminho_docx), '_conferencia')
    os.makedirs(saida_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(caminho_docx))[0]

    copia_id = None
    try:
        # 1. sobe convertendo para Google Docs (e a conversao que renderiza o layout)
        meta = {'name': f'[TEMP CONFERENCIA] {base}',
                'mimeType': 'application/vnd.google-apps.document'}
        media = MediaFileUpload(caminho_docx, mimetype=MIME_DOCX, resumable=False)
        copia = drive_service.files().create(
            body=meta, media_body=media, fields='id',
            supportsAllDrives=True).execute()
        copia_id = copia['id']

        # 2. exporta em PDF
        pdf_bytes = drive_service.files().export_media(
            fileId=copia_id, mimeType='application/pdf').execute()
        caminho_pdf = os.path.join(saida_dir, f'{base}.pdf')
        with open(caminho_pdf, 'wb') as fh:
            fh.write(pdf_bytes)
    finally:
        # 3. a copia temporaria NUNCA fica para tras
        if copia_id:
            try:
                drive_service.files().delete(fileId=copia_id,
                                             supportsAllDrives=True).execute()
            except Exception as e:
                print(f'  AVISO: nao consegui apagar a copia temporaria {copia_id}: {e}')

    # 4. renderiza as paginas
    imagens = []
    with fitz.open(caminho_pdf) as doc:
        for n, pagina in enumerate(doc, 1):
            if n > paginas:
                break
            pix = pagina.get_pixmap(dpi=dpi)
            destino = os.path.join(saida_dir, f'{base} - p{n}.png')
            pix.save(destino)
            imagens.append(destino)
    return imagens
