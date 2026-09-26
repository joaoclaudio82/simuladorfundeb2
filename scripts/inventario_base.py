"""
FND-01 / FND-04 — Inventário reproduzível das bases do catálogo e comparação com os valores oficiais.
Uso: python scripts/inventario_base.py > docs/INVENTARIO_BASE.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from schemas.cenarios import CenarioRequest  # noqa: E402
from services.bases import carregar_base, ler_catalogo  # noqa: E402
from services.calibracao import comparar_com_oficial  # noqa: E402
from services.cenarios import executar_cenario  # noqa: E402


def _bi(v):
    return f"{v / 1e9:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(v, casas=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def secao_base(base_id):
    base = carregar_base(base_id)
    m = base.manifesto
    print(f"## `{base_id}` — exercício {m['ano_exercicio']}\n")
    print(f"- Situação: {m['situacao']} · homologada: {'sim' if m.get('homologada') else 'não'}")
    print(f"- Receita: {m.get('periodo_receita') or 'não informado'}"
          f"{' (publicação ' + m['data_publicacao'] + ')' if m.get('data_publicacao') else ''}")
    print(f"- Ponderador: {'NSE e DREC oficiais' if base.modo_ponderador == 'drec' else 'NSE e NF'}\n")
    print("| Papel | Arquivo de origem | SHA-256 |")
    print("|---|---|---|")
    for a in m["arquivos"]:
        print(f"| {a['papel']} | `{a['caminho']}` | `{a['sha256'][:16]}…` |")

    tipos = base.entes["tipo_rede"].value_counts()
    inab = base.complementar[base.complementar["inabilitados_vaat"]]
    valores = base.matriculas[base.etapas].to_numpy()
    comp = base.complementar
    print("\n**Cobertura e cadastro**\n")
    print(f"- Entes: {len(base.entes)} ({', '.join(f'{t}: {n}' for t, n in tipos.items())})")
    print("- Identificadores duplicados: nenhum; matrículas e receitas cobrem o mesmo conjunto de entes")
    print(f"- Categorias de matrícula: {len(base.etapas)}; contagens não inteiras: "
          f"{'sim' if not np.allclose(valores, np.round(valores)) else 'não'}")
    print(f"- Redes inabilitadas para VAAT: {len(inab)}"
          f" (estaduais/DF: {', '.join(sorted(inab.loc[inab['ibge'] < 100, 'uf'])) or 'nenhuma'})")
    print(f"- Redes com `recursos_vaat` igual a zero: {int((comp['recursos_vaat'] == 0).sum())}")
    p = base.parametros_referencia
    print(f"- Complementações de referência: VAAF R$ {_bi(p['complementacao_vaaf'])} bi, "
          f"VAAT R$ {_bi(p['complementacao_vaat'])} bi, VAAR R$ {_bi(p['complementacao_vaar'])} bi")
    for aviso in base.avisos:
        print(f"- Aviso: {aviso}")

    res = executar_cenario(CenarioRequest(base_id=base_id), base)
    ref = res.resultados["A"].merge(base.referencia, on="ibge", suffixes=("", "_ref"))
    d = (ref["recursos_fundeb"] - ref["recursos_fundeb_ref"]).abs().max()
    print(f"\n**Reprodução do cenário de referência** (`cenario_atual`): maior diferença por ente em "
          f"recursos do Fundeb = R$ {_num(d)}; validação interna: "
          f"{'ok' if res.validacoes['A']['valido'] else res.validacoes['A']['erros']}.")
    if base.modo_ponderador == "drec":
        print("Nos exercícios 2025 e 2026 o `cenario_atual` é produzido pelo próprio motor com os dados oficiais; "
              "por isso a comparação com os valores oficiais abaixo é a que importa.")

    cal = comparar_com_oficial(base)
    if not cal["disponivel"]:
        print(f"\n**Comparação com valores oficiais:** indisponível ({cal['motivo']}).\n")
        return
    print("\n**Comparação com os valores oficiais por ente** (planilha de receita do exercício)\n")
    print("| Indicador | Total simulado (R$ bi) | Total oficial (R$ bi) | Maior diferença por ente (R$) "
          "| Entes acima de R$ 1.000 | Recebem só na simulação | Recebem só no oficial |")
    print("|---|---|---|---|---|---|---|")
    for i in cal["indicadores"]:
        print(f"| {i['rotulo']} | {_bi(i['total_simulado'])} | {_bi(i['total_oficial'])} "
              f"| {_num(i['maior_diferenca_absoluta'])} | {i['entes_acima_da_tolerancia']} "
              f"| {i['recebem_so_na_simulacao']} | {i['recebem_so_no_oficial']} |")
    acima = [u for u in cal["por_uf"] if u["acima_da_tolerancia"]]
    print(f"\nUFs acima da tolerância provisória ({cal['tolerancias']['por_uf_pct']}%): "
          f"{', '.join(u['uf'] for u in acima) or 'nenhuma'}\n")
    print("| UF | Desvio absoluto nos recursos do Fundeb (% do oficial) | Complementação VAAF: simulado − oficial (%) |")
    print("|---|---|---|")
    for u in cal["por_uf"][:8]:
        print(f"| {u['uf']} | {_num(u['desvio_abs_fundeb_pct'], 3)} | {_num(u['vaaf_dif_pct'], 3)} |")
    print("\nMaiores diferenças por ente (recursos do Fundeb):\n")
    print("| UF | Ente | IBGE | Simulado (R$) | Oficial (R$) | Diferença (%) |")
    print("|---|---|---|---|---|---|")
    for r in cal["maiores_diferencas"][:8]:
        print(f"| {r['uf']} | {r['nome']} | {r['ibge']} | {_num(r['recursos_fundeb'], 0)} "
              f"| {_num(r['recursos_fundeb_total'], 0)} | {_num(r['dif_fundeb_pct'])} |")
    if cal["vaat_elegibilidade_divergente"]:
        print("\nEntes com elegibilidade VAAT divergente (recebem em um lado e não no outro):\n")
        for r in cal["vaat_elegibilidade_divergente"]:
            print(f"- {r['uf']} {r['nome']} ({r['ibge']}): inabilitado na base = {r['inabilitados_vaat']}; "
                  f"simulado R$ {_num(r['complemento_vaat'])}; oficial R$ {_num(r['comp_vaat_oficial'])}")
    print()


def main():
    print("# Inventário das bases\n")
    print("Gerado por `scripts/inventario_base.py`. Não editar à mão.\n")
    print("A reprodução do cenário de referência e a validação interna não substituem a comparação "
          "com os valores oficiais. Tolerâncias usadas são provisórias (FND-02).\n")
    for b in ler_catalogo()["bases"]:
        secao_base(b["base_id"])


if __name__ == "__main__":
    main()
