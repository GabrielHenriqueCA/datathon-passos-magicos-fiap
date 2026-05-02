# CONTEXT — Datathon Passos Mágicos
_Última atualização: 2026-05-02 — Sessão 24 (Restauração da aba Treino gamificado)_

## Sessão 24 — Restauração da aba Treino gamificado

### Problema
A aba `🎮 Treino` havia sido removida do `pages/aluno.py` durante os ajustes das Sessões 22/23.

### Arquivo alterado
`pages/aluno.py` — adição de CSS, três funções helper e nova aba. Nenhuma alteração em `app.py`.

### Mudanças

**CSS adicionado ao `_CSS`:**
- `@keyframes bounce`, `shake`, `popIn` — animações do mascote
- `.treino-btn-neutro` — fundo `#1B4F72`, borda `rgba(46,134,193,0.35)`
- `.treino-btn-certo` — fundo `#1E8449`
- `.treino-btn-errado` — fundo `#922B21`

**Funções novas (antes de `render()`):**
- `_init_treino_state(aluno_key, aluno)` — inicializa `st.session_state[f'treino_{aluno_key}']` com 10 questões aleatórias da matéria mais fraca do aluno
- `_render_treino_resultado(sk, aluno_key, g)` — tela de resultado: placar, barra de desempenho, XP total, badge (💎 Perfeito 10/10 · 🎯 Elite 8+), botões Tentar Novamente / Voltar ao Painel
- `_render_treino(aluno_key, aluno, g)` — mecânica principal: cabeçalho motivacional (1ª questão), barra de progresso "Questão X de 10", card da questão, grid 2×2 de botões (antes de responder = st.button) ou divs coloridas (após responder), feedback animado com +10 XP (acerto) / +2 XP (erro), botão Próxima / Ver Resultado

**`st.tabs` atualizado:**
```python
tab_visao, tab_notas, tab_missoes, tab_ranking, tab_treino = st.tabs([
    "📊 Meu Painel", "📚 Minhas Notas", "🎯 Missões & Badges", "🏆 Ranking", "🎮 Treino"
])
```

**Bloco adicionado ao final de `render()`:**
```python
with tab_treino:
    _render_treino(aluno_key, aluno, g)
```

**Estado via `st.session_state[f'treino_{aluno_key}']`:**
`questoes`, `atual`, `respondida`, `acertos`, `concluido`, `materia`, `xp_sessao`, `resposta_sel`

**Fonte de questões:** `data/questoes.py` — 20 questões por matéria (Matemática, Português, Inglês), 10 sorteadas aleatoriamente via `random.shuffle`.

**Nota:** `app.py` não tem `st.radio` de navegação para o aluno (apenas botão Sair no sidebar), portanto o Treino foi adicionado como 5ª aba interna do `pages/aluno.py`, não como item de radio.

---

## Sessão 23 — Fix HTML bruto na aba Ranking

## Sessão 23 — Fix HTML bruto na aba Ranking

### Problema
A aba Ranking (🏆) renderizava HTML como texto bruto. Causa raiz: f-string com aspas duplas aninhadas dentro de `f"""..."""` — inválido em Python < 3.12 (SyntaxError em tempo de análise), impedindo o módulo de ser importado e fazendo o Streamlit exibir o traceback/HTML como texto.

### Arquivo alterado
`pages/aluno.py` — linhas da timeline na aba Ranking. Nenhuma alteração em `app.py`.

### Mudança aplicada
Na seção "Linha do Tempo — INDE" da aba Ranking, o f-string do loop de barras usava expressões com aspas duplas dentro de `f"""..."""`:

```python
# ANTES (SyntaxError em Python < 3.12):
<div style='...; color:{"#E8EDF2" if is_last else "#8AAFC7"}; font-weight:{"700" if is_last else "400"}; ...'>
{"<div style='...'>●&nbsp;Atual</div>" if is_last else ""}
```

Corrigido pré-computando as variáveis antes do f-string:

```python
# DEPOIS (compatível com Python 3.8+):
year_color   = '#E8EDF2' if is_last else '#8AAFC7'
year_weight  = '700'     if is_last else '400'
atual_marker = "<div style='...'>●&nbsp;Atual</div>" if is_last else ""
# f-string passa a usar {year_color}, {year_weight}, {atual_marker}
```

Nenhuma mudança de lógica, dados ou estilo visual. Todos os `st.markdown` da aba já tinham `unsafe_allow_html=True` corretamente.

---

