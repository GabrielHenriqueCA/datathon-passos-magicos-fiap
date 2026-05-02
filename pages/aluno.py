"""
Visão do Aluno — experiência gamificada com dark theme (#0D1B2A).
Chamado por app.py quando role == 'aluno'.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import joblib
import numpy as np
import os
import random

# ---------------------------------------------------------------------------
# CSS dark theme — paleta oficial
# #0D1B2A fundo · #132233 cards · rgba(46,134,193,0.35) bordas
# #F4A261 laranja · #8AAFC7 secundário · #E8EDF2 principal
# ---------------------------------------------------------------------------
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #0D1B2A !important;
    color: #E8EDF2 !important;
    font-family: 'Montserrat', sans-serif !important;
}
[data-testid="stSidebar"] {
    background-color: #0D1B2A !important;
}
[data-testid="stSidebar"] * { color: #8AAFC7 !important; }

/* Containers estruturais transparentes — herdam #0D1B2A do pai */
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stColumn"],
[data-testid="stTabsContent"],
[data-testid="stMarkdownContainer"],
[data-testid="stMainBlockContainer"],
.stMarkdown,
.element-container,
.block-container {
    background-color: transparent !important;
}

/* Painéis de aba recebem o fundo de página explicitamente */
[data-baseweb="tab-panel"],
[role="tabpanel"] {
    background-color: #0D1B2A !important;
}

.aluno-card {
    background: #132233;
    border: 1px solid rgba(46,134,193,0.35);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
}
.aluno-card-title {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #8AAFC7;
    margin-bottom: 0.25rem;
}
.aluno-card-value {
    font-size: 1.6rem;
    font-weight: 800;
    color: #F4A261;
}
.aluno-card-sub {
    font-size: 0.72rem;
    color: #8AAFC7;
    margin-top: 0.1rem;
}

.badge-chip {
    display: inline-block;
    background: #132233;
    border: 1px solid rgba(46,134,193,0.35);
    border-radius: 20px;
    padding: 0.2rem 0.7rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #8AAFC7;
    margin: 0.2rem;
}
.badge-earned {
    background: #132233;
    border-color: rgba(46,134,193,0.35);
    color: #F4A261;
}

.xp-bar-bg {
    background: #132233;
    border-radius: 8px;
    height: 12px;
    width: 100%;
    overflow: hidden;
    margin-top: 0.3rem;
}
.xp-bar-fill {
    background: #F4A261;
    height: 100%;
    border-radius: 8px;
    transition: width 0.6s ease;
}

.nota-pill {
    display: inline-block;
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    font-size: 0.85rem;
    font-weight: 700;
    min-width: 3rem;
    text-align: center;
}
.nota-alta  { background: #1A4A2E; color: #6ADAA0; }
.nota-media { background: #3A3010; color: #F4A261; }
.nota-baixa { background: #4A1520; color: #F08080; }

h1, h2, h3, h4 { color: #E8EDF2 !important; }
hr { border-color: rgba(46,134,193,0.35) !important; }

[data-testid="stButton"] > button {
    background: #132233 !important;
    color: #F4A261 !important;
    border: 1px solid rgba(46,134,193,0.35) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stButton"] > button:hover {
    background: #0D1B2A !important;
}

/* ── Treino gamificado ─────────────────────────────────────────────────── */
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-12px); }
}
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25%       { transform: translateX(-8px); }
    75%       { transform: translateX(8px); }
}
@keyframes popIn {
    0%   { transform: scale(0.5); opacity: 0; }
    100% { transform: scale(1);   opacity: 1; }
}

.treino-btn-neutro {
    background: #1B4F72;
    color: #E8EDF2;
    border: 1px solid rgba(46,134,193,0.35);
    border-radius: 8px;
    padding: 0.65rem 1rem;
    text-align: center;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}
.treino-btn-certo {
    background: #1E8449;
    color: #E8EDF2;
    border-radius: 8px;
    padding: 0.65rem 1rem;
    text-align: center;
    font-weight: 700;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}
.treino-btn-errado {
    background: #922B21;
    color: #E8EDF2;
    border-radius: 8px;
    padding: 0.65rem 1rem;
    text-align: center;
    font-weight: 700;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_PEDRA_ICON = {
    'Quartzo': '🪨', 'Ágata': '🟤', 'Ametista': '💜',
    'Topázio': '💎', 'Diamante': '✨',
}
_PEDRA_NEXT = {
    'Quartzo': 'Ágata', 'Ágata': 'Ametista',
    'Ametista': 'Topázio', 'Topázio': 'Diamante', 'Diamante': None,
}

def _nota_class(v):
    if v >= 7.0: return 'nota-alta'
    if v >= 5.0: return 'nota-media'
    return 'nota-baixa'

def _load_model(path):
    """Carrega artefato .joblib e retorna (modelo, artefato). Retorna (None, None) se não existir."""
    if os.path.exists(path):
        artefato = joblib.load(path)
        if isinstance(artefato, dict) and 'modelo' in artefato:
            return artefato['modelo'], artefato
        return artefato, None  # fallback se for modelo direto
    return None, None

def _predict_risco(aluno):
    """Risco de Defasagem — 14 features (mesmo order que train_model.py)."""
    mdl, _ = _load_model('models/risco_defasagem.joblib')
    if mdl is None:
        return None
    try:
        iaa, ieg, ips, ida, ipv = aluno['iaa'], aluno['ieg'], aluno['ips'], aluno['ida'], aluno['ipv']
        fase = aluno['fase']
        anos_pm = aluno['anos_programa']
        genero_num = 0  # mock default
        pv_num = 1 if ipv >= 7.0 else 0
        score_comp = (iaa + ieg + ips) / 3
        gap_iaa_ida = iaa - ida
        ieg_por_fase = ieg / (fase + 1)
        ieg_x_ipv = ieg * ipv
        ida_x_anos = ida * anos_pm

        X = np.array([[iaa, ieg, ips, ida, ipv,
                        fase, anos_pm, genero_num, pv_num,
                        score_comp, gap_iaa_ida,
                        ieg_por_fase, ieg_x_ipv, ida_x_anos]])
        prob = mdl.predict_proba(X)[0][1]
        return prob
    except Exception:
        return None

def _predict_churn(aluno):
    """Risco de Evasão — 10 features (mesmo order que train_model.py)."""
    mdl, _ = _load_model('models/churn.joblib')
    if mdl is None:
        return None
    try:
        iaa, ieg, ips, ida, ipv = aluno['iaa'], aluno['ieg'], aluno['ips'], aluno['ida'], aluno['ipv']
        ian = aluno.get('ian', aluno['inde'])  # IAN não está no mock, usar INDE como proxy
        fase = aluno['fase']
        anos_pm = aluno['anos_programa']
        pedra_ord = {'Quartzo': 1, 'Ágata': 2, 'Agata': 2, 'Ametista': 3, 'Topázio': 4, 'Topazio': 4, 'Diamante': 5}
        pedra_num = pedra_ord.get(aluno['pedra'], 0)
        media_ind = np.nanmean([iaa, ieg, ips, ida, ipv, ian])

        X = np.array([[iaa, ieg, ips, ida, ipv, ian,
                        fase, anos_pm, pedra_num, media_ind]])
        prob = mdl.predict_proba(X)[0][1]
        return prob
    except Exception:
        return None

# ---------------------------------------------------------------------------
# XP / Gamification helpers
# ---------------------------------------------------------------------------
_BADGES_DEF = [
    {'id': 'first_login',  'label': '🏁 Primeiro Acesso', 'desc': 'Entrou pela primeira vez'},
    {'id': 'inde_7',       'label': '⭐ INDE 7+',         'desc': 'INDE acima de 7.0'},
    {'id': 'inde_8',       'label': '🌟 INDE 8+',         'desc': 'INDE acima de 8.0'},
    {'id': 'nota_mat_8',   'label': '📐 Matemático',       'desc': 'Nota Mat ≥ 8.0'},
    {'id': 'nota_port_8',  'label': '📚 Leitor',           'desc': 'Nota Port ≥ 8.0'},
    {'id': 'streak_3',     'label': '🔥 3 Dias Seguidos',  'desc': 'Streak de 3 dias'},
    {'id': 'topazio',      'label': '💎 Topázio',          'desc': 'Pedra Topázio ou superior'},
]

def _init_gamification(aluno_key, aluno):
    sk = f'gam_{aluno_key}'
    if sk not in st.session_state:
        st.session_state[sk] = {
            'xp': 0,
            'streak': 1,
            'badges': set(),
        }
    g = st.session_state[sk]

    g['badges'].add('first_login')
    if aluno['inde'] >= 7.0: g['badges'].add('inde_7')
    if aluno['inde'] >= 8.0: g['badges'].add('inde_8')
    if aluno['nota_mat'] >= 8.0: g['badges'].add('nota_mat_8')
    if aluno['nota_port'] >= 8.0: g['badges'].add('nota_port_8')
    if g['streak'] >= 3: g['badges'].add('streak_3')
    if aluno['pedra'] in ('Topázio', 'Diamante'): g['badges'].add('topazio')

    g['xp'] = int(aluno['inde'] * 100 + len(g['badges']) * 50)
    return g

# ---------------------------------------------------------------------------
# Treino gamificado — helpers
# ---------------------------------------------------------------------------
def _init_treino_state(aluno_key, aluno):
    sk = f'treino_{aluno_key}'
    if sk in st.session_state:
        return
    from data.questoes import QUESTOES
    notas = {
        'Matemática': aluno['nota_mat'],
        'Português':  aluno['nota_port'],
        'Inglês':     aluno['nota_ing'],
    }
    materia = min(notas, key=notas.get)
    pool = list(QUESTOES[materia])
    random.shuffle(pool)
    st.session_state[sk] = {
        'questoes':    pool[:10],
        'atual':       0,
        'respondida':  False,
        'acertos':     0,
        'concluido':   False,
        'materia':     materia,
        'xp_sessao':   0,
        'resposta_sel': None,
    }


def _render_treino_resultado(sk, aluno_key, g):
    t        = st.session_state[sk]
    acertos  = t['acertos']
    xp       = t['xp_sessao']
    materia  = t['materia']

    if acertos == 10:
        badge_html = "<div style='font-size:1.4rem; margin-top:0.5rem;'>💎</div><div style='color:#F4A261; font-weight:800; font-size:0.95rem;'>Treino Perfeito!</div>"
        msg  = f'Incrível! 10 de 10 em {materia}! Você é demais! 🌟'
        anim = 'bounce'
    elif acertos >= 8:
        badge_html = "<div style='font-size:1.4rem; margin-top:0.5rem;'>🎯</div><div style='color:#F4A261; font-weight:800; font-size:0.95rem;'>Elite!</div>"
        msg  = f'Muito bem! {acertos} de 10 acertos! Continue assim! 🔥'
        anim = 'bounce'
    elif acertos >= 5:
        badge_html = ''
        msg  = f'Bom esforço! {acertos} de 10. Com mais prática você vai longe! 💪'
        anim = 'popIn'
    else:
        badge_html = ''
        msg  = f'Cada erro é uma lição! {acertos} de 10. Tente novamente! 📚'
        anim = 'popIn'

    barra_pct = int((acertos / 10) * 100)

    st.markdown(f"""
    <div class='aluno-card' style='text-align:center; padding:1.5rem;'>
        <div style='font-size:3.5rem; display:inline-block; animation:{anim} 0.6s ease;'>🦉</div>
        <div style='font-size:1.5rem; font-weight:800; color:#E8EDF2; margin-top:0.5rem;'>{acertos} / 10</div>
        <div style='font-size:0.85rem; color:#8AAFC7; margin-top:0.3rem;'>{msg}</div>
        {badge_html}
        <div style='margin:1rem 0 0.3rem; font-size:0.72rem; color:#8AAFC7; text-transform:uppercase; letter-spacing:1px;'>Desempenho</div>
        <div style='background:#0D1B2A; border-radius:8px; height:10px; overflow:hidden;'>
            <div style='background:#F4A261; height:100%; width:{barra_pct}%; border-radius:8px;'></div>
        </div>
        <div style='margin-top:0.8rem; font-size:1.1rem; font-weight:800; color:#F4A261;'>+{xp} XP 🚀</div>
    </div>
    """, unsafe_allow_html=True)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button('🔄 Tentar Novamente', key=f'treino_restart_{aluno_key}', use_container_width=True):
            del st.session_state[f'treino_{aluno_key}']
            st.rerun()
    with col_r2:
        if st.button('🏠 Voltar ao Painel', key=f'treino_home_{aluno_key}', use_container_width=True):
            del st.session_state[f'treino_{aluno_key}']
            st.rerun()


def _render_treino(aluno_key, aluno, g):
    _init_treino_state(aluno_key, aluno)
    sk = f'treino_{aluno_key}'
    t  = st.session_state[sk]

    if t['concluido']:
        _render_treino_resultado(sk, aluno_key, g)
        return

    materia      = t['materia']
    notas_map    = {'Matemática': aluno['nota_mat'], 'Português': aluno['nota_port'], 'Inglês': aluno['nota_ing']}
    nota_materia = notas_map[materia]

    # Cabeçalho motivacional apenas na primeira questão
    if t['atual'] == 0 and not t['respondida']:
        st.markdown(f"""
        <div class='aluno-card' style='border:1px solid rgba(244,162,97,0.5); margin-bottom:1rem; text-align:center;'>
            <div style='font-size:2rem;'>🦉</div>
            <div style='font-size:0.9rem; font-weight:700; color:#E8EDF2; margin-top:0.3rem;'>
                Detectamos que sua nota em <strong style='color:#F4A261;'>{materia}</strong> está mais baixa ({nota_materia:.1f}).
            </div>
            <div style='font-size:0.78rem; color:#8AAFC7; margin-top:0.2rem;'>Vamos praticar juntos! 💪</div>
        </div>
        """, unsafe_allow_html=True)

    # Barra de progresso
    atual_num = t['atual'] + 1
    prog_pct  = int((t['atual'] / 10) * 100)
    st.markdown(f"""
    <div style='margin-bottom:1rem;'>
        <div style='display:flex; justify-content:space-between; font-size:0.72rem; color:#8AAFC7; margin-bottom:0.3rem;'>
            <span>Questão {atual_num} de 10</span>
            <span>✅ {t['acertos']} acertos · ⚡ {t['xp_sessao']} XP</span>
        </div>
        <div style='background:#132233; border-radius:8px; height:8px; overflow:hidden;'>
            <div style='background:#F4A261; height:100%; width:{prog_pct}%; border-radius:8px; transition:width 0.4s ease;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    questao = t['questoes'][t['atual']]

    # Card da questão
    st.markdown(f"""
    <div class='aluno-card' style='margin-bottom:0.8rem;'>
        <div style='font-size:0.68rem; color:#8AAFC7; text-transform:uppercase; letter-spacing:1.2px;'>{materia}</div>
        <div style='font-size:1rem; font-weight:700; color:#E8EDF2; margin-top:0.4rem; line-height:1.55;'>{questao['pergunta']}</div>
    </div>
    """, unsafe_allow_html=True)

    if not t['respondida']:
        # Botões de resposta em grid 2×2
        col_a, col_b = st.columns(2)
        for i, opcao in enumerate(questao['opcoes']):
            btn_col = col_a if i % 2 == 0 else col_b
            with btn_col:
                btn_key = 'top_' + aluno_key + '_' + str(t['atual']) + '_' + str(i)
                if st.button(opcao, key=btn_key, use_container_width=True):
                    t['resposta_sel'] = opcao
                    t['respondida']   = True
                    if opcao == questao['correta']:
                        t['acertos']   += 1
                        t['xp_sessao'] += 10
                    else:
                        t['xp_sessao'] += 2
                    st.rerun()
    else:
        # Exibe resultado de cada opção como div colorida
        col_a, col_b = st.columns(2)
        for i, opcao in enumerate(questao['opcoes']):
            btn_col = col_a if i % 2 == 0 else col_b
            with btn_col:
                if opcao == questao['correta']:
                    css_cls = 'treino-btn-certo'
                    prefix  = '✅ '
                elif opcao == t['resposta_sel']:
                    css_cls = 'treino-btn-errado'
                    prefix  = '❌ '
                else:
                    css_cls = 'treino-btn-neutro'
                    prefix  = ''
                st.markdown(f"<div class='{css_cls}'>{prefix}{opcao}</div>", unsafe_allow_html=True)

        # Feedback
        if t['resposta_sel'] == questao['correta']:
            st.markdown("""
            <div style='text-align:center; padding:0.7rem; animation:bounce 0.5s ease;'>
                <div style='font-size:1.6rem;'>🎉 ⭐ 🏆</div>
                <div style='font-size:0.9rem; font-weight:700; color:#6ADAA0; margin-top:0.3rem;'>Correto! +10 XP</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            correta_str = questao['correta']
            dica_str    = questao['dica']
            st.markdown(f"""
            <div style='text-align:center; padding:0.6rem; animation:shake 0.4s ease;'>
                <div style='font-size:1.3rem;'>😅 💪</div>
                <div style='font-size:0.82rem; color:#F08080; font-weight:700; margin-top:0.3rem;'>
                    Resposta correta: <strong style='color:#E8EDF2;'>{correta_str}</strong>
                </div>
                <div style='font-size:0.75rem; color:#8AAFC7; margin-top:0.2rem;'>💡 {dica_str}</div>
                <div style='font-size:0.72rem; color:#F4A261; margin-top:0.15rem;'>+2 XP pelo esforço!</div>
            </div>
            """, unsafe_allow_html=True)

        # Próxima ou Ver Resultado
        if t['atual'] < 9:
            prox_key = 'treino_prox_' + aluno_key + '_' + str(t['atual'])
            if st.button('Próxima ➡️', key=prox_key):
                t['atual']       += 1
                t['respondida']   = False
                t['resposta_sel'] = None
                st.rerun()
        else:
            if st.button('Ver Resultado 🏆', key=f'treino_fim_{aluno_key}'):
                t['concluido']   = True
                t['xp_sessao']  += 20
                gam_key = f'gam_{aluno_key}'
                if gam_key in st.session_state:
                    st.session_state[gam_key]['xp'] += t['xp_sessao']
                st.rerun()


# ---------------------------------------------------------------------------
# Main render function (called from app.py)
# ---------------------------------------------------------------------------
def render(aluno_key, aluno):
    st.markdown(_CSS, unsafe_allow_html=True)

    g = _init_gamification(aluno_key, aluno)

    pedra_icon = _PEDRA_ICON.get(aluno['pedra'], '🔷')
    proxima = _PEDRA_NEXT.get(aluno['pedra'])

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style='display:flex; align-items:center; gap:1rem; margin-bottom:1.5rem;'>
        <div style='font-size:3rem;'>{pedra_icon}</div>
        <div>
            <div style='font-size:1.5rem; font-weight:800; color:#E8EDF2;'>
                Olá, {aluno['nome'].split()[0]}! 👋
            </div>
            <div style='font-size:0.85rem; color:#8AAFC7;'>
                {aluno['pedra']} · Fase {aluno['fase']} · {aluno['anos_programa']} ano(s) no programa · RA {aluno['ra']}
            </div>
        </div>
        <div style='margin-left:auto; text-align:right;'>
            <div style='font-size:0.7rem; color:#8AAFC7; text-transform:uppercase; letter-spacing:1px;'>XP Total</div>
            <div style='font-size:1.8rem; font-weight:800; color:#F4A261;'>{g['xp']:,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # XP bar
    xp_level = (g['xp'] // 1000) + 1
    xp_in_level = g['xp'] % 1000
    pct = min(xp_in_level / 10, 100)
    st.markdown(f"""
    <div style='margin-bottom:1.5rem;'>
        <div style='font-size:0.72rem; color:#8AAFC7;'>Nível {xp_level} — {xp_in_level}/1000 XP para o próximo nível</div>
        <div class='xp-bar-bg'><div class='xp-bar-fill' style='width:{pct:.0f}%;'></div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_visao, tab_notas, tab_missoes, tab_ranking, tab_treino = st.tabs([
        "📊 Meu Painel", "📚 Minhas Notas", "🎯 Missões & Badges", "🏆 Ranking", "🎮 Treino"
    ])

    # ── TAB 1: Visão 360 ─────────────────────────────────────────────────────
    with tab_visao:
        col_gauge, col_cards = st.columns([1, 1])

        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=aluno['inde'],
                delta={'reference': 6.0, 'valueformat': '.2f'},
                number={'font': {'size': 40, 'color': '#F4A261'}, 'valueformat': '.2f'},
                gauge={
                    'axis': {'range': [0, 10], 'tickcolor': '#8AAFC7',
                             'tickfont': {'color': '#8AAFC7', 'size': 10}},
                    'bar': {'color': '#F4A261', 'thickness': 0.25},
                    'bgcolor': '#132233',
                    'bordercolor': 'rgba(46,134,193,0.35)',
                    'steps': [
                        {'range': [0, 4],  'color': '#3A1520'},
                        {'range': [4, 6],  'color': '#3A3010'},
                        {'range': [6, 8],  'color': '#1A3A2E'},
                        {'range': [8, 10], 'color': '#132233'},
                    ],
                    'threshold': {
                        'line': {'color': '#F4A261', 'width': 3},
                        'thickness': 0.75,
                        'value': 7.0,
                    },
                },
                title={'text': 'INDE', 'font': {'size': 14, 'color': '#8AAFC7'}},
            ))
            fig_gauge.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#E8EDF2',
                height=260,
                margin=dict(t=30, b=10, l=20, r=20),
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

            if proxima:
                st.markdown(f"""
                <div style='text-align:center; font-size:0.78rem; color:#8AAFC7; margin-top:-0.5rem;'>
                    Próxima conquista: <strong style='color:#F4A261;'>{proxima}</strong>
                </div>
                """, unsafe_allow_html=True)

        with col_cards:
            indicadores = [
                ('IAA', aluno['iaa'], 'Aprendizagem e Autoavaliação'),
                ('IEG', aluno['ieg'], 'Engajamento'),
                ('IPS', aluno['ips'], 'Desenvolvimento Social'),
                ('IDA', aluno['ida'], 'Desempenho Acadêmico'),
                ('IPV', aluno['ipv'], 'Ponto de Virada'),
            ]
            for sigla, val, desc in indicadores:
                cor = '#6ADAA0' if val >= 7 else ('#F4A261' if val >= 5 else '#F08080')
                barra_pct = val * 10
                st.markdown(f"""
                <div class='aluno-card' style='padding:0.7rem 1rem; margin-bottom:0.5rem;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <div style='font-size:0.72rem; color:#8AAFC7;'>{sigla} — {desc}</div>
                        </div>
                        <div style='font-size:1.1rem; font-weight:800; color:{cor};'>{val:.1f}</div>
                    </div>
                    <div class='xp-bar-bg' style='margin-top:0.4rem; height:6px;'>
                        <div style='background:{cor}; height:100%; width:{barra_pct:.0f}%; border-radius:6px;'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Evolução INDE histórica
        st.markdown("#### 📈 Evolução do INDE")
        hist = aluno['historico_inde']
        anos = sorted(hist.keys())
        vals = [hist[a] for a in anos]
        fig_evo = px.line(
            x=anos, y=vals,
            markers=True,
            labels={'x': 'Ano', 'y': 'INDE'},
        )
        fig_evo.update_traces(
            line_color='#F4A261', marker_color='#F4A261',
            marker_size=10, line_width=3,
        )
        fig_evo.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E8EDF2',
            xaxis=dict(gridcolor='rgba(46,134,193,0.15)', tickvals=anos),
            yaxis=dict(gridcolor='rgba(46,134,193,0.15)', range=[0, 10]),
            height=220,
            margin=dict(t=10, b=30, l=40, r=20),
        )
        st.plotly_chart(fig_evo, use_container_width=True)


    # ── TAB 2: Notas ─────────────────────────────────────────────────────────
    with tab_notas:
        st.markdown("#### 📚 Desempenho Acadêmico")

        notas = [
            ('Matemática', aluno['nota_mat'], '📐'),
            ('Português',  aluno['nota_port'], '📖'),
            ('Inglês',     aluno['nota_ing'],  '🌍'),
        ]

        cols = st.columns(3)
        for i, (disc, nota, icone) in enumerate(notas):
            cls = _nota_class(nota)
            with cols[i]:
                st.markdown(f"""
                <div class='aluno-card' style='text-align:center;'>
                    <div style='font-size:2rem;'>{icone}</div>
                    <div class='aluno-card-title' style='margin-top:0.3rem;'>{disc}</div>
                    <div style='margin-top:0.5rem;'>
                        <span class='nota-pill {cls}'>{nota:.1f}</span>
                    </div>
                    <div class='aluno-card-sub' style='margin-top:0.5rem;'>
                        {'Excelente! 🏆' if nota >= 8 else ('Bom trabalho! 👍' if nota >= 6 else 'Vamos melhorar! 💪')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        media_notas = (aluno['nota_mat'] + aluno['nota_port'] + aluno['nota_ing']) / 3
        st.markdown(f"""
        <div class='aluno-card' style='margin-top:1rem; text-align:center;'>
            <div class='aluno-card-title'>Média Geral das Disciplinas</div>
            <div class='aluno-card-value'>{media_notas:.2f}</div>
            <div class='aluno-card-sub'>
                {'Parabéns! Continue assim 🌟' if media_notas >= 7 else 'Com dedicação você chega lá! 💪'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Radar chart
        st.markdown("#### 🕸️ Perfil de Indicadores")
        cats = ['IAA', 'IEG', 'IPS', 'IDA', 'IPV']
        vals_radar = [aluno['iaa'], aluno['ieg'], aluno['ips'], aluno['ida'], aluno['ipv']]
        vals_radar_closed = vals_radar + [vals_radar[0]]
        cats_closed = cats + [cats[0]]

        fig_radar = go.Figure(go.Scatterpolar(
            r=vals_radar_closed, theta=cats_closed,
            fill='toself', fillcolor='rgba(244,162,97,0.15)',
            line=dict(color='#F4A261', width=2),
            marker=dict(color='#F4A261', size=8),
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor='#132233',
                radialaxis=dict(range=[0, 10], gridcolor='rgba(46,134,193,0.35)',
                                tickfont=dict(color='#8AAFC7', size=9)),
                angularaxis=dict(gridcolor='rgba(46,134,193,0.35)',
                                 tickfont=dict(color='#8AAFC7', size=11)),
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#E8EDF2',
            height=320,
            margin=dict(t=20, b=20, l=40, r=40),
            showlegend=False,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── TAB 3: Missões & Badges ───────────────────────────────────────────────
    with tab_missoes:
        st.markdown("#### 🎯 Missões Ativas")

        missoes = [
            {
                'titulo': '📈 Superar INDE 7.0',
                'desc': 'Alcance um INDE acima de 7.0',
                'meta': 7.0,
                'atual': aluno['inde'],
                'xp': 200,
                'concluida': aluno['inde'] >= 7.0,
            },
            {
                'titulo': '📐 Nota 8 em Matemática',
                'desc': 'Tire 8.0 ou mais em Matemática',
                'meta': 8.0,
                'atual': aluno['nota_mat'],
                'xp': 150,
                'concluida': aluno['nota_mat'] >= 8.0,
            },
            {
                'titulo': '📖 Nota 8 em Português',
                'desc': 'Tire 8.0 ou mais em Português',
                'meta': 8.0,
                'atual': aluno['nota_port'],
                'xp': 150,
                'concluida': aluno['nota_port'] >= 8.0,
            },
            {
                'titulo': '🌍 Nota 6 em Inglês',
                'desc': 'Tire 6.0 ou mais em Inglês',
                'meta': 6.0,
                'atual': aluno['nota_ing'],
                'xp': 100,
                'concluida': aluno['nota_ing'] >= 6.0,
            },
        ]

        for m in missoes:
            pct_m = min((m['atual'] / m['meta']) * 100, 100)
            cor_m = '#6ADAA0' if m['concluida'] else '#F4A261'
            status = '✅ Concluída!' if m['concluida'] else f"{m['atual']:.1f} / {m['meta']:.1f}"
            st.markdown(f"""
            <div class='aluno-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <div style='font-size:0.9rem; font-weight:700; color:#E8EDF2;'>{m['titulo']}</div>
                        <div style='font-size:0.75rem; color:#8AAFC7; margin-top:0.2rem;'>{m['desc']}</div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:0.72rem; color:#8AAFC7;'>Recompensa</div>
                        <div style='font-size:1rem; font-weight:800; color:#F4A261;'>+{m['xp']} XP</div>
                    </div>
                </div>
                <div style='display:flex; align-items:center; gap:0.7rem; margin-top:0.6rem;'>
                    <div class='xp-bar-bg' style='flex:1;'>
                        <div style='background:{cor_m}; height:100%; width:{pct_m:.0f}%; border-radius:8px;'></div>
                    </div>
                    <div style='font-size:0.78rem; font-weight:600; color:{cor_m}; white-space:nowrap;'>{status}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### 🏅 Badges Conquistados")
        badges_html = ""
        for b in _BADGES_DEF:
            earned = b['id'] in g['badges']
            cls = 'badge-chip badge-earned' if earned else 'badge-chip'
            opacity = '1' if earned else '0.4'
            badges_html += f"<span class='{cls}' style='opacity:{opacity};' title='{b['desc']}'>{b['label']}</span>"
        st.markdown(f"<div style='line-height:2.2;'>{badges_html}</div>", unsafe_allow_html=True)

        earned_count = len([b for b in _BADGES_DEF if b['id'] in g['badges']])
        st.markdown(f"""
        <div style='margin-top:0.8rem; font-size:0.8rem; color:#8AAFC7;'>
            {earned_count} de {len(_BADGES_DEF)} badges desbloqueados
        </div>
        """, unsafe_allow_html=True)

    # ── TAB 4: Minha Evolução (auto-comparação temporal) ─────────────────────
    with tab_ranking:
        st.markdown("#### 🏆 Minha Evolução ao Longo do Tempo")
        st.caption("Acompanhe sua própria jornada — veja como você cresceu desde o início no programa Passos Mágicos.")

        hist = aluno['historico_inde']
        anos_hist = sorted(hist.keys())

        # ── Cartões de comparação: Ano Atual vs Ano Anterior ─────────────────
        if len(anos_hist) >= 2:
            ano_atual  = anos_hist[-1]
            ano_ant    = anos_hist[-2]
            inde_atual = hist[ano_atual]
            inde_ant   = hist[ano_ant]
            delta_inde = inde_atual - inde_ant
            delta_cor  = '#6ADAA0' if delta_inde > 0 else ('#F08080' if delta_inde < 0 else '#F4A261')
            delta_icon = '📈' if delta_inde > 0 else ('📉' if delta_inde < 0 else '➡️')
            delta_str  = f"+{delta_inde:.2f}" if delta_inde >= 0 else f"{delta_inde:.2f}"

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='aluno-card' style='text-align:center;'><div class='aluno-card-title'>INDE em {ano_ant}</div><div class='aluno-card-value' style='color:#8AAFC7;'>{inde_ant:.2f}</div><div class='aluno-card-sub'>Ano anterior</div></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='aluno-card' style='text-align:center; border:2px solid {delta_cor};'><div class='aluno-card-title'>Variação {delta_icon}</div><div class='aluno-card-value' style='color:{delta_cor};'>{delta_str}</div><div class='aluno-card-sub'>{ano_ant} → {ano_atual}</div></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='aluno-card' style='text-align:center;'><div class='aluno-card-title'>INDE em {ano_atual}</div><div class='aluno-card-value'>{inde_atual:.2f}</div><div class='aluno-card-sub'>Ano atual</div></div>", unsafe_allow_html=True)
        else:
            ano_atual  = anos_hist[-1]
            inde_atual = hist[ano_atual]
            st.markdown(f"<div class='aluno-card' style='text-align:center;'><div class='aluno-card-title'>INDE em {ano_atual}</div><div class='aluno-card-value'>{inde_atual:.2f}</div><div class='aluno-card-sub'>Primeiro ano registrado</div></div>", unsafe_allow_html=True)

        # ── Gráfico de barras Plotly: Evolução INDE por ano ──────────────────
        st.markdown("#### 📊 Linha do Tempo — INDE")

        anos_str = [str(a) for a in anos_hist]
        vals_bar = [hist[a] for a in anos_hist]
        cores_bar = ['#F4A261' if i == len(anos_hist) - 1 else 'rgba(244,162,97,0.45)' for i in range(len(anos_hist))]

        fig_bar = go.Figure(go.Bar(
            x=anos_str, y=vals_bar,
            marker_color=cores_bar,
            marker_line=dict(color='#F4A261', width=1),
            text=[f"{v:.1f}" for v in vals_bar],
            textposition='outside',
            textfont=dict(color='#F4A261', size=13, family='Montserrat'),
        ))
        # Adicionar setas de variação como annotations
        for i in range(1, len(anos_hist)):
            diff = vals_bar[i] - vals_bar[i - 1]
            arrow_sym = '▲' if diff > 0 else ('▼' if diff < 0 else '●')
            arrow_col = '#6ADAA0' if diff > 0 else ('#F08080' if diff < 0 else '#F4A261')
            fig_bar.add_annotation(
                x=anos_str[i], y=vals_bar[i] + 0.8,
                text=f"<b>{arrow_sym} {diff:+.2f}</b>",
                showarrow=False,
                font=dict(color=arrow_col, size=11),
            )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E8EDF2',
            xaxis=dict(gridcolor='rgba(46,134,193,0.15)', tickfont=dict(color='#8AAFC7', size=12)),
            yaxis=dict(gridcolor='rgba(46,134,193,0.15)', range=[0, 10.5], tickfont=dict(color='#8AAFC7')),
            height=280,
            margin=dict(t=40, b=30, l=40, r=20),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Histórico detalhado por ano ───────────────────────────────────────
        st.markdown("#### 📋 Histórico Detalhado")

        for idx, ano in enumerate(anos_hist):
            val = hist[ano]
            is_last = (idx == len(anos_hist) - 1)
            inde_color = '#F4A261' if is_last else '#E8EDF2'
            border_style = '2px solid rgba(244,162,97,0.5)' if is_last else '1px solid rgba(46,134,193,0.35)'

            if idx > 0:
                prev = hist[anos_hist[idx - 1]]
                diff = val - prev
                diff_str = f"+{diff:.2f}" if diff >= 0 else f"{diff:.2f}"
                diff_color = '#6ADAA0' if diff > 0 else ('#F08080' if diff < 0 else '#8AAFC7')
                diff_icon = '📈' if diff > 0 else ('📉' if diff < 0 else '➡️')
            else:
                diff_str = '—'
                diff_color = '#8AAFC7'
                diff_icon = '🚀'

            if val >= 8.0:   status_str = 'Excelente 🌟'
            elif val >= 6.0: status_str = 'Bom 👍'
            else:            status_str = 'Em desenvolvimento 💪'

            ano_label = f"{ano} ← Atual" if is_last else str(ano)

            row_cols = st.columns([1.5, 2, 2, 2.5])
            with row_cols[0]:
                if is_last:
                    st.markdown(f"**:orange[{ano_label}]**")
                else:
                    st.markdown(f"**{ano_label}**")
            with row_cols[1]:
                st.markdown(f"INDE: **{val:.2f}**")
            with row_cols[2]:
                st.markdown(f"{diff_icon} {diff_str}")
            with row_cols[3]:
                st.markdown(status_str)

            if not is_last:
                st.markdown("<hr style='margin:0.2rem 0; border-color:rgba(46,134,193,0.15);'>", unsafe_allow_html=True)

        # ── Mensagem motivacional ─────────────────────────────────────────────
        total_ganho = hist[anos_hist[-1]] - hist[anos_hist[0]] if len(anos_hist) > 1 else 0
        anos_no_prog = aluno['anos_programa']
        if total_ganho > 0:
            msg_icon = '🚀' if total_ganho >= 2 else '📈'
            msg_texto = f"{msg_icon} Incrível! Você cresceu **{total_ganho:.2f} pontos** de INDE desde que entrou no programa — continue assim!"
        elif total_ganho < 0:
            msg_texto = "💪 Todo caminho tem altos e baixos. O importante é continuar se dedicando — você consegue!"
        else:
            msg_texto = "➡️ Você está mantendo um ritmo estável. Que tal se desafiar a subir um degrau a mais?"

        st.markdown("---")
        st.markdown(msg_texto)
        st.caption(f"{anos_no_prog} ano(s) no Programa Passos Mágicos")

    # ── TAB 5: Treino gamificado ──────────────────────────────────────────────
    with tab_treino:
        _render_treino(aluno_key, aluno, g)
