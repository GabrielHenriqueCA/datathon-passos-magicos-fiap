"""
Página de Conta — compartilhada entre admin e aluno.
"""

import streamlit as st
from datetime import datetime
from data.mock_alunos import ALUNOS_MOCK


def _render_pagina_conta(nome, usuario, perfil_label, inicial, login_time):
    tempo_logado = datetime.now() - login_time
    minutos  = int(tempo_logado.total_seconds() // 60)
    segundos = int(tempo_logado.total_seconds() % 60)
    tempo_str  = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
    hora_login = login_time.strftime('%H:%M:%S')

    st.title("⚙️ Conta")
    st.divider()

    st.markdown(f"""
    <div style="
        background: #132233;
        border: 1px solid rgba(46,134,193,0.35);
        border-radius: 14px;
        padding: 32px;
        margin-bottom: 24px;
    ">
        <div style="display:flex; align-items:center; gap:20px; margin-bottom:28px">
            <div style="
                width: 72px; height: 72px;
                border-radius: 50%;
                background: linear-gradient(135deg, #1B4F72, #2E86C1);
                display: flex; align-items: center; justify-content: center;
                font-size: 32px; font-weight: 700; color: white; flex-shrink: 0;
            ">{inicial}</div>
            <div>
                <h2 style="color:#F4A261; margin:0; font-size:1.4rem">{nome}</h2>
                <p style="color:#8AAFC7; margin:4px 0 0 0; font-size:0.9rem">{perfil_label}</p>
            </div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px">
            <div style="background:#0D1B2A; border-radius:10px; padding:16px;
                        border:1px solid rgba(46,134,193,0.2)">
                <p style="color:#8AAFC7; margin:0; font-size:0.75rem;
                          text-transform:uppercase; letter-spacing:0.5px">Conta Logada</p>
                <p style="color:#F4A261; margin:6px 0 0 0; font-weight:600; font-size:1rem">{usuario}</p>
            </div>
            <div style="background:#0D1B2A; border-radius:10px; padding:16px;
                        border:1px solid rgba(46,134,193,0.2)">
                <p style="color:#8AAFC7; margin:0; font-size:0.75rem;
                          text-transform:uppercase; letter-spacing:0.5px">Tempo Conectado</p>
                <p style="color:#F4A261; margin:6px 0 0 0; font-weight:600; font-size:1rem">{tempo_str}</p>
            </div>
            <div style="background:#0D1B2A; border-radius:10px; padding:16px;
                        border:1px solid rgba(46,134,193,0.2)">
                <p style="color:#8AAFC7; margin:0; font-size:0.75rem;
                          text-transform:uppercase; letter-spacing:0.5px">Perfil de Acesso</p>
                <p style="color:#F4A261; margin:6px 0 0 0; font-weight:600; font-size:1rem">{perfil_label}</p>
            </div>
            <div style="background:#0D1B2A; border-radius:10px; padding:16px;
                        border:1px solid rgba(46,134,193,0.2)">
                <p style="color:#8AAFC7; margin:0; font-size:0.75rem;
                          text-transform:uppercase; letter-spacing:0.5px">Sessão Iniciada às</p>
                <p style="color:#F4A261; margin:6px 0 0 0; font-weight:600; font-size:1rem">{hora_login}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    with col2:
        if st.button("🚪 Encerrar Sessão", use_container_width=True, type="primary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def render():
    usuario   = st.session_state.get('username', '—')
    role      = st.session_state.get('role', '—')
    aluno_key = st.session_state.get('aluno_key')

    if role == 'admin':
        nome         = 'Administrador'
        perfil_label = 'Administrador do Sistema'
        inicial      = 'A'
    else:
        aluno        = ALUNOS_MOCK.get(aluno_key, {})
        nome         = aluno.get('nome', usuario.capitalize())
        perfil_label = 'Aluno — ' + aluno.get('pedra', '')
        inicial      = nome[0].upper()

    login_time = st.session_state.get('login_time', datetime.now())
    _render_pagina_conta(nome, usuario, perfil_label, inicial, login_time)