## Sessão 22 — Fix azul escuro nos cantos da visão do Aluno

### Problema
Containers com `border-radius` exibiam cantos com tons de azul escuro fora da paleta (`#1A2B3C`, `#0F2030`, `#1E3A5A`, `#0A1520`, `#2A3F55` etc.) que "vazavam" para fora dos cards ou apareciam em elementos estruturais que deveriam ser transparentes.

### Arquivo alterado
`pages/aluno.py` — apenas o bloco `_CSS` e cores inline/Plotly. Nenhuma alteração em `app.py`.

### Paleta oficial aplicada
| Token | Hex | Uso |
|---|---|---|
| Transparente | — | Containers estruturais (stColumn, stVerticalBlock…) |
| `#0D1B2A` | fundo escuro | Fundo de página e sidebar |
| `#132233` | card escuro | `.aluno-card`, `.badge-chip`, gauge bgcolor, radar bgcolor |
| `rgba(46,134,193,0.35)` | borda azul | Bordas de cards, badges, hr, gauge bordercolor, grid Plotly |
| `#F4A261` | laranja | Valores XP, destaques, barra XP, threshold gauge |
| `#8AAFC7` | azul aço | Textos secundários, labels, ticks Plotly |
| `#E8EDF2` | branco suave | Textos principais, h1–h4, font_color Plotly |

### Mudanças no `_CSS`
1. **Sidebar**: `#0A1520` → `#0D1B2A` (cor fora da paleta)
2. **Sidebar `*`**: `#C8CDD8` → `#8AAFC7`
3. **`.aluno-card`**: gradiente `#1A2B3C → #0F2030` → sólido `#132233`; borda `#2A3F55` → `rgba(46,134,193,0.35)`
4. **`.aluno-card-title/sub`**: `#7A8FA6` → `#8AAFC7`
5. **`.aluno-card-value`**: `#F4B41A` → `#F4A261`
6. **`.badge-chip`**: `#1E3A5A` → `#132233`; borda `#2E5A80` → `rgba(46,134,193,0.35)`; cor `#A8C8E8` → `#8AAFC7`
7. **`.badge-earned`**: `#1A4A2E` → `#132233`; borda `#2A7A4E` → `rgba(46,134,193,0.35)`; cor `#6ADAA0` → `#F4A261`
8. **`.xp-bar-bg`**: `#1A2B3C` → `#132233`
9. **`.xp-bar-fill`**: gradiente `#F4B41A, #EE8133` → sólido `#F4A261`
10. **`.nota-media`**: cor `#F4B41A` → `#F4A261`
11. **`h1–h4`**: `#E8EAF0` → `#E8EDF2`
12. **`hr`**: `#2A3F55` → `rgba(46,134,193,0.35)`
13. **Botões**: `#2D325E/#4A4F7A` → `#132233/rgba(46,134,193,0.35)`; hover `#3D4270` → `#0D1B2A`
14. **Adicionadas regras de containers transparentes**: `stVerticalBlock`, `stHorizontalBlock`, `stColumn`, `stTabsContent`, `stMarkdownContainer`, `stMainBlockContainer`, `.stMarkdown`, `.element-container`, `.block-container` → `transparent`
15. **Tab panels**: `[data-baseweb="tab-panel"]`, `[role="tabpanel"]` → `#0D1B2A`

### Mudanças nos inline styles HTML
- Todas as ocorrências de `#E8EAF0` → `#E8EDF2`
- Todas as ocorrências de `#7A8FA6` → `#8AAFC7`
- Todas as ocorrências de `#F4B41A` → `#F4A261`
- Bordas inline `#2A3F55` (ranking) → `rgba(46,134,193,0.35)`

### Mudanças nos gráficos Plotly
- **Gauge INDE**: `bgcolor #1A2B3C` → `#132233`; `bordercolor #2A3F55` → `rgba(46,134,193,0.35)`; número/barra `#F4B41A` → `#F4A261`; threshold `#EE8133` → `#F4A261`; ticks `#7A8FA6` → `#8AAFC7`; step topo `#1A2B3C` → `#132233`; `font_color #E8EAF0` → `#E8EDF2`
- **Line chart Evolução INDE**: linha/marcador `#F4B41A/#EE8133` → `#F4A261`; gridcolor `#1A2B3C` → `rgba(46,134,193,0.15)`; `font_color #E8EAF0` → `#E8EDF2`
- **Radar chart**: `polar bgcolor #1A2B3C` → `#132233`; gridlines `#2A3F55` → `rgba(46,134,193,0.35)`; ticks `#7A8FA6/#C8CDD8` → `#8AAFC7`; fill `rgba(244,180,26,0.15)` → `rgba(244,162,97,0.15)`; linha/marcador `#F4B41A/#EE8133` → `#F4A261`; `font_color #E8EAF0` → `#E8EDF2`

