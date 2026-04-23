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
from datetime import datetime

# ---------------------------------------------------------------------------
# CSS dark theme
# ---------------------------------------------------------------------------
_CSS = """
<style>
/* Suprime navegação automática de pages/ */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarNav"] + div hr { display: none !important; }

@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #0D1B2A !important;
    color: #E8EAF0 !important;
    font-family: 'Montserrat', sans-serif !important;
}
[data-testid="stSidebar"] {
    background-color: #0A1520 !important;
}
[data-testid="stSidebar"] * { color: #C8CDD8 !important; }

.aluno-card {
    background: linear-gradient(135deg, #1A2B3C 0%, #0F2030 100%);
    border: 1px solid #2A3F55;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
}
.aluno-card-title {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #7A8FA6;
    margin-bottom: 0.25rem;
}
.aluno-card-value {
    font-size: 1.6rem;
    font-weight: 800;
    color: #F4B41A;
}
.aluno-card-sub {
    font-size: 0.72rem;
    color: #7A8FA6;
    margin-top: 0.1rem;
}

.badge-chip {
    display: inline-block;
    background: #1E3A5A;
    border: 1px solid #2E5A80;
    border-radius: 20px;
    padding: 0.2rem 0.7rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #A8C8E8;
    margin: 0.2rem;
}
.badge-earned {
    background: #1A4A2E;
    border-color: #2A7A4E;
    color: #6ADAA0;
}

.xp-bar-bg {
    background: #1A2B3C;
    border-radius: 8px;
    height: 12px;
    width: 100%;
    overflow: hidden;
    margin-top: 0.3rem;
}
.xp-bar-fill {
    background: linear-gradient(90deg, #F4B41A, #EE8133);
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
.nota-media { background: #3A3010; color: #F4B41A; }
.nota-baixa { background: #4A1520; color: #F08080; }

h1, h2, h3, h4 { color: #E8EAF0 !important; }
hr { border-color: #2A3F55 !important; }

[data-testid="stButton"] > button {
    background: #2D325E !important;
    color: #F4B41A !important;
    border: 1px solid #4A4F7A !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stButton"] > button:hover {
    background: #3D4270 !important;
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
    if os.path.exists(path):
        return joblib.load(path)
    return None

def _predict_risco(aluno):
    mdl = _load_model('models/risco_defasagem.joblib')
    if mdl is None:
        return None
    media = (aluno['iaa'] + aluno['ieg'] + aluno['ips'] + aluno['ida'] + aluno['ipv']) / 5
    X = np.array([[aluno['inde'], media, 0.0, 1.0, 0.0]])
    try:
        prob = mdl.predict_proba(X)[0][1]
        return prob
    except Exception:
        return None

def _predict_churn(aluno):
    mdl = _load_model('models/churn.joblib')
    if mdl is None:
        return None
    media = (aluno['iaa'] + aluno['ieg'] + aluno['ips'] + aluno['ida'] + aluno['ipv']) / 5
    X = np.array([[aluno['inde'], aluno['fase'], aluno['anos_programa'], media, 0.0, 1.0, 0.0]])
    try:
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

    # Grant badges based on data
    g['badges'].add('first_login')
    if aluno['inde'] >= 7.0: g['badges'].add('inde_7')
    if aluno['inde'] >= 8.0: g['badges'].add('inde_8')
    if aluno['nota_mat'] >= 8.0: g['badges'].add('nota_mat_8')
    if aluno['nota_port'] >= 8.0: g['badges'].add('nota_port_8')
    if g['streak'] >= 3: g['badges'].add('streak_3')
    if aluno['pedra'] in ('Topázio', 'Diamante'): g['badges'].add('topazio')

    # XP from performance
    g['xp'] = int(aluno['inde'] * 100 + len(g['badges']) * 50)
    return g

# ---------------------------------------------------------------------------
# Main render function (called from app.py)
# ---------------------------------------------------------------------------
def render(aluno_key, aluno, pagina_aluno="🏠 Meu Painel"):
    st.markdown(_CSS, unsafe_allow_html=True)

    g = _init_gamification(aluno_key, aluno)

    pedra_icon = _PEDRA_ICON.get(aluno['pedra'], '🔷')
    proxima = _PEDRA_NEXT.get(aluno['pedra'])

    # ── Header ──────────────────────────────────────────────────────────────
    inicial = aluno['nome'][0].upper()
    nome = aluno['nome']
    pedra = aluno['pedra']
    fase = aluno['fase']
    anos = aluno['anos_programa']
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #132233 0%, #0D1B2A 100%);
        border: 1px solid rgba(46,134,193,0.35);
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 20px;
    ">
        <div style="
            width: 64px; height: 64px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1B4F72, #2E86C1);
            display: flex; align-items: center; justify-content: center;
            font-size: 28px; font-weight: 700; color: white;
            flex-shrink: 0;
        ">{inicial}</div>
        <div style="flex:1;">
            <h2 style="color:#F4A261; margin:0; font-size:1.5rem">Olá, {nome.split()[0]}! 👋</h2>
            <p style="color:#8AAFC7; margin:4px 0 0 0; font-size:0.9rem">
                {pedra_icon} {pedra} &nbsp;·&nbsp; Fase {fase}
                &nbsp;·&nbsp; {anos} ano(s) no programa
            </p>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.7rem; color:#7A8FA6; text-transform:uppercase; letter-spacing:1px;">XP Total</div>
            <div style="font-size:1.8rem; font-weight:800; color:#F4B41A;">{g['xp']:,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # XP bar (next 1000 XP threshold)
    xp_level = (g['xp'] // 1000) + 1
    xp_in_level = g['xp'] % 1000
    pct = min(xp_in_level / 10, 100)
    st.markdown(f"""
    <div style='margin-bottom:1.5rem;'>
        <div style='font-size:0.72rem; color:#7A8FA6;'>Nível {xp_level} — {xp_in_level}/1000 XP para o próximo nível</div>
        <div class='xp-bar-bg'><div class='xp-bar-fill' style='width:{pct:.0f}%;'></div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Roteamento por seleção do sidebar ────────────────────────────────────
    if pagina_aluno == "🏠 Meu Painel":
        col_gauge, col_cards = st.columns([1, 1])

        with col_gauge:
            # INDE Gauge
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=aluno['inde'],
                delta={'reference': 6.0, 'valueformat': '.2f'},
                number={'font': {'size': 40, 'color': '#F4B41A'}, 'valueformat': '.2f'},
                gauge={
                    'axis': {'range': [0, 10], 'tickcolor': '#7A8FA6',
                             'tickfont': {'color': '#7A8FA6', 'size': 10}},
                    'bar': {'color': '#F4B41A', 'thickness': 0.25},
                    'bgcolor': '#1A2B3C',
                    'bordercolor': '#2A3F55',
                    'steps': [
                        {'range': [0, 4],  'color': '#3A1520'},
                        {'range': [4, 6],  'color': '#3A3010'},
                        {'range': [6, 8],  'color': '#1A3A2E'},
                        {'range': [8, 10], 'color': '#1A2B3C'},
                    ],
                    'threshold': {
                        'line': {'color': '#EE8133', 'width': 3},
                        'thickness': 0.75,
                        'value': 7.0,
                    },
                },
                title={'text': 'INDE', 'font': {'size': 14, 'color': '#7A8FA6'}},
            ))
            fig_gauge.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#E8EAF0',
                height=260,
                margin=dict(t=30, b=10, l=20, r=20),
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

            if proxima:
                st.markdown(f"""
                <div style='text-align:center; font-size:0.78rem; color:#7A8FA6; margin-top:-0.5rem;'>
                    Próxima conquista: <strong style='color:#F4B41A;'>{proxima}</strong>
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
                cor = '#6ADAA0' if val >= 7 else ('#F4B41A' if val >= 5 else '#F08080')
                barra_pct = val * 10
                st.markdown(f"""
                <div class='aluno-card' style='padding:0.7rem 1rem; margin-bottom:0.5rem;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <div style='font-size:0.72rem; color:#7A8FA6;'>{sigla} — {desc}</div>
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
            line_color='#F4B41A', marker_color='#EE8133',
            marker_size=10, line_width=3,
        )
        fig_evo.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E8EAF0',
            xaxis=dict(gridcolor='#1A2B3C', tickvals=anos),
            yaxis=dict(gridcolor='#1A2B3C', range=[0, 10]),
            height=220,
            margin=dict(t=10, b=30, l=40, r=20),
        )
        st.plotly_chart(fig_evo, use_container_width=True)

        # ML predictions
        st.markdown("#### 🤖 Análise Preditiva")
        prob_risco = _predict_risco(aluno)
        prob_churn = _predict_churn(aluno)

        c1, c2 = st.columns(2)
        with c1:
            if prob_risco is not None:
                cor_r = '#F08080' if prob_risco > 0.5 else '#6ADAA0'
                label_r = '⚠️ Risco identificado' if prob_risco > 0.5 else '✅ Sem risco'
                st.markdown(f"""
                <div class='aluno-card'>
                    <div class='aluno-card-title'>Risco de Defasagem</div>
                    <div class='aluno-card-value' style='color:{cor_r};'>{prob_risco:.0%}</div>
                    <div class='aluno-card-sub'>{label_r}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Modelo de risco não disponível.")
        with c2:
            if prob_churn is not None:
                cor_c = '#F08080' if prob_churn > 0.4 else '#6ADAA0'
                label_c = '⚠️ Atenção necessária' if prob_churn > 0.4 else '✅ Engajamento saudável'
                st.markdown(f"""
                <div class='aluno-card'>
                    <div class='aluno-card-title'>Risco de Evasão</div>
                    <div class='aluno-card-value' style='color:{cor_c};'>{prob_churn:.0%}</div>
                    <div class='aluno-card-sub'>{label_c}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Modelo de evasão não disponível.")

    elif pagina_aluno == "📝 Minhas Notas":
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
            fill='toself', fillcolor='rgba(244,180,26,0.15)',
            line=dict(color='#F4B41A', width=2),
            marker=dict(color='#EE8133', size=8),
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor='#1A2B3C',
                radialaxis=dict(range=[0, 10], gridcolor='#2A3F55',
                                tickfont=dict(color='#7A8FA6', size=9)),
                angularaxis=dict(gridcolor='#2A3F55',
                                 tickfont=dict(color='#C8CDD8', size=11)),
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#E8EAF0',
            height=320,
            margin=dict(t=20, b=20, l=40, r=40),
            showlegend=False,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    elif pagina_aluno == "🎮 Missões & Badges":
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
            cor_m = '#6ADAA0' if m['concluida'] else '#F4B41A'
            status = '✅ Concluída!' if m['concluida'] else f"{m['atual']:.1f} / {m['meta']:.1f}"
            st.markdown(f"""
            <div class='aluno-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <div style='font-size:0.9rem; font-weight:700; color:#E8EAF0;'>{m['titulo']}</div>
                        <div style='font-size:0.75rem; color:#7A8FA6; margin-top:0.2rem;'>{m['desc']}</div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:0.72rem; color:#7A8FA6;'>Recompensa</div>
                        <div style='font-size:1rem; font-weight:800; color:#F4B41A;'>+{m['xp']} XP</div>
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
        <div style='margin-top:0.8rem; font-size:0.8rem; color:#7A8FA6;'>
            {earned_count} de {len(_BADGES_DEF)} badges desbloqueados
        </div>
        """, unsafe_allow_html=True)

    elif pagina_aluno == "🏆 Ranking":
        st.markdown("#### 🏆 Mini Ranking do Programa")

        from data.mock_alunos import ALUNOS_MOCK
        ranking_data = []
        for key, a in ALUNOS_MOCK.items():
            sk = f'gam_{key}'
            xp_a = st.session_state.get(sk, {}).get('xp', int(a['inde'] * 100))
            ranking_data.append({
                'nome': a['nome'],
                'pedra': a['pedra'],
                'inde': a['inde'],
                'xp': xp_a,
                'key': key,
            })
        ranking_data.sort(key=lambda x: x['xp'], reverse=True)

        medals = ['🥇', '🥈', '🥉']
        for i, r in enumerate(ranking_data):
            medal = medals[i] if i < 3 else f'{i+1}.'
            destaque = r['key'] == aluno_key
            border = '2px solid #F4B41A' if destaque else '1px solid #2A3F55'
            nome_str = f"<strong>{r['nome']}</strong> ← você" if destaque else r['nome']
            pedra_ic = _PEDRA_ICON.get(r['pedra'], '🔷')
            st.markdown(f"""
            <div class='aluno-card' style='border:{border}; padding:0.8rem 1.1rem;'>
                <div style='display:flex; align-items:center; gap:0.8rem;'>
                    <div style='font-size:1.4rem; min-width:2rem;'>{medal}</div>
                    <div style='flex:1;'>
                        <div style='font-size:0.88rem; color:#E8EAF0;'>{nome_str}</div>
                        <div style='font-size:0.72rem; color:#7A8FA6;'>{pedra_ic} {r['pedra']} · INDE {r['inde']:.2f}</div>
                    </div>
                    <div style='font-size:1.1rem; font-weight:800; color:#F4B41A;'>{r['xp']:,} XP</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    elif pagina_aluno == "⚙️ Conta":
        from pages.conta import render as _render_conta
        _render_conta()
