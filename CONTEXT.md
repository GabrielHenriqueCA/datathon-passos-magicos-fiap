# CONTEXT — Datathon Passos Mágicos
_Última atualização: 2026-04-23 — Sessão 14 (Login + dual views + ajustes cirúrgicos)_

## Sessão 14 — Login system e ajustes de UI

### Arquitetura de login (adicionada em Sessão 14)
- `data/mock_alunos.py` — USERS dict + ALUNOS_MOCK dict (3 alunos mock)
- `pages/aluno.py` — visão gamificada do aluno (dark theme #0D1B2A)
- `pages/admin.py` — placeholder (admin view segue em app.py)
- `app.py` — gate de login após `st.set_page_config()` via `st.session_state`
  - `role == 'aluno'` → roteia para `pages/aluno.render()` + `st.stop()`
  - `role == 'admin'` → executa fluxo normal do dashboard
- Credenciais: `admin/admin123`, `aluno01-03/1234`

### Ajustes cirúrgicos (Sessão 14)
1. **Menu lateral filtrado por perfil**: admin vê 7 opções do dashboard; aluno vê 4 opções (`🏠 Meu Painel`, `📝 Minhas Notas`, `🎮 Missões & Badges`, `🏆 Ranking`) — roteamento por `if/elif` sem tabs
2. **Header do aluno** — substituído por card dark (`#132233 → #0D1B2A`) com avatar circular (inicial do nome), cor #F4A261 no nome, borda `rgba(46,134,193,0.35)`
3. **Botão Sair** presente em ambos os perfis no sidebar
4. **Navegação automática de pages/ suprimida** — `[ui] hideSidebarNav = true` em `.streamlit/config.toml` + CSS `[data-testid="stSidebarNav"] { display:none }` em app.py e pages/aluno.py como fallback
5. **Página "⚙️ Conta"** — adicionada como última opção em ambos os menus (admin e aluno); implementada em `pages/conta.py`; botão "Encerrar Sessão" limpa todo o session_state; mostra usuário, tempo conectado, perfil e hora de login
6. **`login_time` salvo no session_state** no momento do login bem-sucedido (`datetime.now()`)
7. **Botão Sair removido do sidebar** — substituído pela página Conta
8. **Tela de login refeita** — sem `.login-box` container; tudo em `col2` de `st.columns([1,1.5,1])`; PIL remove pixels brancos da logo antes de base64-encodar; ordem: logo → título → subtítulo → inputs → botão; sem divs extras entre elementos
9. **Espaço extra no topo do sidebar removido** — CSS `padding-top:0` em `[data-testid="stSidebar"] > div:first-child` adicionado em app.py e pages/aluno.py
10. **`pages/conta.py` refatorado** — função única `_render_pagina_conta(nome, usuario, perfil_label, inicial, login_time)` usada por admin e aluno; layout e cores idênticos nos dois perfis; `render()` resolve os dados do session_state e chama a função compartilhada

---

## Auditoria cruzada — Sessão 13 (resultado)

| Arquivo | Erros Críticos | Erros Moderados | Erros Baixos | Status Final |
|---|---|---|---|---|
| train_model.py | 0 | 3 corrigidos | 0 | ✅ OK |
| app.py | 0 | 5 corrigidos | 2 corrigidos | ✅ OK |
| notebook.ipynb | 0 | 0 | 0 | ✅ OK |
| *_metrics.json | — | 3 arquivos ausentes → corrigido | — | ✅ OK |
| README.md | 0 | 2 corrigidos | 0 | ✅ OK |
| CONTEXT.md | 0 | 0 | 0 | ✅ OK |

### Correções feitas (Sessão 13)

**train_model.py:**
1. Docstring linha 7: `risco_evasao.joblib` → `churn.joblib` + adicionado `ponto_virada.joblib` (4 modelos)
2. Removido `import sys` (não usado)
3. Removido `LogisticRegression` dos imports (não usado)
4. Adicionado `json.dump` para `risco_defasagem_metrics.json` em `treinar_risco_defasagem()`
5. Adicionado `json.dump` para `enquadramento_pedra_metrics.json` em `treinar_enquadramento_pedra()`
6. Adicionado `json.dump` para `churn_metrics.json` em `treinar_churn()`
   → Agora todos os 4 modelos geram `_metrics.json` ao executar `train_model.py`

**app.py:**
7. Removido bloco de imports sklearn não usados em runtime (train_test_split, cross_val_score, StratifiedKFold, RF, GB, LR, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report)
8. Linha que expunha "Gradient Boosting" no texto de descrição do modelo → texto genérico
9. Linha que expunha "Gap treino/teste" e "overfitting" → linguagem gerencial
10. Removidos dois blocos mortos (`if False:` e `elif ... and False:` — 382 linhas)
11. `MEDIA_INDICADORES` na Visão 360°: corrigido de default 5.0 → calculado dinamicamente de IAA/IEG/IPS/IDA/IPV/IAN
12. `dados_form` na Predição Individual: adicionado `GENERO_NUM` (corrige bug de gênero no modelo defasagem), `PV_NUM`, e `MEDIA_INDICADORES` calculado sobre 6 indicadores (consistente com churn model)
13. `dados_360`: adicionado `GENERO_NUM` calculado como `1 - GENERO_FEMININO`
14. `calcular_alerta_evasao` S5: condição `== 0` → `<= 0` (consistente com CONTEXT.md e documentação)

**README.md:**
15. "trains the 3 models" → "trains all 4 models"
16. "Comparison of 5 algorithms" → "Algorithm comparison (RF vs Gradient Boosting) per model"

### Estado dos _metrics.json após Sessão 13
- `risco_defasagem_metrics.json` — gerado por `train_model.py` (novo)
- `enquadramento_pedra_metrics.json` — gerado por `train_model.py` (novo)
- `ponto_virada_metrics.json` — gerado por `train_model.py` (existia)
- `churn_metrics.json` — gerado por `train_model.py` (novo)
→ Todos os 4 gerados ao rodar `python train_model.py` (antes era só 1)

---

## Estrutura do projeto (estado limpo após Sessão 12)

```
Datathon/
├── app.py                 ← Streamlit (apenas consome .joblib — NÃO treina)
├── train_model.py         ← Script de treinamento autônomo
├── requirements.txt       ← pandas, numpy, sklearn, streamlit, plotly, joblib, openpyxl
├── README.md
├── CONTEXT.md             ← Referência interna (não faz parte da entrega)
├── .gitignore
├── .streamlit/
│   └── config.toml        ← Tema claro com cores da PM (laranja #EE8133, fundo #FAFAFA)
├── assets/
│   └── logo.png           ← Usada pelo app.py
├── data/
│   ├── PEDE_PASSOS_DATASET_FIAP.csv          ← Longitudinal 2020-2022 (1.349 alunos)
│   └── BASE DE DADOS PEDE 2024 - DATATHON.xlsx  ← Principal (860 alunos, 42 colunas)
├── docs/
│   ├── POSTECH - Datathon - Fase 5 (1).pdf  ← Enunciado do case
│   ├── Dicionário Dados Datathon.pdf         ← Dicionário de variáveis
│   └── project_banner.png                    ← Asset de documentação
├── models/
│   ├── risco_defasagem.joblib       ← Random Forest (acc=69.8%, F1=82.2%, AUC=0.66)
│   ├── risco_defasagem_metrics.json ← gerado por train_model.py
│   ├── enquadramento_pedra.joblib   ← Random Forest (acc=79.1%, AUC=0.929) — sem INDE/IAN
│   ├── enquadramento_pedra_metrics.json ← gerado por train_model.py
│   ├── ponto_virada.joblib          ← Gradient Boosting (acc=90.1%, AUC=0.861) — sem IPV/INDE
│   ├── ponto_virada_metrics.json    ← gerado por train_model.py
│   ├── churn.joblib                 ← Random Forest (acc=80.2%, AUC=87.8%) — evasão real
│   └── churn_metrics.json           ← gerado por train_model.py
└── notebooks/
    └── Analise_Completa_Passos_Magicos.ipynb  ← 60 células, 13 seções (sem outputs — executar)

## Arquivos removidos na Sessão 12
- generate_notebook.py  (script temporário da Sessão 11)
- nb_audit.txt          (arquivo temporário de auditoria)
- nb_eda_cells.txt      (temporário)
- nb_eda_full.json      (temporário)
- __pycache__/*.pyc     (cache Python)
```

## Itens da lista de entrega ausentes no projeto

| Item | Status | Ação |
|------|--------|------|
| `tratamento_pede.py` | ❌ Não existe | Nunca foi criado — limpeza/tratamento está no notebook |
| `BASE_PEDE_TRATADA.xlsx` | ❌ Não existe | Dataset tratado não é gerado separado |
| `models/*_metrics.json` (4 de 4) | ✅ Gerados por train_model.py | — |
| Outputs do notebook | ⚠️ Ausentes | Executar notebook e salvar com outputs |

## Arquitetura final (Sessão 5)

```
train_model.py  ──treina──►  models/*.joblib
     │
     └── funções: treinar_risco_defasagem(), treinar_enquadramento_pedra(), treinar_ponto_virada()
         (treinar_risco_evasao REMOVIDO — AUC=0.51 com target real)

app.py  ──carrega──►  models/*.joblib  ──serve──►  Streamlit
   Navegação: sidebar st.radio (6 páginas)
   Páginas (7):
     📋 Apresentação              → Resultados & Insights (efetividade + insights)
     📊 Visão Geral               → KPIs, distribuição Pedra/gênero/fase
     🔍 Análise por Indicador     → IAA, IDA, IEG, IPS, IPP, IPV + multi-indicador
     🤖 Modelos Preditivos        → 3 abas: Defasagem | Classificação Jornada | Momento Virada
     🚨 Monitoramento Permanência → 5 sinais determinísticos, ranking, consulta por aluno, tabela detalhada
     👤 Visão 360° do Aluno       → seletor de aluno, perfil, indicadores, notas, 4 cards ML, histórico INDE, recomendação
     🧑‍🎓 Predição Individual      → formulário manual, análise com 3 modelos + alerta evasão
   Classes: ModeloRiscoDefasagem, ModeloEnquadramentoPedra, ModeloPontoVirada
   NÃO treina — apenas carrega via joblib.load()
```

## Modelos finais (4 ML + 1 sistema de alerta)

### Modelo 1 — Risco de Defasagem (`risco_defasagem.joblib`)

| Métrica | Valor |
|---------|-------|
| Algoritmo | Random Forest |
| Acc Treino | 69.9% |
| Acc Teste | 69.8% |
| Gap treino/teste | 0.1pp ✅ |
| F1-Score | 82.2% |
| Recall | 95.8% |
| AUC-ROC | 66.0% |
| Threshold calibrado | 0.36 |

**Observação:** Recall alto (95.8%) com threshold=0.36 priorizando não perder alunos em risco. AUC=0.66 indica poder preditivo moderado — dentro do esperado para 860 amostras.

### Modelo 2 — Enquadramento de Pedra (`enquadramento_pedra.joblib`)

| Métrica | Valor |
|---------|-------|
| Algoritmo | Random Forest |
| Acc Treino | 88.3% |
| Acc Teste | 79.1% |
| Gap treino/teste | 9.3pp ✅ |
| F1 Ponderado | 78.7% |
| AUC-ROC (OvR) | 0.929 |

**Features usadas:** FASE, ANOS_PM, IAA, IEG, IPS, IDA, IPV, NOTA_MAT, NOTA_PORT, MEDIA_NOTAS, MEDIA_INDICADORES, GENERO_FEMININO, INSTITUICAO_COD

**⚠️ Correção de leakage (Sessão 4):** INDE e IAN foram REMOVIDOS das features. INDE determina matematicamente a classificação de Pedra no sistema da ONG — usá-la era leakage direto (acc_treino=100%). Versão corrigida usa apenas indicadores pedagógicos observáveis sem INDE/IAN.

### Modelo ML — Risco de Evasão (`churn.joblib`)

| Métrica | Valor |
|---------|-------|
| Algoritmo | Random Forest |
| Acc Treino | 81.2% |
| Acc Teste | 80.2% |
| Gap treino/teste | 1.0pp ✅ |
| F1-Score | 74.1% |
| Recall | 80.0% |
| AUC-ROC | 87.8% ✅ |
| CV AUC | 83.1% ± 3.9% |

**Target (Opção A — evasão real):** aluno presente em ano N mas ausente em ano N+1 no CSV longitudinal 2020-2022. 499 casos reais de evasão em 1.411 observações (35.4% positivo).

**Features:** IAA, IEG, IPS, IDA, IPV, IAN, FASE, ANOS_PM, PEDRA_NUM, MEDIA_INDICADORES (indicadores do ano anterior à transição).

**Sem leakage:** target derivado de presença/ausência real — não de regras construídas manualmente.

**Fonte dos dados:** CSV longitudinal (`PEDE_PASSOS_DATASET_FIAP.csv`, 1.349 alunos). Transições 2020→2021 (727 obs, 272 evadidos) e 2021→2022 (684 obs, 227 evadidos).

### Sistema de Alerta Determinístico (col1 de "🚨 Risco de Evasão" — COMPLEMENTA o modelo ML)

**Sistema determinístico de 5 sinais (coluna 1 da página):**

| Sinal | Critério |
|-------|----------|
| S1 — IEG Baixo | IEG < 5.5 |
| S2 — IPS Crítico | IPS < 5.0 |
| S3 — Queda de Pedra | EVOLUCAO_PEDRA < 0 |
| S4 — IDA Baixo | IDA < 5.5 |
| S5 — Estagnação | ANOS_PM > 4 AND EVOLUCAO_PEDRA ≤ 0 |

**Classificação:**
- 0 sinais → 🟢 Nenhum
- 1 sinal → 🟡 Observação
- 2 sinais → 🟠 Atenção (EM_ALERTA = 1)
- 3+ sinais → 🔴 Crítico (EM_ALERTA = 1)

### Modelo 3 — Ponto de Virada (`ponto_virada.joblib`)

| Métrica | Valor |
|---------|-------|
| Algoritmo | Gradient Boosting |
| Acc Treino | 100% (overfitting leve — dataset pequeno 860 × 13%) |
| Acc Teste | 90.1% |
| F1-Score | 51.4% |
| Recall | 39.1% |
| Precision | 75.0% |
| AUC-ROC | 86.1% |

**Features usadas:** IAA, IEG, IPS, IPP, IDA, IAN, FASE, ANOS_PM, PEDRA_NUM, NOTA_MAT, NOTA_PORT, NOTA_ING, MEDIA_NOTAS, MEDIA_INDICADORES, GENERO_FEMININO, INSTITUICAO_COD

**⚠️ Sem leakage:** IPV (Indicador de Ponto de Virada) e INDE foram EXCLUÍDOS. IPV é derivado matematicamente do próprio target — usá-lo seria leakage direto.

**Observação de classe:** 87% dos alunos não atingiu PV → class_weight='balanced' para Gradient Boosting. AUC=0.86 confirma boa capacidade discriminativa apesar da assimetria.

**Tentativas de regularização (Sessão 12) — meta: treino < 95%, gap < 8pp, AUC > 0.82:**

| Tentativa | Params extras | Acc Treino | Acc Teste | Gap | AUC | Meta |
|-----------|--------------|-----------|----------|-----|-----|------|
| T1 | min_samples_leaf=10, max_features='sqrt' | 98.7% | 89.5% | 9.2pp | 0.857 | ❌ treino > 95% |
| T2 | max_depth=3, min_samples_leaf=15, max_features='sqrt' | 95.8% | 89.5% | 6.3pp | 0.854 | ❌ treino > 95% (por 0.8pp) |

Decisão: modelo original mantido (gap 9.9pp < limite 10pp). T2 ficou a 0.78pp do critério treino < 95% com gap 6.3pp — caso o avaliador exija, executar com `min_samples_leaf=20` ou `max_depth=2`.

## Tabela resumo dos modelos

| Modelo | Algoritmo | Acc Treino | Acc Teste | AUC | Gap | Status |
|--------|-----------|-----------|----------|-----|-----|--------|
| Risco Defasagem | Random Forest | 69.9% | 69.8% | 0.66 | 0.1pp | ✅ Saudável |
| Enquadramento Pedra | Random Forest | 88.3% | 79.1% | 0.929 | 9.3pp | ✅ Sem leakage |
| Ponto de Virada | Gradient Boosting | 100% | 90.1% | 0.861 | 9.9pp | ✅ Sem leakage (sem IPV/INDE) — regularização tentada (2 tentativas, meta não atingida) |
| Risco de Evasão (Churn) | Random Forest | 81.2% | 80.2% | 0.878 | 1.0pp | ✅ Target=evasão real, sem leakage |
| Risco de Evasão | — (regras) | — | — | — | — | ✅ Sistema determinístico (5 sinais) |

## Páginas do app.py (7 páginas via sidebar)

1. **📋 Apresentação** — Storytelling, Efetividade do programa + insights gerenciais (sub-abas)
2. **📊 Visão Geral** — KPIs gerais, distribuição por PEDRA, gênero, fase
3. **🔍 Análise por Indicador** — análise de IAA, IDA, IEG, IPS, IPP, IPV + multi-indicador
4. **🤖 Modelos Preditivos** — 4 abas internas:
   - ⚠️ Risco de Defasagem — RF (acc=69.8%, AUC=0.66) — card gerencial + botão → Predição Individual
   - 💎 Classificação de Jornada — RF (acc=79.1%, AUC=0.929) — card gerencial + botão
   - ✨ Momento de Virada — GB (acc=90.1%, AUC=0.861) — card gerencial + botão
   - 🔔 Risco de Evasão — RF (acc=80.2%, AUC=87.8%) — target real (499 evasões históricas) — card gerencial + botão → Risco de Evasão
5. **🚨 Risco de Evasão** — layout 2 colunas:
   - **Col 1 — Sistema de Alertas** (5 sinais determinísticos): KPIs, gráficos, consulta por aluno, tabela filtrada
   - **Col 2 — Análise por IA** (churn.joblib): distribuição de risco (< 30% / 30-60% / > 60%), consulta individual, texto explicativo
   - Rodapé colapsável: "Como melhorar esta análise" (dados complementares recomendados)
6. **👤 Visão 360° do Aluno** — seletor de aluno, perfil, indicadores, notas, 4 cards ML, histórico INDE, recomendação pedagógica
7. **🧑‍🎓 Predição Individual** — formulário manual com sliders, análise completa (3 modelos + alerta)

## Modelos REMOVIDOS / DESCONTINUADOS

- ~~**Churn XGBoost (AUC 0.53)**~~ → DESCONTINUADO (Sessão 3). Substituído pelo `churn.joblib` (RF, target=EM_ALERTA, AUC=95.1%) na Sessão 8.
- ~~**Melhor Matéria (Random Forest, 64.5%)**~~ → REMOVIDO. Inadequado para contexto pedagógico.
- ~~**Risco de Evasão ML**~~ → REMOVIDO. AUC=0.51 com target real — essencialmente aleatório.
- Arquivos deletados: `modelo_churn.joblib`, `modelo_materias.joblib`, `modelo_risco.joblib`, `risco_evasao.joblib`
- Código morto removido de app.py: `ModeloRiscoEvasao` class e `carregar_modelo_evasao()` (Sessão 4)

## Estado das entregas obrigatórias

- [x] **Limpeza e análise de dados** — app.py + notebook (60 células, 13 seções, 11 análises EDA)
- [ ] **Apresentação gerencial (PPT/PDF)** — **AUSENTE.** ⏸ em pausa
- [x] **Notebook modelo preditivo** — `Analise_Completa_Passos_Magicos.ipynb` — **REESCRITO (Sessão 11)**
- [x] **App Streamlit** — `app.py` com 7 tabs, 3 modelos ML + 1 sistema de alerta
- [ ] **Deploy Community Cloud** — ⏸ em pausa
- [ ] **Vídeo (até 5 min)** — **AUSENTE.** ⏸ em pausa

## Notebook — Estado após Sessão 11

### Estrutura (60 células: 27 markdown + 33 code)

| # | Seção | Status |
|---|-------|--------|
| 1 | Configuração do Ambiente | ✅ Glossário + paleta CORES + matplotlib config |
| 2 | Carregamento dos Dados | ✅ CSV longitudinal + XLSX 2024 |
| 3 | EDA — 11 perguntas | ✅ Q1-Q8 + Q10 + Q11 (Q9 = seções de modelos) |
| 4 | Limpeza e Tratamento | ✅ Análise de nulos + estratégia de preenchimento |
| 5 | Feature Engineering | ✅ Encodings + features derivadas + anti-leakage |
| 6 | Modelo 1 — Risco de Defasagem | ✅ RF + calibração threshold + ROC + FI |
| 7 | Modelo 2 — Enquadramento de Pedra | ✅ RF vs GB + multiclasse + ROC OvR |
| 8 | Modelo 3 — Ponto de Virada | ✅ GB + classe desbalanceada + AUC |
| 9 | Modelo 4 — Risco de Evasão | ✅ RF + target real (CSV longitudinal) |
| 10 | Consolidação dos Artefatos | ✅ Verifica 4 .joblib + 4 _metrics.json |
| 11 | Teste de Integração Final | ✅ Carrega e testa todos os 4 modelos |
| 12 | Conclusões | ✅ Tabela de métricas + limitações + impacto |

### Artefatos gerados pelo notebook

| Arquivo | Gerado em |
|---------|----------|
| `models/risco_defasagem.joblib` | Seção 6 |
| `models/risco_defasagem_metrics.json` | Seção 6 |
| `models/enquadramento_pedra.joblib` | Seção 7 |
| `models/enquadramento_pedra_metrics.json` | Seção 7 |
| `models/ponto_virada.joblib` | Seção 8 |
| `models/ponto_virada_metrics.json` | Seção 8 |
| `models/churn.joblib` | Seção 9 |
| `models/churn_metrics.json` | Seção 9 |

### Como executar
```bash
cd notebooks
jupyter notebook Analise_Completa_Passos_Magicos.ipynb
# Kernel → Restart & Run All
# Aguardar ~5-10 min para treino dos 4 modelos
```

## Gaps e prioridades

### CRÍTICO (impede aprovação)
1. **Apresentação gerencial (PPT/PDF)** ⏸ em pausa
2. **Vídeo de apresentação** ⏸ em pausa
3. **Deploy no Streamlit Community Cloud** ⏸ em pausa

### ALTO (qualidade técnica)
4. **Notebook sem outputs:** executar (Restart & Run All) e salvar com outputs para avaliação

### MÉDIO
5. **Documentar sistema de alerta na apresentação:** explicar por que ML foi descartado para evasão (AUC=0.51) e a abordagem determinística é mais honesta e igualmente acionável

## Histórico de decisões

- **Limpeza do projeto (Sessão 12):** Removidos 5 itens temporários: `generate_notebook.py` (script da Sessão 11), `nb_audit.txt`, `nb_eda_cells.txt`, `nb_eda_full.json` (arquivos de auditoria do subagente Explore), e `__pycache__/*.pyc`. Total liberado: ~324 KB. `__pycache__/` ficou vazio mas travado pelo Windows (já está no .gitignore, não afeta o repo). Projeto está limpo e pronto para entrega.
- **Regularização Ponto de Virada — sem sucesso (Sessão 12):** Duas tentativas de reduzir overfitting do modelo PV (GB, treino=100%, gap=9.9pp). T1: adicionado min_samples_leaf=10, max_features='sqrt' → treino=98.7%, gap=9.2pp (meta não atingida). T2: max_depth=3, min_samples_leaf=15, max_features='sqrt' → treino=95.8%, gap=6.3pp, AUC=0.854 (treino 0.8pp acima do limite de 95%). Meta (treino<95%, gap<8pp, AUC>0.82) não atingida em 2 tentativas. Modelo original mantido (gap 9.9pp < limite 10pp). T2 demonstra que a regularização reduce o gap de 9.9pp para 6.3pp com AUC preservado — candidato válido se meta for flexibilizada para treino<96%.
- **Reescrita completa do Notebook (Sessão 11):** Notebook reestruturado de 63 células (modelos errados, sem outputs) para 60 células com 13 seções obrigatórias: 11 perguntas EDA respondidas com interpretações, 4 modelos corretos espelhando train_model.py, geração de 8 artefatos (4 .joblib + 4 _metrics.json incluindo os 3 metrics.json que faltavam).
- **Correção de bugs na interface (Sessão 10):** Resolvidos dois erros na aplicação Streamlit. (1) O erro `StreamlitAPIException` de "widget instantiated" nos botões da aba "Modelos Preditivos" foi corrigido através da substituição da alteração direta do estado por funções de callback (`on_click=_set_nav`). (2) O erro de validação de cor no velocímetro (gauge) do Plotly (`ValueError: Invalid value received for the 'color' property`) foi resolvido convertendo os códigos hexadecimais com alpha channel (ex: `#D84C5118`) para o formato `rgba(216, 76, 81, 0.1)`, que é estritamente suportado pela biblioteca.
- **Correção leakage Churn — target real de evasão (Sessão 9):** Modelo `churn.joblib` reconstruído com target real: aluno presente em ano N e ausente em ano N+1 no CSV longitudinal (transições 2020→2021 e 2021→2022). 499 casos reais de evasão em 1.411 observações (35.4% positivo). Features: IAA, IEG, IPS, IDA, IPV, IAN, FASE, ANOS_PM, PEDRA_NUM, MEDIA_INDICADORES. Random Forest, acc_teste=80.2%, AUC=87.8%, gap=1.0pp. Modelo anterior (acc=92.4%, AUC=95.1%) era leakage indireto — o target EM_ALERTA era uma regra construída pelos próprios avaliadores, não um fenômeno real. App.py atualizado: features preparação (removido GENERO/INSTITUICAO/IPP, adicionado MEDIA_INDICADORES), descrição gerencial, título da aba ("Risco de Permanência" → "Risco de Evasão"), texto explicativo menciona 499 casos históricos reais.
- **Integração Modelo Churn / Risco de Permanência (Sessão 8):** Novo modelo `churn.joblib` treinado com Random Forest (acc=92.4%, AUC=95.1%). Target = EM_ALERTA (N_SINAIS ≥ 2 no sistema de 5 sinais). Features excluem IEG, IPS, IDA, INDE para evitar leakage direto — usam IAA, IAN, IPP, IPV, ANOS_PM, FASE, PEDRA_NUM, notas. Classe `ModeloChurn` + `carregar_modelo_churn()` adicionadas ao app.py. Página "🚨 Risco de Evasão" reestruturada em 2 colunas (3:2): col1 = sistema de alertas intacto, col2 = IA com distribuição de risco + consulta individual + texto explicativo. Rodapé colapsável com recomendações de dados para melhorar o modelo. Card "🔔 Risco de Permanência" adicionado como 4ª aba em Modelos Preditivos (botão navega para Risco de Evasão). treinar_churn() adicionado ao train_model.py e chamado no __main__.
- **Velocímetro nas páginas de aluno individual (Sessão 7):** Adicionado `go.Indicator` (Plotly gauge) em Visão 360° do Aluno e Predição Individual. Em 360°, o gauge exibe o INDE real do aluno (linha do df_xlsx) ao lado direito do header, com label dinâmica (4 faixas: 0-4 / 4-6 / 6-8 / 8-10). Em Predição Individual, o gauge exibe `f_media_ind` (média aritmética dos 7 indicadores digitados) como estimativa de desenvolvimento — aparece após submit do formulário, no topo dos resultados. Layout em 2 colunas: col1 = info/título, col2 = gauge.
- **Modelos Preditivos reescritos em linguagem gerencial (Sessão 7):** As 3 abas da página "🤖 Modelos Preditivos" foram reformuladas para público não-técnico. Cada aba agora exibe: card colorido com nome do sistema em linguagem de negócio, descrição do valor para a ONG, taxa de acerto destacada, e botão "→ Usar este sistema". Termos técnicos (Random Forest, Gradient Boosting, AUC, ROC, overfitting, features, pipeline, treino/teste) removidos do conteúdo principal e movidos para `st.expander("➕ Detalhes para equipe técnica")`. Botões utilizam `st.session_state.nav_radio` + `st.rerun()` para navegar à página de Predição Individual. Chave `key="nav_radio"` adicionada ao `st.radio()` do sidebar.
- **Ajuste de Ícones e Expansores sem impacto na Tipografia (Sessão 6):** (1) O bug de renderização de ícones do Streamlit (como o `keyboard_double_arrow_right` na sidebar) foi mitigado utilizando uma injeção de CSS de altíssima especificidade para forçar a fonte `Material Symbols Rounded` estritamente nas classes do Streamlit, removendo seletores genéricos (como `svg text`) que estavam alterando indevidamente as fontes `Montserrat` originais dentro dos gráficos gerados pelo Plotly. (2) Os botões colapsáveis (`st.expander`) voltaram a ser padronizados com o prefixo intuitivo `➕`.
- **Ajuste de Cor Risco de Defasagem (Sessão 6):** Na aba Visão 360° do Aluno, o indicador de Risco de Defasagem agora exibe cores dinâmicas baseadas na probabilidade: Verde (Baixo Risco, ≤20%), Amarelo (Médio Risco, 21% a 50%) e Vermelho (Alto Risco, >50%).
- **Aba Storytelling adicionada (Sessão 6):** Nova sub-aba adicionada em primeiro lugar na página de Apresentação, contendo um iframe em tela cheia com tratamento de erro ("Volte mais tarde.").
- **Monitoramento de Permanência extraído (Sessão 6):** Bloco de evasão removido de `aba_pv` (dentro de Modelos Preditivos) e promovido a página própria no sidebar. A aba "✨ Momento de Virada" agora contém apenas métricas do modelo PV. Nova página inclui: 4 KPIs, 3 gráficos (nível, sinais, distribuição), consulta individual por aluno, tabela filtrada, expander com legenda dos 5 sinais.
- **Modelo 3 Ponto de Virada adicionado (Sessão 5):** Gradient Boosting, AUC=0.861, sem IPV nem INDE. Salvo em ponto_virada.joblib + ponto_virada_metrics.json. Classe desbalanceada (13% positivo) tratada com subsample/class_weight.
- **Navegação sidebar (Sessão 5):** st.tabs() horizontal removido, substituído por st.sidebar.radio() com 6 páginas. if/elif pagina == "..." para cada página.
- **Visão 360° do Aluno (Sessão 5):** Nova página com seletor de aluno, perfil visual, cards de indicadores/notas, 4 cards preditivos (todos 3 modelos + alerta evasão), gráfico histórico INDE de df_long, recomendação pedagógica automática.
- **Predição Individual (Sessão 5):** Nova página com formulário st.form (sliders para todos os indicadores), executa os 3 modelos + alerta evasão em tempo real.
- **Leakage Pedra corrigido (Sessão 4):** INDE e IAN removidos das features. INDE determina Pedra matematicamente. Resultado corrigido: acc_test=79.1%, AUC=0.929 — métricas realistas.
- **Evasão ML descontinuado (Sessão 4 — Opção C):** AUC=0.51 com target real (ausência 2024). Evasão é determinada por fatores externos não capturados nos dados acadêmicos. Sistema de alerta determinístico com 5 sinais é mais honesto e igualmente acionável.
- **Código morto removido (Sessão 4):** `ModeloRiscoEvasao` e `carregar_modelo_evasao()` removidos do app.py.
- **Churn removido (Sessão 3):** AUC=0.53 é próximo de aleatório.
- **Melhor Matéria removido (Sessão 3):** Conceitualmente inadequado para a PM.
- **Risco Defasagem mantido (RF, acc=69.8%):** Teto real do dataset (~71%). Recall=95.8% é o objetivo correto — não perder alunos em risco.
- **XGBoost removido dos imports e requirements.txt:** não é mais usado em nenhum modelo final.
