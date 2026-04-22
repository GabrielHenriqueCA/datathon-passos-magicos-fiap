# CONTEXT — Datathon Passos Mágicos
_Última atualização: 2026-04-22 — Sessão 9 (Correção de leakage no modelo Churn — target real de evasão via CSV longitudinal)_

## Estrutura do projeto

```
Datathon/
├── app.py                 ← Streamlit (apenas consome .joblib — NÃO treina) — 3335 linhas
├── train_model.py         ← Script de treinamento autônomo (sem imports de app.py)
├── requirements.txt       ← pandas, numpy, sklearn, streamlit, plotly, joblib, openpyxl
├── README.md
├── .streamlit/config.toml ← Tema claro com cores da PM (laranja #EE8133, fundo #FAFAFA)
├── assets/logo.png
├── data/
│   ├── PEDE_PASSOS_DATASET_FIAP.csv   ← Longitudinal 2020-2022 (1.349 alunos, wide format)
│   └── BASE DE DADOS PEDE 2024 - DATATHON.xlsx ← Principal (860 alunos, 42 colunas)
├── docs/
│   ├── POSTECH - Datathon - Fase 5 (1).pdf
│   └── Dicionário Dados Datathon.pdf
├── models/
│   ├── risco_defasagem.joblib       ← Random Forest (acc=69.8%, F1=82.2%, AUC=0.66)
│   ├── enquadramento_pedra.joblib   ← Random Forest (acc_test=79.1%, AUC=0.929) — sem INDE/IAN
│   ├── ponto_virada.joblib          ← Gradient Boosting (acc_test=90.1%, AUC=0.861) — sem IPV/INDE
│   ├── churn.joblib                 ← Random Forest (acc_test=80.2%, AUC=87.8%) — target=evasão real (CSV longitudinal)
│   └── ponto_virada_metrics.json    ← Métricas JSON do modelo PV
└── notebooks/
    └── Analise_Completa_Passos_Magicos.ipynb
```

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

## Tabela resumo dos modelos

| Modelo | Algoritmo | Acc Treino | Acc Teste | AUC | Gap | Status |
|--------|-----------|-----------|----------|-----|-----|--------|
| Risco Defasagem | Random Forest | 69.9% | 69.8% | 0.66 | 0.1pp | ✅ Saudável |
| Enquadramento Pedra | Random Forest | 88.3% | 79.1% | 0.929 | 9.3pp | ✅ Sem leakage |
| Ponto de Virada | Gradient Boosting | 100% | 90.1% | 0.861 | 9.9pp | ✅ Sem leakage (sem IPV/INDE) |
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

- [x] **Limpeza e análise de dados** — app.py + notebook (63 células, 11 análises)
- [ ] **Apresentação gerencial (PPT/PDF)** — **AUSENTE.** ⏸ em pausa
- [x] **Notebook modelo preditivo** — `Analise_Completa_Passos_Magicos.ipynb`
- [x] **App Streamlit** — `app.py` com 7 tabs, 2 modelos ML + 1 sistema de alerta
- [ ] **Deploy Community Cloud** — ⏸ em pausa
- [ ] **Vídeo (até 5 min)** — **AUSENTE.** ⏸ em pausa

## Gaps e prioridades

### CRÍTICO (impede aprovação)
1. **Apresentação gerencial (PPT/PDF)** ⏸ em pausa
2. **Vídeo de apresentação** ⏸ em pausa
3. **Deploy no Streamlit Community Cloud** ⏸ em pausa

### ALTO (qualidade técnica)
4. **Notebook sem outputs:** executar e salvar com outputs para avaliação

### MÉDIO
5. **Documentar sistema de alerta na apresentação:** explicar por que ML foi descartado para evasão (AUC=0.51) e a abordagem determinística é mais honesta e igualmente acionável

## Histórico de decisões

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
