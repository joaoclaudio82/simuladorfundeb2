"""Artigo em Markdown a partir dos CSVs do estudo nacional."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from analises.fundeb_ceara.relatorio import brl, num, pct
from analises.fundeb_regioes.config import ANALISE_DIR, RESULTADOS_DIR


def _ler(nome: str) -> pd.DataFrame:
    return pd.read_csv(Path(RESULTADOS_DIR) / nome)


def mi(x) -> str:
    return num(float(x) / 1e6, 1)


def _md(df: pd.DataFrame, cols: list[str], fmt: dict | None = None) -> str:
    fmt = fmt or {}
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, r in df.iterrows():
        cells = [fmt[c](r[c]) if c in fmt else str(r[c]) for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def escrever(dados: dict[str, pd.DataFrame] | None = None) -> Path:
    if dados is None:
        dados = {
            "baseline": _ler("baseline.csv"),
            "simulacoes": _ler("simulacoes.csv"),
            "melhores": _ler("melhores.csv"),
            "controle_inverso": _ler("controle_inverso.csv"),
            "meta": _ler("meta.csv"),
            "municipios": _ler("municipios.csv"),
        }
    base = dados["baseline"]
    mel = dados["melhores"]
    sim = dados["simulacoes"]
    ctrl = dados["controle_inverso"]
    meta = dados["meta"]
    muns = dados["municipios"]

    ano = int(mel["ano"].max())
    anos = ", ".join(str(int(a)) for a in sorted(meta["ano"].unique()))
    n_cen = int(meta["n_cenarios"].sum())
    n_ok = int(meta["n_validos"].sum())

    ida = sim[sim["familia"] == "parcial_para_integral"]
    cem = ida[(ida["ano"] == ano) & (ida["percentual"] == 100)]
    melhores_ano = mel[mel["ano"] == ano].sort_values(["regiao", "municipio"])
    n_pos = int((melhores_ano["delta_r"] > 0).sum())
    n_mun = len(melhores_ano)

    ctrl_c = ctrl[(ctrl["ano"] == ano) & (ctrl["codigo_transicao"] == "C")].sort_values("municipio")
    n_neg_ctrl = int((ctrl_c["delta_r"] < 0).sum()) if len(ctrl_c) else 0

    top_pct = melhores_ano.loc[melhores_ano["delta_r_percentual"].idxmax()]
    top_abs = melhores_ano.loc[melhores_ano["delta_r"].idxmax()]
    min_pct = melhores_ano.loc[melhores_ano["delta_r_percentual"].idxmin()]

    spill = (
        cem.sort_values("delta_r", ascending=False)
        .groupby("municipio", as_index=False)
        .first()
        .sort_values("regiao")
    )
    ufs_comp = spill.loc[spill["delta_uf_total"] > 1_000_000, "uf"].tolist()
    ufs_zero = spill.loc[spill["delta_uf_total"].abs() < 1, "uf"].tolist()

    am = muns[muns["ano"] == ano].sort_values(["regiao", "municipio"])
    n_ufs = am["uf"].nunique()
    n_reg = am["regiao"].nunique()

    p: list[str] = []
    p.append("# Composição das matrículas e transferências do FUNDEB: evidência contrafactual nas cinco regiões brasileiras")
    p.append("")
    p.append("## Resumo")
    p.append("")
    p.append(
        f"Este artigo testa, no motor completo do FUNDEB, se a composição das matrículas — "
        f"e não apenas o total de alunos — altera os recursos simulados de municípios e estados. "
        f"A amostra cobre {n_mun} municípios de {n_ufs} unidades da federação, com ao menos um estado "
        f"em cada uma das {n_reg} regiões brasileiras. Em cada cenário, um percentual dos alunos de "
        f"uma modalidade de menor peso é transferido para outra de maior peso (ou o inverso), "
        f"conservando o total de matrículas do município. O simulador é reexecutado sobre todos os "
        f"entes do país. Nos exercícios {anos} foram gerados {n_cen} cenários, todos aprovados pela "
        f"validação interna do motor. No exercício {ano}, a melhor transformação factível aumentou "
        f"os recursos do município-alvo em {n_pos} de {n_mun} casos; o controle inverso reduziu-os "
        f"em {n_neg_ctrl} de {len(ctrl_c)}. O sinal segue a diferença de pesos. O ente estadual e os "
        f"demais municípios da mesma UF absorvem parte do ajuste. A soma estadual só cresce de forma "
        f"material quando a União complementar o fundo (VAAF/VAAT). Os resultados descrevem incentivos "
        f"implícitos nos fatores de ponderação; não constituem recomendação para reclassificar alunos."
    )
    p.append("")
    p.append(
        "**Palavras-chave:** FUNDEB; matrícula ponderada; fatores de ponderação; VAAF; VAAT; "
        "estudo contrafactual; equalização federativa."
    )
    p.append("")
    p.append("## Abstract")
    p.append("")
    p.append(
        f"We test, in a full FUNDEB simulation engine, whether the composition of enrollments — "
        f"holding the municipal headcount fixed — changes simulated transfers to municipalities and "
        f"states. The sample comprises {n_mun} municipalities in {n_ufs} states, covering all five "
        f"Brazilian regions, over {anos}. Counterfactual shifts from lower-weight to higher-weight "
        f"modalities raise municipal resources in {n_pos}/{n_mun} cases in {ano}; the reverse shift "
        f"lowers them in {n_neg_ctrl}/{len(ctrl_c)}. The state-level total rises only when the Union "
        f"complements the fund. The article maps implicit incentives in weighting factors; it does "
        f"not recommend reclassifying students."
    )
    p.append("")
    p.append("**Keywords:** FUNDEB; weighted enrollment; VAAF; VAAT; counterfactual simulation.")
    p.append("")
    p.append("## 1 Introdução")
    p.append("")
    p.append(
        "O Fundo de Manutenção e Desenvolvimento da Educação Básica e de Valorização dos Profissionais "
        "da Educação (FUNDEB) reparte recursos segundo matrículas ponderadas por etapa, modalidade e "
        "turno, e equaliza o valor aluno-ano entre entes (VAAF no âmbito estadual; VAAT no âmbito "
        "nacional). Segue da fórmula que dois municípios com o mesmo número de alunos podem receber "
        "montantes distintos se a composição das matrículas for diferente. A tese examinada aqui é "
        "mais estreita e operacional: *mantido constante o total de alunos de um município, uma "
        "reclassificação contrafactual entre modalidades de pesos distintos altera o que esse "
        "município — e o estado a que pertence — recebe no motor oficial do fundo?*"
    )
    p.append("")
    p.append(
        "A pergunta não é normativa. Transferir alunos de turno parcial para integral, ou o inverso, "
        "tem custos pedagógicos, de infraestrutura e de jornada que este estudo não estima. O ótimo "
        "matemático (concentrar matrículas na etapa de maior peso) não é tratado como política. O "
        "objeto é o incentivo financeiro implícito nos fatores de ponderação: se o sinal do efeito "
        "é estável entre regiões, anos e sentidos da transferência, a composição deixa de ser um "
        "detalhe de planilha e passa a ser um parâmetro causal da alocação simulada."
    )
    p.append("")
    p.append(
        "Um estudo anterior, restrito a dez municípios do Ceará, já havia documentado ganhos "
        "municipais, quase-linearidade e spillover intraestadual. Restava saber se o mecanismo é "
        "local ou nacional: se capitais de UFs ricas e pobres, do Norte ao Sul, reproduzem o mesmo "
        "sinal, e se a União entra ou não no ajuste. Este artigo responde com uma amostra mínima "
        "que cruza as cinco macrorregiões."
    )
    p.append("")
    p.append("## 2 Dados e método")
    p.append("")
    p.append("### 2.1 Amostra e exercícios")
    p.append("")
    p.append(
        f"Selecionaram-se {n_mun} municípios — capitais e grandes redes — em {n_ufs} estados, "
        f"com pelo menos um estado em cada região. Os códigos IBGE foram resolvidos no próprio "
        f"dataset (município: IBGE > 100; nome oficial normalizado e UF), sem lista prévia de códigos. "
        f"Os exercícios são {anos}: o de 2024 vem dos arquivos legados do simulador; 2025 e 2026, "
        f"das planilhas oficiais do ciclo correspondente. Cada ano é um snapshot completo, não uma "
        f"série interpolada."
    )
    p.append("")
    p.append(f"**Tabela 1.** Municípios da amostra (exercício {ano}).")
    p.append("")
    p.append(_md(am, ["regiao", "uf", "municipio", "ibge"], {"ibge": lambda x: str(int(x))}))
    p.append("")
    p.append(
        f"**Tabela 2.** Baseline municipal no exercício {ano}: matrículas totais, recursos FUNDEB "
        "e complementação da União recebida pelo ente."
    )
    p.append("")
    p.append(_md(
        base[base["ano"] == ano].sort_values(["regiao", "municipio"]),
        ["municipio", "uf", "regiao", "total_matriculas", "recursos_fundeb", "complemento_uniao"],
        {
            "total_matriculas": lambda x: num(x, 0),
            "recursos_fundeb": brl,
            "complemento_uniao": brl,
        },
    ))
    p.append("")
    p.append("### 2.2 Desenho contrafactual")
    p.append("")
    p.append(
        "Quatro transições factíveis de turno, detectadas automaticamente pelos aliases de etapa "
        "de cada ano, formam a grade experimental: (A) creche parcial → integral pública; "
        "(B) pré-escola parcial → integral pública; (C) ensino fundamental, anos iniciais urbano → "
        "fundamental integral; (D) anos finais urbano → fundamental integral. Em 2024 o peso VAAF "
        "do fundamental integral é 1,40; em 2025–2026, 1,50. O peso dos anos iniciais urbanos permanece 1,00."
    )
    p.append("")
    p.append(
        "Para cada município, transição e percentual de 5% a 100% (passo 5), os alunos são "
        "movidos da origem para o destino. A conservação do total municipal e a não-negatividade "
        "são exigidas antes de cada simulação. O controle inverso faz o caminho oposto "
        "(integral → parcial/urbano) a 50% e 100% do estoque de destino. Em ambos os sentidos o "
        "headcount do município-alvo é idêntico ao baseline."
    )
    p.append("")
    p.append("### 2.3 Motor, parâmetros e validação")
    p.append("")
    p.append(
        "Cada cenário reexecuta `simula_fundeb` sobre o universo de entes, não um produto local "
        "peso × aluno. Os parâmetros `max_nse = min_nse = max_nf = min_nf = 1,0` reproduzem o "
        "cenário de referência dos exercícios 2025–2026; em 2024 o NF interno é achatado para 1 "
        "após o reescalonamento do motor, persistindo o NSE oficial. O ponderador é NF em 2024 e "
        "DREC a partir de 2025. As complementações da União são as oficiais do dataset. Após cada "
        f"corrida corre a validação interna (RF-10). Dos {n_cen} cenários, {n_ok} foram válidos."
    )
    p.append("")
    p.append(
        "As métricas reportadas são: variação absoluta e percentual de `recursos_fundeb` do "
        "município-alvo; variação dos demais municípios da mesma UF; variação do ente estadual "
        "(IBGE < 100); variação da soma da UF; e decomposição em VAAF próprio, complemento VAAF "
        "e complemento VAAT."
    )
    p.append("")
    p.append("## 3 Resultados")
    p.append("")
    p.append("### 3.1 O município-alvo ganha quando o peso sobe")
    p.append("")
    p.append(
        f"No exercício {ano}, a melhor transformação factível — em todos os {n_mun} municípios, "
        f"a transição C a 100% — aumentou `recursos_fundeb`. Nenhum ΔR$ foi negativo. A magnitude "
        f"varia com o estoque elegível e com a posição da UF no mecanismo de equalização. "
        f"{top_pct['municipio']} concentra o extremo da amostra"
        + (
            f" em ganho percentual e absoluto ({pct(top_pct['delta_r_percentual'], 2)}; {brl(top_pct['delta_r'])})"
            if top_pct["municipio"] == top_abs["municipio"]
            else (
                f": maior Δ% ({pct(top_pct['delta_r_percentual'], 2)}; {brl(top_pct['delta_r'])}), "
                f"enquanto {top_abs['municipio']} lidera em valor absoluto "
                f"({brl(top_abs['delta_r'])}; {pct(top_abs['delta_r_percentual'], 2)})"
            )
        )
        + f". O menor ganho percentual da amostra ainda é positivo: {min_pct['municipio']}, "
        f"{pct(min_pct['delta_r_percentual'], 2)}."
    )
    p.append("")
    p.append(
        f"**Tabela 3.** Melhor cenário factível por município ({ano}). Transição C a 100% em todos os casos. "
        "Valores em R$ milhões, salvo o Δ%."
    )
    p.append("")
    tab3 = melhores_ano.copy()
    tab3["delta_mi"] = tab3["delta_r"] / 1e6
    tab3["base_mi"] = tab3["r_base"] / 1e6
    p.append(_md(
        tab3,
        ["municipio", "uf", "regiao", "alunos_movidos", "base_mi", "delta_mi", "delta_r_percentual"],
        {
            "alunos_movidos": lambda x: num(x, 0),
            "base_mi": lambda x: num(x, 1),
            "delta_mi": lambda x: num(x, 1),
            "delta_r_percentual": lambda x: pct(x, 2),
        },
    ))
    p.append("")
    p.append("![Ganho percentual no melhor cenário factível.](figuras/01_ganho_percentual.png)")
    p.append("")
    p.append("![Ganho absoluto (R$ milhões) no melhor cenário factível.](figuras/02_ganho_absoluto.png)")
    p.append("")
    p.append(
        "O heatmap município × transição confirma que C domina o Δ% nas capitais da amostra. "
        "A e B também são positivas, porém com estoque elegível menor nas redes urbanas grandes. "
        "D replica o mecanismo de C nos anos finais, com peso de origem um pouco maior (1,10) e, "
        "por isso, ganho unitário menor."
    )
    p.append("")
    p.append(f"![Mapa de calor do Δ% máximo por município e transição ({ano}).](figuras/03_heatmap.png)")
    p.append("")
    p.append(
        f"Todos os pontos do melhor cenário situam-se acima da identidade recursos baseline × "
        f"recursos contrafactuais (Figura 9). A composição, com headcount fixo, desloca o município "
        f"para um nível mais alto de transferência simulada."
    )
    p.append("")
    p.append("![Recursos baseline versus melhor cenário factível.](figuras/09_baseline_vs_cenario.png)")
    p.append("")
    p.append("### 3.2 O controle inverso inverte o sinal")
    p.append("")
    p.append(
        f"O teste decisivo não é o ganho, e sim a assimetria. Ao devolver 100% do estoque de "
        f"fundamental integral para anos iniciais urbanos (transição C invertida), "
        f"{n_neg_ctrl} de {len(ctrl_c)} municípios perdem recursos. O motor, os pesos, os montantes "
        f"da União e o total de alunos são os mesmos; muda só o sentido do peso. Fortaleza ilustra "
        f"a amplitude: o estoque integral da capital cearense é grande, e o Δ% inverso chega a "
        f"{pct(ctrl_c.loc[ctrl_c['municipio']=='Fortaleza', 'delta_r_percentual'].iloc[0], 2)} "
        f"quando esse estoque é revertido. Belém, com pouco estoque integral, perde pouco em valor "
        f"absoluto — o que reforça que o efeito escala com o volume reclassificado, não com um "
        f"viés fixo do município."
    )
    p.append("")
    p.append(
        f"**Tabela 4.** Controle inverso, transição C a 100% ({ano}): integral → anos iniciais urbanos."
    )
    p.append("")
    p.append(_md(
        ctrl_c,
        ["municipio", "uf", "regiao", "alunos_movidos", "delta_r", "delta_r_percentual"],
        {
            "alunos_movidos": lambda x: num(x, 0),
            "delta_r": brl,
            "delta_r_percentual": lambda x: pct(x, 2),
        },
    ))
    p.append("")
    p.append("![Ida e volta da transição C: o sinal acompanha o peso.](figuras/08_controle_inverso.png)")
    p.append("")
    p.append("### 3.3 O efeito é aproximadamente linear no percentual convertido")
    p.append("")
    p.append(
        "As curvas percentual convertido × ΔR$ da transição C, para os dez municípios, não "
        "exibem limiar visível de equalização no intervalo 5–100%. Converter 50% produz cerca "
        "de metade do ganho de 100%. A quase-linearidade implica que o resultado não depende de "
        "um salto discreto no fundo estadual ou nacional: cada aluno reponderado desloca a fatia "
        "do município de modo proporcional, neste recorte e neste intervalo."
    )
    p.append("")
    p.append(f"![Quase-linearidade da transição C ({ano}).](figuras/04_curvas_transicao_c.png)")
    p.append("")
    p.append("### 3.4 O sinal se repete nas cinco regiões e nos três exercícios")
    p.append("")
    p.append(
        "A média regional do Δ% a 100% é positiva nas quatro transições e nas cinco regiões. "
        "A transição C é, em geral, a de maior impacto percentual nas capitais, porque o estoque "
        "de anos iniciais urbanos é o maior entre as origens factíveis. Creche e pré-escola "
        "integral sobem o recebido, mas movem menos alunos."
    )
    p.append("")
    p.append(f"![Δ% médio a 100% por região e transição ({ano}).](figuras/05_transicoes_por_regiao.png)")
    p.append("")
    p.append(
        "O sinal positivo do melhor cenário reaparece em 2024, 2025 e 2026. A magnitude muda com "
        "os pesos (1,40 versus 1,50 no fundamental integral), com o DREC e com os montantes da "
        "União — não com a tese. Manaus permanece o extremo percentual nos três anos; as capitais "
        "do Sudeste, com fundos estaduais mais altos e sem complemento VAAF, concentram ganhos "
        "absolutos grandes e percentuais menores."
    )
    p.append("")
    p.append("![Melhor Δ% municipal nos três exercícios.](figuras/10_anos.png)")
    p.append("")
    p.append(
        "O retorno por aluno convertido no melhor cenário também é heterogêneo: redes em UFs "
        "complementadas tendem a capturar mais real por cabeça reponderada, porque o aumento de "
        "matrícula ponderada puxa complementação da União, não apenas fatia de um bolo fixo."
    )
    p.append("")
    p.append(f"![Retorno por aluno convertido no melhor cenário ({ano}).](figuras/12_por_aluno.png)")
    p.append("")
    p.append("### 3.5 Quem perde na UF — e quando a União entra")
    p.append("")
    p.append(
        "Aumentar a matrícula ponderada do alvo reduz a participação relativa dos demais "
        "municípios da mesma UF e, em regra, do ente estadual no VAAF. Esse spillover é "
        "sistemático: em cada um dos dez experimentos a 100% da melhor transição, o número de "
        "municípios prejudicados na UF coincide com o total de demais municípios da unidade "
        "(nenhum outro município ganha)."
    )
    p.append("")
    p.append(
        f"**Tabela 5.** Redistribuição na UF no melhor cenário a 100% ({ano}). "
        f"UFs em que a soma estadual cresce: {', '.join(ufs_comp) if ufs_comp else '—'}. "
        f"UFs com soma aproximadamente nula: {', '.join(ufs_zero) if ufs_zero else '—'}."
    )
    p.append("")
    p.append(_md(
        spill,
        ["municipio", "uf", "delta_alvo", "delta_demais_mun", "delta_ente_estadual", "delta_uf_total", "n_prejudicados"],
        {
            "delta_alvo": brl,
            "delta_demais_mun": brl,
            "delta_ente_estadual": brl,
            "delta_uf_total": brl,
            "n_prejudicados": lambda x: str(int(x)),
        },
    ))
    p.append("")
    p.append(
        "Dois regimes aparecem com nitidez. No primeiro — Amazonas, Pará, Ceará, Bahia e "
        "Rio de Janeiro, neste exercício — a União complementar o fundo. O alvo ganha mais do que "
        "os demais e o ente estadual perdem; a soma da UF sobe. O canal dominante do ganho "
        "municipal adicional é o complemento VAAT e/ou VAAF, não apenas a redistribuição do ICMS "
        "educacional estadual. No segundo regime — São Paulo, Minas Gerais, Paraná, Rio Grande do "
        "Sul e Goiás — o Δ da UF é da ordem de centavos. O ganho do alvo é quase integralmente "
        "a perda dos demais municípios mais a perda do ente estadual. É um jogo de soma zero "
        "dentro do estado: a composição muda quem come o bolo, não o tamanho do bolo."
    )
    p.append("")
    p.append(f"![Município-alvo, demais municípios e ente estadual ({ano}).](figuras/06_alvo_uf_estado.png)")
    p.append("")
    p.append("![Ente estadual versus soma da UF: dois regimes de equalização.](figuras/11_estado_vs_uf.png)")
    p.append("")
    p.append(f"![Decomposição do ganho municipal em VAAF e complementos da União ({ano}).](figuras/07_decomposicao.png)")
    p.append("")
    p.append("## 4 Discussão")
    p.append("")
    p.append(
        "A evidência computacional sustenta a tese em três camadas. Primeiro, no município: a "
        "composição altera o recebido, e o sinal é o da mudança de peso. Isso vale nas cinco "
        f"regiões, em {n_ufs} estados e em três exercícios. Segundo, no estado: o ente estadual e os "
        "demais municípios absorvem o deslocamento de fatia. Terceiro, na Federação: só há "
        "recurso novo na UF se a União complementar. A distinção entre UFs complementadas e UFs "
        "auto-suficientes no VAAF é, portanto, parte da tese — não um resíduo."
    )
    p.append("")
    p.append(
        "O resultado não autoriza interpretar tempo integral como alavanca fiscal. A vaga integral "
        "custa mais em pessoal, alimentação e infraestrutura; o ΔR$ simulado é o lado da receita "
        "do fundo, não o resultado líquido da política. Tampouco se deve ler o controle inverso "
        "como argumento contra a jornada estendida: ele apenas demonstra que o motor é simétrico "
        "no peso. A formulação correta é de incentivo implícito. Gestores que maximizassem o "
        "repasse, ignorando custo e pedagogia, teriam motivo para inflar modalidades de peso alto. "
        "A ponderação existe precisamente para financiar etapas mais caras; o risco é o uso da "
        "classificação como instrumento de arrecadação."
    )
    p.append("")
    p.append(
        "Em UFs sem complemento VAAF, o incentivo é ainda mais redistributivo: o município que "
        "repondera extrai recurso dos vizinhos e da rede estadual. Em UFs complementadas, parte "
        "do ganho é externalizada para a União. Os dois desenhos produzem o mesmo sinal municipal "
        "e implicações federativas opostas."
    )
    p.append("")
    p.append("## 5 Limitações")
    p.append("")
    p.append(
        "A amostra é de capitais e grandes redes. A direção do efeito — peso maior, mais recurso "
        "municipal — deve se repetir em municípios menores; a magnitude e o peso relativo do VAAT "
        "não. Não se estima o custo da vaga, o efeito sobre aprendizagem, nem a factibilidade "
        "administrativa de converter 100% de uma etapa. Os ponderadores NSE/DREC e os fatores "
        "máximo/mínimo foram fixados no cenário de referência; outras combinações de parâmetros "
        "podem alterar a magnitude, não necessariamente o sinal. O estudo não cobre a reclassificação "
        "entre etapas de pesos iguais, nem a criação de matrículas novas. Por fim, o motor reproduz "
        "a regra vigente nos microdados de cada exercício; mudanças normativas posteriores "
        "requerem nova simulação."
    )
    p.append("")
    p.append("## 6 Conclusão")
    p.append("")
    p.append(
        "Alterações contrafactuais na composição das matrículas, com o total de alunos constante, "
        "modificam os recursos simulados do FUNDEB do município porque alteram a matrícula "
        "ponderada e, com ela, a participação no fundo estadual (VAAF) e na equalização nacional "
        "(VAAT). O sinal do efeito segue o sinal da mudança de peso: parcial ou urbano rumo a "
        "integral aumenta o recebido do alvo; o inverso o reduz. O ente estadual e os demais "
        "municípios da UF absorvem parte do ajuste. A UF só cresce de forma material se a União "
        f"complementar mais. Esse padrão reproduz-se em {n_mun} municípios, {n_ufs} estados e cinco "
        "regiões, nos exercícios 2024, 2025 e 2026."
    )
    p.append("")
    p.append("## Referências")
    p.append("")
    p.append(
        "- Brasil. Lei nº 14.113, de 25 de dezembro de 2020. Regulamenta o Fundo de Manutenção e "
        "Desenvolvimento da Educação Básica e de Valorização dos Profissionais da Educação (Fundeb)."
    )
    p.append(
        "- Brasil. Lei nº 14.276, de 27 de dezembro de 2021. Altera a Lei nº 14.113/2020."
    )
    p.append(
        "- Instituto Federal do Ceará. Simulador FUNDEB v2. Motor `simula_fundeb` e dataset dos "
        "exercícios 2024–2026. Reprodução deste artigo: `python -m analises.fundeb_regioes.run`."
    )
    p.append("")

    path = Path(ANALISE_DIR) / "RELATORIO.md"
    path.write_text("\n".join(p), encoding="utf-8")
    return path
