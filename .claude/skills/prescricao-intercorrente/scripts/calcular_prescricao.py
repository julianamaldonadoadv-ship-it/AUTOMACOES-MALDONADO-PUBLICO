#!/usr/bin/env python3
"""
Calculadora de Prescrição Intercorrente Trienal
Escritório Maldonado Advogados
Uso: python3 calcular_prescricao.py
"""

from datetime import date
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dateutil", "-q"])
    from dateutil.relativedelta import relativedelta


def calcular_prescricao(
    data_marco_inicial: str,
    atos_interruptivos: list = None,
    prazo_prescricional_anos: int = 3,
    tipo_marco: str = "diligencia_negativa"
) -> dict:
    """
    Calcula o prazo de prescrição intercorrente.

    Args:
        data_marco_inicial: Data do marco inicial no formato YYYY-MM-DD.
                            Pode ser a data da 1ª diligência negativa juntada aos autos
                            ou a data do despacho de suspensão judicial (art. 921, III, CPC).
        atos_interruptivos: Lista de dicts com atos eficazes (citação válida ou penhora efetiva):
                            [{"data": "YYYY-MM-DD", "descricao": "...", "executado": "..."}]
        prazo_prescricional_anos: 3 para CCB/CRP/NCR (padrão), 5 para contratos bancários simples.
        tipo_marco: "diligencia_negativa" ou "despacho_suspensao"

    Returns:
        Dicionário com análise completa e resultado.
    """
    if atos_interruptivos is None:
        atos_interruptivos = []

    marco = date.fromisoformat(data_marco_inicial)
    fim_suspensao = marco + relativedelta(years=1)
    inicio_prazo = fim_suspensao
    data_consumacao_base = inicio_prazo + relativedelta(years=prazo_prescricional_anos)

    resultado = {
        "marco_inicial": marco.strftime("%d/%m/%Y"),
        "tipo_marco": tipo_marco,
        "fim_suspensao_1_ano": fim_suspensao.strftime("%d/%m/%Y"),
        "inicio_prazo_prescricional": inicio_prazo.strftime("%d/%m/%Y"),
        "data_consumacao_sem_interrupcao": data_consumacao_base.strftime("%d/%m/%Y"),
        "prazo_anos": prazo_prescricional_anos,
        "atos_analisados": [],
        "data_consumacao_efetiva": None,
        "prescricao_consumada": None,
        "data_hoje": date.today().strftime("%d/%m/%Y"),
    }

    # Analisa atos interruptivos
    atos_validos_pos_suspensao = []
    for ato in atos_interruptivos:
        data_ato = date.fromisoformat(ato["data"])
        if data_ato < inicio_prazo:
            resultado["atos_analisados"].append({
                "data": data_ato.strftime("%d/%m/%Y"),
                "descricao": ato.get("descricao", ""),
                "executado": ato.get("executado", ""),
                "interrompe": False,
                "motivo": "Ocorreu DURANTE o período de suspensão — não interrompe prazo que ainda não fluiu"
            })
        else:
            atos_validos_pos_suspensao.append({
                "data_obj": data_ato,
                "data": data_ato.strftime("%d/%m/%Y"),
                "descricao": ato.get("descricao", ""),
                "executado": ato.get("executado", ""),
                "interrompe": True,
                "nova_consumacao": (data_ato + relativedelta(years=prazo_prescricional_anos)).strftime("%d/%m/%Y")
            })
            resultado["atos_analisados"].append(atos_validos_pos_suspensao[-1])

    if atos_validos_pos_suspensao:
        ultimo = max(atos_validos_pos_suspensao, key=lambda x: x["data_obj"])
        data_consumacao_final = ultimo["data_obj"] + relativedelta(years=prazo_prescricional_anos)
        resultado["data_consumacao_efetiva"] = data_consumacao_final.strftime("%d/%m/%Y")
        resultado["prescricao_consumada"] = date.today() > data_consumacao_final
    else:
        resultado["data_consumacao_efetiva"] = data_consumacao_base.strftime("%d/%m/%Y")
        resultado["prescricao_consumada"] = date.today() > data_consumacao_base

    return resultado