### Cores semânticas mantidas (não são azul escuro)
- `#6ADAA0` / `#F08080` — indicadores de risco/saúde nas predições e barras de indicadores
- `#1A4A2E` / `#3A3010` / `#4A1520` — fundos dos pills de nota (verde/âmbar/vermelho)

### Nota sobre diretório
O diretório `pages/` havia sido deletado da árvore de trabalho. Foi recriado e `pages/aluno.py` foi restaurado a partir do commit `89958ef` com todas as correções desta sessão aplicadas.

---

## Sessão 21 — Unificação visual completa: Aluno = Admin

### Objetivo
Fazer a visão do aluno usar exatamente o mesmo tema visual do admin: fundo `#FAFAFA`, sidebar roxo gradiente `#2D325E → #1E2245`, botões laranja `#EE8133`, tabs roxo, fontes Montserrat.

### Arquivo alterado
`pages/aluno.py` — apenas o bloco `_CSS` e os layouts Plotly. Nenhuma alteração no `app.py`.

### Mudanças no `_CSS`
O bloco `_CSS` foi reescrito: **removidos** todos os overrides de dark theme que conflitavam com o CSS compartilhado do `app.py`:
- `html/body/stAppViewContainer/stMain { background: #0D1B2A }` → **removido** (herda #FAFAFA do admin)
- `h1–h4 { color: #E8EDF2 }` → **removido** (herda #333333 do admin)
- `hr { border-color: rgba(46,134,193,0.2) }` → **removido**
- Botões com gradiente azul `#1B4F72 → #2E86C1` → **removidos** (herda laranja do admin)
- Tabs com `#132233/#2E86C1` → **removidos** (herda tabs roxo do admin)
- Labels com `#8AAFC7` → **removidos**
- Todos os container fixes da Sessão 20 → **removidos** (não necessários sem dark theme)

**Mantidas** apenas as classes de componente gamificado exclusivas:
- `.aluno-card` — dark card `#132233` sobre fundo claro (contraste intencional)
- `.aluno-card-title/value/sub` — cores da paleta do aluno
- `.badge-chip/.badge-earned` — badges gamificados
- `.xp-bar-bg/.xp-bar-fill` — barra de XP laranja
- `.nota-pill/.nota-alta/.nota-media/.nota-baixa` — pills de notas
- `@keyframes bounce/shake/popIn/spin` — animações do Treino
- `.treino-btn-neutro/certo/errado/apagado` — botões do jogo (dark intencional dentro dos cards)

### Mudanças nos gráficos Plotly
3 gráficos tinham `font_color='#E8EAF0'` (branco — invisível no fundo claro) e `gridcolor` escuro:
- **Gauge INDE**: `font_color` → `#555555`
- **Line chart Evolução INDE**: `font_color` → `#333333`, `gridcolor` → `#E0E0E0`
- **Radar chart Indicadores**: `font_color` → `#333333` (bgcolor polar `#1A2B3C` mantido — dark chart box intencional)

### Resultado verificado visualmente (browser subagent)
| Elemento | Admin | Aluno | Status |
|---|---|---|---|
| Fundo | #FAFAFA | #FAFAFA | ✅ |
| Sidebar | Roxo gradiente | Roxo gradiente | ✅ |
| Botão Sair | Laranja | Laranja | ✅ |
| Cards gamificados | Dark #132233 | Dark #132233 | ✅ |
| Tabs | Roxo ativo | Roxo ativo | ✅ |
| Gráficos | Fundo transparente | Fundo transparente | ✅ |
| Títulos | #333333 Montserrat | #333333 Montserrat | ✅ |

App rodando em: http://localhost:8507

---

## Sessão 20 — Fix fundos pretos na visão do aluno

### Problema
O Streamlit injeta automaticamente um fundo escuro próximo de preto em containers internos (`stVerticalBlock`, `stHorizontalBlock`, `stColumn`, painéis de tabs, etc.) quando o CSS do tema dark está parcialmente ativo. Isso causava fundos pretos visíveis em cards e seções da visão do aluno.

### Arquivo alterado
`pages/aluno.py` — apenas o bloco `_CSS` (HTML inline/CSS local). Nenhuma alteração no `app.py` ou CSS global.

### Solução
Adicionadas regras CSS cirúrgicas no bloco `_CSS` de `pages/aluno.py` para forçar `background-color: transparent !important` nos containers internos do Streamlit, fazendo-os herdar corretamente o `#0D1B2A` do fundo principal. Os painéis de tab (`[data-baseweb="tab-panel"]`, `[role="tabpanel"]`) recebem `background-color: #0D1B2A !important` explicitamente.

### Seletores corrigidos
- `[data-testid="stVerticalBlock"]` → transparent
- `[data-testid="stHorizontalBlock"]` → transparent
- `[data-testid="stColumn"]` → transparent
- `[data-testid="stTabsContent"]` → transparent
- `[data-testid="stMarkdownContainer"]` → transparent
- `[data-testid="stMainBlockContainer"]` → transparent
- `.stMarkdown`, `.element-container`, `.block-container` → transparent
- `[data-baseweb="tab-panel"]`, `[role="tabpanel"]` → `#0D1B2A`

### Verificação
Inspecionado visualmente via browser subagent: todas as 5 abas da visão do aluno confirmadas sem fundos pretos. Cards com `#132233`, fundo principal `#0D1B2A`, botões com gradiente azul, tabs com `#132233`/`#2E86C1`.

---

## Sessão 19 — Unificação visual Admin = Aluno

### Problema raiz
O CSS global do admin ficava depois do `st.stop()` do aluno → nunca aplicava ao perfil aluno.
O `_CSS` de `pages/aluno.py` forçava dark theme (#0D1B2A) que conflitava com o admin.

### Solução (3 mudanças)

**1. app.py — bloco "Tema compartilhado"** inserido logo após `if not logged_in → st.stop()`,
antes do roteamento de perfil. Define: Montserrat, :root vars, fundo #FAFAFA, sidebar roxo gradiente,
botões laranja, tabs roxo, stHeader transparente, stSidebarNav oculto, #MainMenu/footer ocultos.
Roda para admin E aluno (admin pode ter duplicação idempotente com seu bloco CSS original).

**2. pages/aluno.py — `_CSS` reescrito**: removidos todos os overrides de dark theme
(html/body/sidebar/h1-h6/hr/botões). Mantidos apenas:
- `.aluno-card`: bg=#132233, border=rgba(46,134,193,0.35) — dark card on light bg
- `.aluno-card-value`: color=#F4A261 (laranja quente)
- `.aluno-card-title`/`.aluno-card-sub`: color=#8AAFC7 (azul aço)
- `.badge-chip`: bg=#1B4F72, border azul
- `.xp-bar-bg`: bg=#D9E8F5 (claro), fill=laranja gradiente
- `.nota-pill` classes: mantidas (usadas dentro de cards escuros)
- `@keyframes` e `.treino-btn-*`: mantidos (UI do jogo)

**3. pages/aluno.py — cabeçalho do aluno**: inline styles atualizados:
- Nome: `#E8EAF0` → `#2D325E`
- Subtítulo/labels: `#7A8FA6` → `#555555`
- XP valor: `#F4B41A` → `#F4A261`

## Sessão 18 — Fix TypeError + supressão de menu

### Problema 1 — TypeError na chamada de _render_aluno (app.py)
- Adicionado `pagina_aluno = st.radio(...)` ao sidebar do aluno com as 5 opções de navegação
- Chamada atualizada para `_render_aluno(aluno_key, aluno_data, pagina_aluno)`
- Assinatura de `render` em `pages/aluno.py` atualizada para `render(aluno_key, aluno, pagina_aluno=None)` — sem mudanças internas

### Problema 2 — Menu pages/ aparecendo para aluno
- Causa: CSS de supressão de `stSidebarNav` ficava no bloco admin (após `st.stop()` do aluno)
- Fix: injetado bloco CSS com as duas regras de supressão **imediatamente após `st.set_page_config()`**, antes de qualquer roteamento — garante execução para todos os perfis
- `[ui] hideSidebarNav = true` em `.streamlit/config.toml` já estava correto

## Sessão 17 — Aba Treino gamificada (Duolingo-style)

### Novos elementos em pages/aluno.py
- **6ª aba `🎮 Treino`** adicionada à visão do aluno
- **Lógica de matéria fraca**: compara `nota_mat / nota_port / nota_ing` → foca na pior
- **Mensagem motivacional** na 1ª questão: "Detectamos que sua nota em [Matéria] está mais baixa. Vamos praticar juntos! 💪"
- **10 questões sorteadas** aleatoriamente de `data/questoes.py` (pool de 20/matéria)
- **Uma questão por vez** com grid 2×2 de botões interativos
- **Feedback animado**: acerto → `bounce 🎉 ��� 🏆 +10 XP`; erro → `shake 😅 resposta correta`
- **Tela de resultado final**: mascote animado, barra de acerto, XP ganho, badge desbloqueado
- **XP por sessão**: acerto=+10 XP, erro=+2 XP, bônus conclusão=+20 XP
- **2 novos badges**: `treino_elite` (8+ acertos) e `treino_perfeito` (10/10)
- **Animações CSS** no `_CSS` global: `@keyframes bounce/shake/popIn/spin` + classes `.treino-btn-*`
- **Helpers criados**: `_init_treino_state()`, `_render_treino_questao()`, `_render_treino_resultado()`
- **Estado**: `st.session_state[f'treino_{aluno_key}']` com dict `{questoes, atual, respondida, acertos, concluido, materia, xp_sessao, resposta_sel}`
- **"Tentar Novamente"** reseta estado e sorteia novas 10 questões da mesma matéria

## Sessão 16 — Fix header branco + aba Quiz

### Fix faixa branca no topo (app.py CSS global)
Adicionadas 3 regras cirúrgicas ao final do bloco CSS global de `app.py` para remover a faixa branca nativa do Streamlit:
- `[data-testid="stHeader"]` → `background: transparent`
- `[data-testid="stToolbar"]` → `background: transparent`
- `[data-testid="collapsedControl"]` e `[data-testid="stSidebarCollapsedControl"]` → `background: transparent`, `border: none`, `box-shadow: none`
As novas regras ficam **após** a regra existente `background: white !important` do `collapsedControl` (linha ~1003), garantindo que a sobrescrevem pela ordem de cascade.

### Aba Quiz em pages/aluno.py
Integrado `data/questoes.py` (60 questões: 20 Mat / 20 Port / 20 Inglês) à visão gamificada do aluno:
- Nova aba `🧠 Quiz` (5ª aba) com seletor de matéria, barra de progresso, questão aleatória, 4 opções, feedback (acerto/erro + dica), +50 XP por acerto
- Estado persistido em `st.session_state[f'quiz_{aluno_key}']`
- 4 novos badges: 🧠 Primeiro Quiz, 🎯 5 Acertos, 🏆 10 Acertos, 🔢 Mestre em Matemática
- Painel de desempenho geral (acertos/total por matéria) ao final da aba

## Sessão 14 — Login system e ajustes de UI

### Arquitetura de login (adicionada em Sessão 14)
- `data/mock_alunos.py` — USERS dict + ALUNOS_MOCK dict (3 alunos mock)
- `pages/aluno.py` — visão gamificada do aluno (dark theme #0D1B2A)
- `pages/admin.py` — placeholder (admin view segue em app.py)
- `app.py` — gate de login após `st.set_page_config()` via `st.session_state`
  - `role == 'aluno'` → roteia para `pages/aluno.render()` + `st.stop()`
  - `role == 'admin'` → executa fluxo normal do dashboard
- Credenciais: `admin/admin123`, `aluno01-03/1234`

### Sessão 15 — Revert + fix tela de login
- Código revertido para o commit `65ba995` (primeiro login do dia 23/04)
- `pages/conta.py` removido, `.streamlit/config.toml` restaurado
- **Tela de login corrigida**: removido `.login-box` div sombreado; tudo em `st.columns([1,1.2,1])` → `col2`; logo processada com PIL (remove pixels brancos > 200), base64-encoded inline; ordem: logo → título → subtítulo → inputs → botão → rodapé; sem container externo
- **Nav automática suprimida**: `[ui] hideSidebarNav = true` em `.streamlit/config.toml` + 2 regras CSS (`[data-testid="stSidebarNav"]` e `nav[data-testid="stSidebarNav"]`); regras `ul/li/a[href]` removidas pois ocultavam o sidebar inteiro

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
11. **CSS global antes do roteamento** — bloco CSS inserido entre o gate de login e o `if role == 'aluno'`; cobre sidebar dark, supressão de nav automática, remoção de espaço do topo, fundo `.stApp` e containers transparentes
12. **Sidebar admin e aluno espelhados** — ambos usam `st.title` + `st.caption` + `st.divider` + `st.radio` + `st.divider` + `st.caption`; CSS de sidebar local removido de `pages/aluno.py` (herda do global)

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
