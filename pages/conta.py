"""
Página de Conta & Configurações — compartilhada entre admin e aluno.
"""

import streamlit as st
from datetime import datetime
from data.mock_alunos import ALUNOS_MOCK


def render():
    usuario      = st.session_state.get('username', '—')
    role         = st.session_state.get('role', '—')
    perfil_label = 'Administrador' if role == 'admin' else 'Aluno'
    aluno_key    = st.session_state.get('aluno_key')

    if aluno_key and aluno_key in ALUNOS_MOCK:
        nome = ALUNOS_MOCK[aluno_key]['nome']
    else:
        nome = usuario.capitalize()
    inicial = nome[0].upper()

    login_time = st.session_state.get('login_time', datetime.now())
    delta      = datetime.now() - login_time
    minutos    = int(delta.total_seconds() // 60)
    segundos   = int(delta.total_seconds() % 60)
    tempo_str  = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
    hora_login = login_time.strftime('%H:%M:%S')

    st.markdown("""
    <style>
    .conta-inner p { margin: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("⚙️ Conta")

    st.markdown(f"""
    <div style="
        background:#132233;
        border:1px solid rgba(46,134,193,0.35);
        border-radius:14px;
        padding:32px;
        margin-bottom:24px;
    " class="conta-inner">
        <div style="display:flex;align-items:center;gap:20px;margin-bottom:24px">
            <div style="
                width:72px;height:72px;border-radius:50%;
                background:linear-gradient(135deg,#1B4F72,#2E86C1);
                display:flex;align-items:center;justify-content:center;
                font-size:32px;font-weight:700;color:white;flex-shrink:0;
            ">{inicial}</div>
            <div>
                <h2 style="color:#F4A261;margin:0">{nome}</h2>
                <p style="color:#8AAFC7;margin:4px 0 0 0">{perfil_label}</p>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
            <div style="background:#0D1B2A;border-radius:10px;padding:16px">
                <p style="color:#8AAFC7;font-size:0.8rem">CONTA LOGADA</p>
                <p style="color:#F4A261;font-weight:600;margin-top:4px">{usuario}</p>
            </div>
            <div style="background:#0D1B2A;border-radius:10px;padding:16px">
                <p style="color:#8AAFC7;font-size:0.8rem">TEMPO CONECTADO</p>
                <p style="color:#F4A261;font-weight:600;margin-top:4px">{tempo_str}</p>
            </div>
            <div style="background:#0D1B2A;border-radius:10px;padding:16px">
                <p style="color:#8AAFC7;font-size:0.8rem">PERFIL DE ACESSO</p>
                <p style="color:#F4A261;font-weight:600;margin-top:4px">{perfil_label}</p>
            </div>
            <div style="background:#0D1B2A;border-radius:10px;padding:16px">
                <p style="color:#8AAFC7;font-size:0.8rem">SESSÃO INICIADA EM</p>
                <p style="color:#F4A261;font-weight:600;margin-top:4px">{hora_login}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚪 Encerrar Sessão", use_container_width=True, type="primary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