def imprimir_relatorio(resultado: dict, processo: str = "", partes: str = ""):
    sep = "=" * 68
    print(sep)
    print("ANÁLISE DE PRESCRIÇÃO INTERCORRENTE TRIENAL")
    if processo:
        print(f"Processo: {processo}")
    if partes:
        print(f"Partes: {partes}")
    print(sep)
    print(f"\nData de hoje: {resultado['data_hoje']}")
    print()

    tipo = "1ª diligência negativa juntada" if resultado["tipo_marco"] == "diligencia_negativa" else "despacho de suspensão (art. 921, III, CPC)"
    print(f"📌 MARCO INICIAL ({tipo}):")
    print(f"   {resultado['marco_inicial']}")
    print(f"\n⏸️  Período de suspensão de 1 ano: até {resultado['fim_suspensao_1_ano']}")
    print(f"▶️  Início do prazo prescricional trienal: {resultado['inicio_prazo_prescricional']}")
    print(f"⚠️  Consumação (sem atos interruptivos): {resultado['data_consumacao_sem_interrupcao']}")

    if resultado["atos_analisados"]:
        print(f"\n📋 ATOS COM POTENCIAL INTERRUPTIVO ANALISADOS:")
        for ato in resultado["atos_analisados"]:
            exec_str = f" [{ato['executado']}]" if ato.get("executado") else ""
            if ato["interrompe"]:
                print(f"   ✅ {ato['data']}{exec_str} — {ato['descricao']}")
                print(f"      → INTERROMPE. Nova consumação: {ato['nova_consumacao']}")
            else:
                print(f"   ❌ {ato['data']}{exec_str} — {ato['descricao']}")
                print(f"      → NÃO INTERROMPE: {ato['motivo']}")

    print(f"\n📅 DATA DE CONSUMAÇÃO EFETIVA: {resultado['data_consumacao_efetiva']}")
    print()

    if resultado["prescricao_consumada"]:
        from datetime import datetime; consumacao = datetime.strptime(resultado["data_consumacao_efetiva"], "%d/%m/%Y")
        hoje = datetime.strptime(resultado["data_hoje"], "%d/%m/%Y")
        diff = (hoje - consumacao).days
        print(f"🔴 CONCLUSÃO: PRESCRIÇÃO INTERCORRENTE CONSUMADA")
        print(f"   Há {diff} dias ({diff // 30} meses) desde a consumação")
        print(f"   Fundamento: art. 921, III, §1º, §4º e §4º-A, CPC + art. 206-A, CC")
        print(f"   + Lei 10.931/2004, art. 44 + LUG, art. 70 + art. 924, V c/c 487, II, CPC")
        print(f"   → Cabível extinção com resolução de mérito")
    else:
        from datetime import datetime; consumacao = datetime.strptime(resultado["data_consumacao_efetiva"], "%d/%m/%Y")
        hoje = datetime.strptime(resultado["data_hoje"], "%d/%m/%Y")
        restam = (consumacao - hoje).days
        print(f"🟡 CONCLUSÃO: Prazo ainda em curso")
        print(f"   Restam {restam} dias para a consumação ({restam // 30} meses)")
        print(f"   → Monitorar processo até {resultado['data_consumacao_efetiva']}")

    print(sep)


# ─── EXEMPLOS DOS PROCESSOS ANALISADOS (números e nomes fictícios) ────────────

if __name__ == "__main__":

    print("\n" + "─" * 68)
    print("CASO 1 — Processo 0000011-00.0000.8.22.0001 (Porto Velho/RO)")
    print("─" * 68)
    r1 = calcular_prescricao(
        data_marco_inicial="2023-03-02",   # certidão do oficial — 1ª diligência negativa
        atos_interruptivos=[],
        prazo_prescricional_anos=3,
        tipo_marco="diligencia_negativa"
    )
    imprimir_relatorio(r1,
        processo="0000011-00.0000.8.22.0001",
        partes="Banco da Amazônia SA x Executada A e Executada B"
    )
    print("⚖️  STATUS REAL: EXTINTO POR SENTENÇA em 15/05/2026\n")

    print("\n" + "─" * 68)
    print("CASO 2 — Processo 0000012-00.0000.8.22.0001 (Porto Velho/RO)")
    print("EXECUTADA: EXECUTADA C")
    print("─" * 68)
    r2 = calcular_prescricao(
        data_marco_inicial="2023-03-02",   # certidão negativa (Executado D) juntada 02/03/2023
        atos_interruptivos=[
            {
                "data": "2023-12-04",
                "descricao": "Citação da Executada C com entrega de contrafé",
                "executado": "Executada C"
            }
        ],
        prazo_prescricional_anos=3,
        tipo_marco="diligencia_negativa"
    )
    imprimir_relatorio(r2,
        processo="0000012-00.0000.8.22.0001",
        partes="Banco da Amazônia SA x Executada C e Executado D"
    )
    print("⚖️  STATUS REAL: Prazo em curso — monitorar até 02/03/2027\n")

    print("\n" + "─" * 68)
    print("CASO 3 — Processo 0000013-00.0000.8.22.0021 (Buritis/RO)")
    print("─" * 68)
    r3 = calcular_prescricao(
        data_marco_inicial="2021-05-18",   # despacho de suspensão judicial (art. 921, III)
        atos_interruptivos=[],
        prazo_prescricional_anos=3,
        tipo_marco="despacho_suspensao"
    )
    imprimir_relatorio(r3,
        processo="0000013-00.0000.8.22.0021",
        partes="Banco da Amazônia SA x Executado E e Executado F"
    )
    print("⚖️  STATUS REAL: 🔴 EXCEÇÃO CABÍVEL IMEDIATAMENTE\n")
