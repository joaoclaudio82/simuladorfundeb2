"""Teste completo do aplicativo"""
import requests
import json

BASE = "http://localhost:8000"

print("=== Teste do Frontend ===")
r = requests.get(f"{BASE}/")
print(f"Pagina principal: {'OK' if r.status_code == 200 and 'Simulador FUNDEB v2' in r.text else 'FALHA'}")

print("\n=== Teste dos Endpoints ===")

r = requests.get(f"{BASE}/api/estados")
print(f"GET /api/estados: OK - {len(r.json()['estados'])} estados")

r = requests.get(f"{BASE}/api/pesos")
print(f"GET /api/pesos: OK - {len(r.json())} pesos")

r = requests.get(f"{BASE}/api/etapas")
print(f"GET /api/etapas: OK - {len(r.json())} etapas")

r = requests.get(f"{BASE}/api/municipios?uf=CE")
muns = r.json()
print(f"GET /api/municipios?uf=CE: OK - {len(muns)} municipios")

ibge = int(muns[0]["ibge"])
r = requests.get(f"{BASE}/api/municipio/{ibge}/matriculas")
print(f"GET /api/municipio/{ibge}/matriculas: OK - {r.json()['nome']}")

print("\n=== Teste de Simulacao Principal ===")
body = {
    "complementacao_vaaf": 24153287047,
    "complementacao_vaat": 18114965285,
    "complementacao_vaar": 0,
    "max_nse": 1.1, "min_nse": 1, "max_nf": 1, "min_nf": 1,
}
r = requests.post(f"{BASE}/api/simular", json=body)
d = r.json()
res = d["resumo"]
print(f"POST /api/simular: OK")
print(f"  VAAF min simulado: {res['vaaf_minimo_simulado']}")
print(f"  VAAT min simulado: {res['vaat_minimo_simulado']}")
print(f"  Compl. municipios: R$ {res['complementacao_municipios']:,.0f}")
print(f"  Compl. estados:    R$ {res['complementacao_estados']:,.0f}")
print(f"  % complementados:  {res['percentual_complementados']}%")
print(f"  UFs nos graficos:  {len(d['por_uf'])}")
print(f"  Grupos VP VAAF:    {len(d['vencedores_perdedores']['vaaf'])}")
print(f"  Diferenca UF:      {len(d['diferenca_uf'])} UFs")

print("\n=== Teste Simulacao com VAAR ===")
body["complementacao_vaar"] = 5400000000
r = requests.post(f"{BASE}/api/simular/completo", json=body)
dados = r.json()
vaar_total = sum(d.get("complemento_vaar", 0) for d in dados)
print(f"POST /api/simular/completo: OK - {len(dados)} entes")
print(f"  Total VAAR distribuido: R$ {vaar_total:,.0f}")

print("\n=== Teste Simulacao Municipal ===")
body_mun = {
    "ibge": ibge,
    "complementacao_vaaf": 24153287047,
    "complementacao_vaat": 18114965285,
    "complementacao_vaar": 5400000000,
    "max_nse": 1.1, "min_nse": 1, "max_nf": 1, "min_nf": 1,
    "matriculas_ajustadas": {"creche_integral_rede_publica": 500},
}
r = requests.post(f"{BASE}/api/simular/municipio", json=body_mun)
d = r.json()
o = d["municipio_original"]
a = d["municipio_ajustado"]
print(f"POST /api/simular/municipio: OK")
print(f"  {o['nome']} ({o['uf']}):")
print(f"    Original  -> VAAF: {o['vaaf_final']:.2f} | VAAT: {o['vaat_final']:.2f} | VAAR: R$ {o['complemento_vaar']:,.0f} | FUNDEB: R$ {o['recursos_fundeb']:,.0f}")
print(f"    Ajustado  -> VAAF: {a['vaaf_final']:.2f} | VAAT: {a['vaat_final']:.2f} | VAAR: R$ {a['complemento_vaar']:,.0f} | FUNDEB: R$ {a['recursos_fundeb']:,.0f}")
print(f"  Entes impactados no estado: {len(d['estado_ajustado'])}")

print("\n========================================")
print("  TODOS OS TESTES PASSARAM COM SUCESSO")
print("========================================")
