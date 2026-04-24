"""
📊 Datathon Passos Mágicos — Dashboard Analítico & Modelo Preditivo
Aplicação Streamlit standalone para análise de dados e predição de risco
de defasagem escolar na ONG Passos Mágicos.

Equipe FIAP PosTech — Fase 5
Estrutura: arquivo único, sem dependências de módulos externos.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import warnings
import joblib
import base64
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from data.mock_alunos import USERS, ALUNOS_MOCK

warnings.filterwarnings('ignore')

# =============================================================================
# FUNÇÕES DE DADOS (antes em src/data_loader.py)
# =============================================================================

def carregar_dataset_csv(caminho='data/PEDE_PASSOS_DATASET_FIAP.csv'):
    df = pd.read_csv(caminho, sep=';', encoding='latin1')
    indicadores = ['INDE','IAA','IEG','IPS','IDA','IPP','IPV','IAN']
    for ano in [2020, 2021, 2022]:
        sufixos = [f'{i}_{ano}' for i in indicadores]
        if ano == 2022:
            sufixos += [f'NOTA_PORT_{ano}', f'NOTA_MAT_{ano}', f'NOTA_ING_{ano}']
        for col in sufixos:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ['PEDRA_2020', 'PEDRA_2021', 'PEDRA_2022']:
        if col in df.columns:
            df[col] = df[col].replace({'Ã\x81gata': 'Ágata', 'TopÃ¡zio': 'Topázio',
                                        '#NULO!': np.nan, 'D9891/2A': np.nan})
    for col in ['PONTO_VIRADA_2020', 'PONTO_VIRADA_2021', 'PONTO_VIRADA_2022']:
        if col in df.columns:
            df[col] = df[col].replace({'NÃ£o': 'Não', '#NULO!': np.nan, 'D9600': np.nan})
    if 'FASE_TURMA_2020' in df.columns:
        df['FASE_2020'] = df['FASE_TURMA_2020'].apply(
            lambda x: int(x[0]) if pd.notna(x) and len(str(x)) > 0 and str(x)[0].isdigit() else np.nan)
    return df


def carregar_dataset_xlsx(caminho='data/BASE DE DADOS PEDE 2024 - DATATHON.xlsx'):
    df = pd.read_excel(caminho)
    rename_map = {
        'Fase':'FASE','Turma':'TURMA','Nome':'NOME','Ano nasc':'ANO_NASC',
        'Idade 22':'IDADE','Gênero':'GENERO','Ano ingresso':'ANO_INGRESSO',
        'Instituição de ensino':'INSTITUICAO_ENSINO',
        'Pedra 20':'PEDRA_2020','Pedra 21':'PEDRA_2021','Pedra 22':'PEDRA_2022',
        'INDE 22':'INDE','Cg':'CG','Cf':'CF','Ct':'CT',
        'Nº Av':'NUM_AVALIADORES','Avaliador1':'AVALIADOR_1','Rec Av1':'REC_AVAL_1',
        'Avaliador2':'AVALIADOR_2','Rec Av2':'REC_AVAL_2',
        'Avaliador3':'AVALIADOR_3','Rec Av3':'REC_AVAL_3',
        'Avaliador4':'AVALIADOR_4','Rec Av4':'REC_AVAL_4',
        'Rec Psicologia':'REC_PSICOLOGIA','Matem':'NOTA_MAT','Portug':'NOTA_PORT',
        'Inglês':'NOTA_ING','Indicado':'INDICADO_BOLSA','Atingiu PV':'PONTO_VIRADA',
        'Fase ideal':'FASE_IDEAL','Defas':'DEFASAGEM',
        'Destaque IEG':'DESTAQUE_IEG','Destaque IDA':'DESTAQUE_IDA','Destaque IPV':'DESTAQUE_IPV',
    }
    df = df.rename(columns=rename_map)
    df['ANOS_PM'] = 2022 - df['ANO_INGRESSO']
    return df


def criar_dataset_longitudinal(df_csv, df_xlsx=None):
    registros = []
    indicadores = ['INDE','IAA','IEG','IPS','IDA','IPP','IPV','IAN']
    for ano in [2020, 2021, 2022]:
        pedra_col = f'PEDRA_{ano}'
        pv_col    = f'PONTO_VIRADA_{ano}'
        fase_col  = f'FASE_{ano}' if f'FASE_{ano}' in df_csv.columns else None
        for _, row in df_csv.iterrows():
            if pd.isna(row.get(f'INDE_{ano}')): continue
            reg = {'NOME': str(row.get('NOME','')).upper(), 'ANO': ano}
            for ind in indicadores:
                col = f'{ind}_{ano}'
                if col in df_csv.columns: reg[ind] = row[col]
            if pedra_col in df_csv.columns: reg['PEDRA']        = row[pedra_col]
            if pv_col    in df_csv.columns: reg['PONTO_VIRADA'] = row[pv_col]
            if fase_col  and fase_col in df_csv.columns: reg['FASE'] = row[fase_col]
            registros.append(reg)
    if df_xlsx is not None:
        for _, row in df_xlsx.iterrows():
            if pd.isna(row.get('INDE')): continue
            reg = {'NOME': str(row.get('NOME','')).upper(), 'ANO': 2024}
            for ind in indicadores:
                if ind in df_xlsx.columns: reg[ind] = row[ind]
            if 'PEDRA_2022'   in df_xlsx.columns: reg['PEDRA']        = row['PEDRA_2022']
            if 'PONTO_VIRADA' in df_xlsx.columns: reg['PONTO_VIRADA'] = row['PONTO_VIRADA']
            if 'FASE'         in df_xlsx.columns: reg['FASE']         = row['FASE']
            registros.append(reg)
    return pd.DataFrame(registros)


def criar_dataset_modelo(df_xlsx):
    df = df_xlsx.copy()

    # ── Target ──────────────────────────────────────────────────────────────
    df['RISCO']      = (df['DEFASAGEM'] < 0).astype(int)

    # ── Encoding categórico ─────────────────────────────────────────────────
    df['GENERO_NUM'] = (df['GENERO'] == 'Menino').astype(int)
    df['PV_NUM']     = (df['PONTO_VIRADA'] == 'Sim').astype(int)

    # ── Features derivadas (sem leakage) ────────────────────────────────────
    # Score comportamental médio — combina as dimensões subjetivas
    df['SCORE_COMPORTAMENTAL'] = (df['IAA'] + df['IEG'] + df['IPS']) / 3

    # Desequilíbrio entre autopercepção e desempenho real
    df['GAP_IAA_IDA'] = df['IAA'] - df['IDA']

    # Nível de engajamento relativo à fase (alunos em fases mais avançadas
    # com baixo engajamento têm maior risco)
    df['IEG_POR_FASE'] = df['IEG'] / (df['FASE'] + 1)

    # Interação engajamento × ponto de virada — sinal combinado forte
    df['IEG_X_IPV'] = df['IEG'] * df['IPV']

    # Interação desempenho acadêmico × anos no programa
    # (alunos com muitos anos e IDA baixo têm risco acumulado)
    df['IDA_X_ANOS'] = df['IDA'] * df['ANOS_PM']

    features = [
        'IAA', 'IEG', 'IPS', 'IDA', 'IPV',
        'FASE', 'ANOS_PM', 'GENERO_NUM', 'PV_NUM',
        'SCORE_COMPORTAMENTAL', 'GAP_IAA_IDA',
        'IEG_POR_FASE', 'IEG_X_IPV', 'IDA_X_ANOS',
    ]

    df_modelo = df.dropna(subset=['IAA','IEG','IPS','IDA','IPV','FASE','ANOS_PM'])
    return df_modelo, features


def classificar_risco_ian(valor):
    if pd.isna(valor):    return 'Sem dados'
    if valor >= 8:        return 'Adequado'
    if valor >= 5:        return 'Moderadamente defasado'
    if valor >= 2.5:      return 'Severamente defasado'
    return 'Criticamente defasado'


def classificar_pedra(inde):
    if pd.isna(inde):  return 'Sem classificação'
    if inde < 5.506:   return 'Quartzo'
    if inde < 6.868:   return 'Ágata'
    if inde < 8.230:   return 'Ametista'
    return 'Topázio'


# =============================================================================
# PALETAS E TEMPLATE (antes em src/analysis.py)
# =============================================================================

CORES_PEDRAS = {'Quartzo':'#9B59B6','Ágata':'#3498DB','Ametista':'#8E44AD','Topázio':'#F39C12'}
CORES_RISCO  = {'Adequado':'#2ECC71','Moderadamente defasado':'#F39C12',
                'Severamente defasado':'#E74C3C','Criticamente defasado':'#C0392B','Sem dados':'#95A5A6'}
TEMPLATE     = 'plotly_white'


# =============================================================================
# FUNÇÕES DE ANÁLISE (antes em src/analysis.py)
# =============================================================================

def analise_ian(df_long):
    df = df_long.copy()
    df['RISCO_IAN'] = df['IAN'].apply(classificar_risco_ian)
    dist   = df.groupby(['ANO','RISCO_IAN']).size().reset_index(name='N')
    totais = df.groupby('ANO').size().reset_index(name='TOTAL')
    dist   = dist.merge(totais, on='ANO')
    dist['PERCENTUAL'] = (dist['N'] / dist['TOTAL'] * 100).round(1)
    fig1 = px.bar(dist, x='ANO', y='PERCENTUAL', color='RISCO_IAN',
                  color_discrete_map=CORES_RISCO,
                  title='📊 Como a adequação dos alunos ao nível evoluiu ao longo dos anos',
                  labels={'PERCENTUAL':'Percentual (%)','ANO':'Ano','RISCO_IAN':'Classificação'},
                  barmode='group', template=TEMPLATE)
    fig1.update_layout(legend_title_text='Classificação')
    media = df.groupby('ANO')['IAN'].agg(['mean','median','std']).reset_index()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=media['ANO'], y=media['mean'], mode='lines+markers',
                               name='Média IAN', line=dict(color='#E74C3C', width=3), marker=dict(size=12)))
    fig2.add_trace(go.Scatter(x=media['ANO'], y=media['median'], mode='lines+markers',
                               name='Mediana IAN', line=dict(color='#3498DB', width=3, dash='dash'), marker=dict(size=12)))
    fig2.update_layout(title='📈 Tendência da adequação ao nível (IAN) ao longo do tempo',
                       xaxis_title='Ano', yaxis_title='IAN', template=TEMPLATE)
    return {'fig_ian_evolucao': fig1, 'fig_ian_media': fig2, 'stats_ian': media}


def analise_ida(df_long):
    media = df_long.groupby('ANO')['IDA'].agg(['mean','median','std']).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=media['ANO'], y=media['mean'], mode='lines+markers+text',
                              text=media['mean'].round(2), textposition='top center',
                              name='Média IDA', line=dict(color='#2ECC71', width=3), marker=dict(size=14)))
    fig.add_trace(go.Bar(x=media['ANO'], y=media['std'], name='Desvio Padrão',
                          marker_color='rgba(46,204,113,0.3)', yaxis='y2'))
    fig.update_layout(title='📚 Como o desempenho acadêmico evoluiu ao longo dos anos', xaxis_title='Ano',
                      yaxis_title='IDA Médio',
                      yaxis2=dict(title='Desvio Padrão', overlaying='y', side='right'),
                      template=TEMPLATE)
    res = {'fig_ida_evolucao': fig, 'stats_ida': media}
    if 'PEDRA' in df_long.columns:
        ip = df_long.groupby(['ANO','PEDRA'])['IDA'].mean().reset_index().dropna(subset=['PEDRA'])
        res['fig_ida_pedra'] = px.line(ip, x='ANO', y='IDA', color='PEDRA',
                                        color_discrete_map=CORES_PEDRAS,
                                        title='📊 Desempenho acadêmico por nível de classificação', markers=True, template=TEMPLATE)
    return res


def analise_engajamento(df_long):
    dv = df_long.dropna(subset=['IEG','IDA','IPV'])
    f1 = px.scatter(dv, x='IEG', y='IDA', color='ANO', trendline='ols',
                    title='🎯 Alunos mais engajados têm melhor desempenho acadêmico?', template=TEMPLATE, opacity=0.6)
    f2 = px.scatter(dv, x='IEG', y='IPV', color='ANO', trendline='ols',
                    title='🔄 O engajamento antecipa o alcance do Ponto de Virada?', template=TEMPLATE, opacity=0.6)
    return {'fig_ieg_ida': f1, 'fig_ieg_ipv': f2,
            'corr_ieg_ida': dv[['IEG','IDA']].corr().iloc[0,1],
            'corr_ieg_ipv': dv[['IEG','IPV']].corr().iloc[0,1]}


def analise_autoavaliacao(df_long):
    dv = df_long.dropna(subset=['IAA','IDA','IEG']).copy()
    dv['DIFERENCA_IAA_IDA'] = dv['IAA'] - dv['IDA']
    f1 = px.histogram(dv, x='DIFERENCA_IAA_IDA', color='ANO', nbins=30, barmode='overlay',
                      title='📋 Os alunos se avaliam de forma coerente com seu desempenho real?', template=TEMPLATE, opacity=0.7)
    f1.add_vline(x=0, line_dash='dash', line_color='#6B3FA0', annotation_text='IAA = IDA')
    f2 = px.scatter(dv, x='IAA', y='IDA', color='ANO', trendline='ols',
                    title='🔍 Autopercepção do aluno vs Desempenho real', template=TEMPLATE, opacity=0.6)
    f2.add_trace(go.Scatter(x=[0,10], y=[0,10], mode='lines',
                             line=dict(dash='dash', color='rgba(107,63,160,0.4)'), name='IAA=IDA'))
    return {'fig_iaa_ida_diff': f1, 'fig_iaa_ida_scatter': f2,
            'corr_iaa_ida': dv[['IAA','IDA']].corr().iloc[0,1],
            'media_diferenca': dv['DIFERENCA_IAA_IDA'].mean()}


def analise_psicossocial(df_long):
    dv = df_long.dropna(subset=['IPS','IDA','IEG'])
    f1 = px.scatter(dv, x='IPS', y='IDA', color='ANO', trendline='ols',
                    title='🧠 O suporte psicossocial influencia o desempenho acadêmico?', template=TEMPLATE, opacity=0.6)
    f2 = px.scatter(dv, x='IPS', y='IEG', color='ANO', trendline='ols',
                    title='🧠 O suporte psicossocial influencia o engajamento do aluno?', template=TEMPLATE, opacity=0.6)
    dc = dv.copy()
    dc['IPS_GRUPO'] = pd.cut(dc['IPS'], bins=[0,4,6,8,10], labels=['Muito Baixo','Baixo','Médio','Alto'])
    gp = dc.groupby('IPS_GRUPO', observed=True).agg({'IDA':'mean','IEG':'mean','INDE':'mean'}).reset_index()
    f3 = go.Figure()
    for col, cor in [('IDA','#2ECC71'),('IEG','#3498DB'),('INDE','#E74C3C')]:
        if col in gp.columns:
            f3.add_trace(go.Bar(x=gp['IPS_GRUPO'], y=gp[col], name=col, marker_color=cor))
    f3.update_layout(title='📊 Desempenho médio dos alunos por nível de suporte psicossocial', barmode='group',
                     template=TEMPLATE, xaxis_title='Grupo IPS', yaxis_title='Média')
    return {'fig_ips_ida': f1, 'fig_ips_ieg': f2, 'fig_ips_grupos': f3,
            'corr_ips_ida': dv[['IPS','IDA']].corr().iloc[0,1],
            'corr_ips_ieg': dv[['IPS','IEG']].corr().iloc[0,1]}


def analise_psicopedagogico(df_long):
    dv = df_long.dropna(subset=['IPP','IAN'])
    f1 = px.scatter(dv, x='IPP', y='IAN', color='ANO', trendline='ols',
                    title='📝 A avaliação psicopedagógica confirma a adequação ao nível?', template=TEMPLATE, opacity=0.6)
    dc = dv.copy()
    dc['RISCO_IAN'] = dc['IAN'].apply(classificar_risco_ian)
    gp = dc.groupby('RISCO_IAN')['IPP'].agg(['mean','std']).reset_index()
    f2 = px.bar(gp, x='RISCO_IAN', y='mean', error_y='std', color='RISCO_IAN',
                color_discrete_map=CORES_RISCO, title='📊 Avaliação psicopedagógica por grau de adequação ao nível', template=TEMPLATE)
    return {'fig_ipp_ian': f1, 'fig_ipp_por_risco': f2,
            'corr_ipp_ian': dv[['IPP','IAN']].corr().iloc[0,1]}


def analise_ponto_virada(df_long):
    dv = df_long.dropna(subset=['IPV','IDA','IEG','IAA','IPS','IPP'])
    inds = ['IDA','IEG','IAA','IPS','IPP','IAN']
    corrs = {i: dv[['IPV',i]].corr().iloc[0,1] for i in inds if i in dv.columns}
    cdf = pd.DataFrame({'Indicador': list(corrs.keys()), 'Correlação com IPV': list(corrs.values())}).sort_values('Correlação com IPV')
    f1 = px.bar(cdf, x='Correlação com IPV', y='Indicador', orientation='h',
                color='Correlação com IPV', color_continuous_scale='RdYlGn',
                title='🏆 Quais fatores mais influenciam o Ponto de Virada?', template=TEMPLATE)
    res = {'fig_ipv_correlacoes': f1, 'correlacoes_ipv': corrs}
    if 'PONTO_VIRADA' in dv.columns:
        pvc = dv.groupby('PONTO_VIRADA')[inds].mean().T.reset_index()
        pvc.columns = ['Indicador'] + list(pvc.columns[1:])
        if 'Sim' in pvc.columns and 'Não' in pvc.columns:
            f2 = go.Figure()
            f2.add_trace(go.Bar(x=pvc['Indicador'], y=pvc['Não'], name='Não atingiu PV', marker_color='#E74C3C'))
            f2.add_trace(go.Bar(x=pvc['Indicador'], y=pvc['Sim'], name='Atingiu PV', marker_color='#2ECC71'))
            f2.update_layout(title='🔄 Perfil dos alunos que alcançaram o Ponto de Virada',
                             barmode='group', template=TEMPLATE)
            res['fig_ipv_comparacao'] = f2
    return res


def analise_multidimensional(df_long):
    inds = ['IDA','IEG','IPS','IPP','IAA','IPV','IAN']
    dv = df_long.dropna(subset=inds + ['INDE'])
    cm = dv[inds + ['INDE']].corr()
    f1 = px.imshow(cm.values, x=cm.columns, y=cm.index, color_continuous_scale='RdBu_r',
                   title='🔗 Como os indicadores se relacionam entre si',
                   template=TEMPLATE, text_auto='.2f', aspect='auto')
    ci = cm['INDE'].drop('INDE').sort_values()
    f2 = px.bar(x=ci.values, y=ci.index, orientation='h', color=ci.values,
                color_continuous_scale='Viridis', title='📊 Quais indicadores mais impactam o score educacional geral?',
                labels={'x':'Correlação','y':'Indicador'}, template=TEMPLATE)
    res = {'fig_correlacao_matrix': f1, 'fig_importancia_inde': f2, 'correlacao_inde': ci.to_dict()}
    if 'PEDRA' in dv.columns:
        pm = dv.groupby('PEDRA')[inds].mean().reindex(['Quartzo','Ágata','Ametista','Topázio']).dropna()
        f3 = go.Figure()
        for pedra in pm.index:
            vals = pm.loc[pedra].tolist(); vals.append(vals[0])
            cats = inds + [inds[0]]
            f3.add_trace(go.Scatterpolar(r=vals, theta=cats, fill='toself', name=pedra,
                                          line_color=CORES_PEDRAS.get(pedra,'#95A5A6')))
        f3.update_layout(title='🎯 Perfil completo de cada nível de classificação',
                         polar=dict(radialaxis=dict(visible=True, range=[0,10])), template=TEMPLATE)
        res['fig_radar_pedra'] = f3
    return res


def analise_efetividade(df_long, df_xlsx=None):
    res = {}
    if 'PEDRA' in df_long.columns:
        pa = df_long.groupby(['ANO','PEDRA']).agg(INDE=('INDE','mean'), IDA=('IDA','mean'),
                                                    IEG=('IEG','mean')).reset_index().dropna(subset=['PEDRA'])
        res['fig_inde_pedra_evolucao'] = px.line(pa, x='ANO', y='INDE', color='PEDRA',
                                                   color_discrete_map=CORES_PEDRAS, markers=True,
                                                   title='📈 Como cada nível de classificação progrediu ao longo dos anos', template=TEMPLATE)
    pd_ = df_long.groupby(['ANO','PEDRA']).size().reset_index(name='N').dropna(subset=['PEDRA'])
    tot = df_long.groupby('ANO').size().reset_index(name='TOTAL')
    pd_ = pd_.merge(tot, on='ANO')
    pd_['PERCENTUAL'] = (pd_['N'] / pd_['TOTAL'] * 100).round(1)
    res['fig_pedra_distribuicao'] = px.bar(pd_, x='ANO', y='PERCENTUAL', color='PEDRA',
                                            color_discrete_map=CORES_PEDRAS,
                                            title='📊 Como os alunos estão progredindo nos níveis educacionais ao longo dos anos',
                                            barmode='stack', template=TEMPLATE)
    if 'PONTO_VIRADA' in df_long.columns:
        pv = df_long.groupby('ANO')['PONTO_VIRADA'].apply(
            lambda x: (x=='Sim').sum()/len(x)*100).reset_index(name='TAXA_PV')
        f = px.bar(pv, x='ANO', y='TAXA_PV', title='🏆 Proporção de alunos que alcançaram o Ponto de Virada por ano',
                   color='TAXA_PV', color_continuous_scale='Greens', template=TEMPLATE)
        f.update_layout(yaxis_title='% Alunos')
        res['fig_taxa_pv'] = f
    return res


def analise_insights(df_xlsx):
    res = {}
    if 'GENERO' in df_xlsx.columns:
        cols = [c for c in ['INDE','IDA','IEG','IAA','IPS','IPV'] if c in df_xlsx.columns]
        gen = df_xlsx.groupby('GENERO')[cols].mean().T.reset_index()
        gen.columns = ['Indicador'] + list(gen.columns[1:])
        f = go.Figure()
        for g, cor in [('Menina','#FF69B4'),('Menino','#4169E1')]:
            if g in gen.columns:
                f.add_trace(go.Bar(x=gen['Indicador'], y=gen[g], name=g, marker_color=cor))
        f.update_layout(title='👫 Comparativo de indicadores: meninas e meninos', barmode='group', template=TEMPLATE)
        res['fig_genero'] = f
    if 'ANOS_PM' in df_xlsx.columns:
        cols = [c for c in ['INDE','IDA','IEG'] if c in df_xlsx.columns]
        ap = df_xlsx.groupby('ANOS_PM')[cols].mean().reset_index()
        res['fig_anos_pm'] = px.line(ap, x='ANOS_PM', y=cols, markers=True,
                                      title='⏰ Quanto mais tempo na Passos Mágicos, melhores os indicadores?',
                                      labels={'ANOS_PM':'Anos na PM','value':'Média','variable':'Indicador'},
                                      template=TEMPLATE)
    if 'IDADE' in df_xlsx.columns:
        res['fig_idade'] = px.histogram(df_xlsx, x='IDADE',
                                         color='GENERO' if 'GENERO' in df_xlsx.columns else None,
                                         nbins=15, barmode='overlay', opacity=0.7,
                                         title='📊 Quais são as faixas etárias atendidas pelo programa?',
                                         color_discrete_map={'Menina':'#FF69B4','Menino':'#4169E1'},
                                         template=TEMPLATE)
    if 'FASE' in df_xlsx.columns:
        cols = [c for c in ['INDE','IDA','IEG','IAA','IPS'] if c in df_xlsx.columns]
        fs = df_xlsx.groupby('FASE')[cols].mean().reset_index()
        res['fig_fase'] = px.line(fs, x='FASE', y=cols, markers=True,
                                   title='📚 Como os indicadores se desenvolvem em cada fase do programa', template=TEMPLATE,
                                   labels={'FASE':'Fase','value':'Média','variable':'Indicador'})
    if 'INDICADO_BOLSA' in df_xlsx.columns:
        cols = [c for c in ['INDE','IDA','IEG'] if c in df_xlsx.columns]
        bs = df_xlsx.groupby('INDICADO_BOLSA')[cols].mean().reset_index()
        res['fig_bolsa'] = px.bar(bs, x='INDICADO_BOLSA', y=cols, barmode='group',
                                   title='🎓 Perfil dos alunos indicados para bolsa vs demais', template=TEMPLATE)
    return res


# =============================================================================
# CLASSE DO MODELO (antes em src/model.py)
# =============================================================================

class ModeloRiscoDefasagem:
    def __init__(self):
        self.resultados = {}
        self.melhor_modelo = None
        self.melhor_nome = None
        self.scaler = StandardScaler()
        self.features = None
        self.feature_importance = None
        self.melhor_threshold = 0.5

    def predizer_risco(self, dados_aluno):
        if self.melhor_modelo is None: raise ValueError("Modelo não treinado!")
        df_a = pd.DataFrame([dados_aluno])

        # Recalcular features derivadas para o aluno individual
        df_a['SCORE_COMPORTAMENTAL'] = (df_a.get('IAA', 0) + df_a.get('IEG', 0) + df_a.get('IPS', 0)) / 3
        df_a['GAP_IAA_IDA']  = df_a.get('IAA', 0) - df_a.get('IDA', 0)
        df_a['IEG_POR_FASE'] = df_a.get('IEG', 0) / (df_a.get('FASE', 1) + 1)
        df_a['IEG_X_IPV']    = df_a.get('IEG', 0) * df_a.get('IPV', 0)
        df_a['IDA_X_ANOS']   = df_a.get('IDA', 0) * df_a.get('ANOS_PM', 0)

        for f in self.features:
            if f not in df_a.columns: df_a[f] = 0
        df_a = df_a[self.features]

        usa_scale = self.melhor_nome == 'Logistic Regression'
        inp  = self.scaler.transform(df_a) if usa_scale else df_a
        prob = self.melhor_modelo.predict_proba(inp)[0]

        # Usar threshold calibrado (se disponível)
        thr  = getattr(self, 'melhor_threshold', 0.5)
        pred = int(prob[1] >= thr)

        return {'risco': pred,
                'probabilidade_sem_risco': float(prob[0]),
                'probabilidade_risco':     float(prob[1]),
                'threshold_usado':         thr,
                'classificacao': 'EM RISCO' if pred == 1 else 'SEM RISCO'}

    def salvar_modelo(self, caminho='models/risco_defasagem.joblib'):
        art = {'modelo': self.melhor_modelo, 'scaler': self.scaler,
               'features': self.features, 'melhor_nome': self.melhor_nome,
               'melhor_threshold': getattr(self, 'melhor_threshold', 0.5),
               'resultados': {n: {k: v for k, v in r.items()
                                  if k in ['accuracy','precision','recall','f1_score','roc_auc',
                                           'threshold','cv_acc_mean','cv_acc_std']}
                              for n, r in self.resultados.items()}}
        if self.feature_importance is not None:
            art['feature_importance'] = self.feature_importance
        joblib.dump(art, caminho)

    @staticmethod
    def carregar_modelo(caminho='models/risco_defasagem.joblib'):
        art = joblib.load(caminho)
        inst = ModeloRiscoDefasagem()
        inst.melhor_modelo      = art['modelo']
        inst.scaler             = art['scaler']
        inst.features           = art['features']
        inst.melhor_nome        = art['melhor_nome']
        inst.resultados         = art.get('resultados', {})
        inst.feature_importance = art.get('feature_importance', None)
        inst.melhor_threshold   = art.get('melhor_threshold', 0.5)
        return inst


# =============================================================================
# MODELO DE ENQUADRAMENTO DE PEDRA (carrega .joblib)
# =============================================================================

class ModeloEnquadramentoPedra:
    """Carrega o modelo de enquadramento de Pedra (classificacao multiclasse)."""

    def __init__(self):
        self.modelo            = None
        self.label_encoder     = None
        self.classes           = []
        self.features          = []
        self.feature_importance = None
        self.resultados        = {}

    def predizer_pedra(self, dados_aluno: dict) -> dict:
        if self.modelo is None:
            raise ValueError("Modelo nao carregado!")
        df_a = pd.DataFrame([dados_aluno])
        for f in self.features:
            if f not in df_a.columns:
                df_a[f] = 0
        X    = df_a[self.features].values
        prob = self.modelo.predict_proba(X)[0]
        idx  = int(np.argmax(prob))
        pred = self.label_encoder.inverse_transform([idx])[0]
        return {
            'pedra':        pred,
            'probabilidades': dict(zip(self.classes, prob.tolist())),
            'confianca':    float(np.max(prob)),
        }

    @staticmethod
    def carregar(caminho='models/enquadramento_pedra.joblib'):
        art  = joblib.load(caminho)
        inst = ModeloEnquadramentoPedra()
        inst.modelo             = art['modelo']
        inst.label_encoder      = art['label_encoder']
        inst.classes            = art.get('classes', [])
        inst.features           = art['features']
        inst.feature_importance = art.get('feature_importance', None)
        inst.resultados         = art.get('resultados', {})
        return inst


def carregar_modelo_pedra():
    try:
        return ModeloEnquadramentoPedra.carregar('models/enquadramento_pedra.joblib')
    except Exception:
        return None


# =============================================================================
# MODELO DE PONTO DE VIRADA (carrega .joblib)
# =============================================================================

class ModeloPontoVirada:
    def __init__(self):
        self.modelo = None
        self.features = []
        self.feature_importance = None
        self.resultados = {}
        self.melhor_nome = None
        self.inst_map = {}

    def predizer_pv(self, dados_aluno: dict) -> dict:
        if self.modelo is None:
            raise ValueError("Modelo nao carregado!")
        df_a = pd.DataFrame([dados_aluno])
        for f in self.features:
            if f not in df_a.columns:
                df_a[f] = 0
        prob = self.modelo.predict_proba(df_a[self.features].values)[0]
        return {
            'atingiu': int(prob[1] >= 0.5),
            'probabilidade': float(prob[1]),
        }

    @staticmethod
    def carregar(caminho='models/ponto_virada.joblib'):
        art = joblib.load(caminho)
        inst = ModeloPontoVirada()
        inst.modelo = art['modelo']
        inst.features = art['features']
        inst.melhor_nome = art.get('melhor_nome', '')
        inst.feature_importance = art.get('feature_importance', None)
        inst.resultados = art.get('resultados', {})
        inst.inst_map = art.get('inst_map', {})
        return inst


@st.cache_resource
def carregar_modelo_pv():
    try:
        return ModeloPontoVirada.carregar('models/ponto_virada.joblib')
    except Exception:
        return None


# =============================================================================
# MODELO DE RISCO DE PERMANÊNCIA / CHURN (carrega .joblib)
# =============================================================================

class ModeloChurn:
    def __init__(self):
        self.modelo = None
        self.features = []
        self.feature_importance = None
        self.resultados = {}
        self.inst_map = {}

    def predizer_churn(self, dados_aluno: dict) -> dict:
        if self.modelo is None:
            raise ValueError("Modelo não carregado!")
        df_a = pd.DataFrame([dados_aluno])
        for f in self.features:
            if f not in df_a.columns:
                df_a[f] = 0.0
        prob = self.modelo.predict_proba(df_a[self.features].values)[0]
        return {
            'em_risco': int(prob[1] >= 0.5),
            'probabilidade': float(prob[1]),
        }

    def predizer_lote(self, df: pd.DataFrame) -> pd.DataFrame:
        df_f = df.copy()
        for f in self.features:
            if f not in df_f.columns:
                df_f[f] = 0.0
        probs = self.modelo.predict_proba(df_f[self.features].fillna(0).values)[:, 1]
        return probs

    @staticmethod
    def carregar(caminho='models/churn.joblib'):
        art = joblib.load(caminho)
        inst = ModeloChurn()
        inst.modelo = art['modelo']
        inst.features = art['features']
        inst.feature_importance = art.get('feature_importance', None)
        inst.resultados = art.get('resultados', {})
        inst.inst_map = art.get('inst_map', {})
        return inst


@st.cache_resource
def carregar_modelo_churn():
    try:
        return ModeloChurn.carregar('models/churn.joblib')
    except Exception:
        return None


_PEDRA_ORD = {'Quartzo': 1, 'Agata': 2, 'Ágata': 2, 'Ametista': 3, 'Topazio': 4, 'Topázio': 4}
_PEDRA_ICONE = {'Quartzo': '⬜', 'Agata': '🟣', 'Ágata': '🟣', 'Ametista': '💜', 'Topazio': '💎', 'Topázio': '💎'}
_PEDRA_COR = {
    'Quartzo': '#78909C', 'Agata': '#42A5F5', 'Ágata': '#42A5F5',
    'Ametista': '#AB47BC', 'Topazio': '#FFD740', 'Topázio': '#FFD740',
}


def calcular_alerta_evasao(row):
    sinais, descricoes = 0, []
    if row.get('IEG', 10) < 5.5:
        sinais += 1; descricoes.append("Engajamento crítico (IEG < 5.5)")
    if row.get('IPS', 10) < 5.0:
        sinais += 1; descricoes.append("Aspecto psicossocial crítico (IPS < 5.0)")
    if row.get('IDA', 10) < 5.5:
        sinais += 1; descricoes.append("Desempenho acadêmico baixo (IDA < 5.5)")
    if row.get('EVOLUCAO_PEDRA', 0) < 0:
        sinais += 1; descricoes.append("Regrediu de nível de classificação")
    if row.get('ANOS_PM', 0) > 4 and row.get('EVOLUCAO_PEDRA', 0) <= 0:
        sinais += 1; descricoes.append("Estagnado há mais de 4 anos")
    if sinais >= 3:
        return 'Alto', sinais, descricoes
    if sinais >= 2:
        return 'Moderado', sinais, descricoes
    return 'Baixo', sinais, descricoes


# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="Passos Mágicos - Datathon Analytics",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# LOGIN — gate must come right after set_page_config
# =============================================================================
def _render_login():
    from PIL import Image
    import io as _io

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap');
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0D1B2A !important;
        font-family: 'Montserrat', sans-serif !important;
    }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"]  { background: transparent !important; }
    label { color: #C8CDD8 !important; }
    [data-testid="stTextInput"] > div > input {
        background: #0D1B2A !important;
        color: #E8EAF0 !important;
        border: 1px solid #2A3F55 !important;
        border-radius: 8px !important;
    }
    [data-testid="stButton"] > button {
        background: #2D325E !important; color: #F4B41A !important;
        border: 1px solid #4A4F7A !important; border-radius: 8px !important;
        font-weight: 700 !important; width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Processar logo — remove fundo branco
    _src = None
    for _lp in ["assets/logo_passos_magicos.png", "assets/logo.png"]:
        if Path(_lp).exists():
            try:
                _img = Image.open(_lp).convert("RGBA")
                _img.putdata([
                    (r, g, b, 0) if (r > 200 and g > 200 and b > 200) else (r, g, b, a)
                    for r, g, b, a in _img.getdata()
                ])
                _buf = _io.BytesIO()
                _img.save(_buf, format="PNG")
                _src = f"data:image/png;base64,{base64.b64encode(_buf.getvalue()).decode()}"
            except Exception:
                with open(_lp, "rb") as _f:
                    _src = f"data:image/png;base64,{base64.b64encode(_f.read()).decode()}"
            break

    _logo_tag = (
        f'<img src="{_src}" style="width:130px; background:transparent; border:none; '
        'box-shadow:none; filter: drop-shadow(0 4px 20px rgba(244,162,97,0.4));">'
        if _src else ''
    )

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align:center; padding: 40px 0 8px 0">
            {_logo_tag}
        </div>
        <h1 style="text-align:center; color:#F4A261;
                   margin:12px 0 4px 0; font-size:2rem; font-weight:700">
            ✨ Passos Mágicos
        </h1>
        <p style="text-align:center; color:#8AAFC7;
                  margin:0 0 28px 0; font-size:0.9rem; letter-spacing:0.3px">
            Plataforma de Análise Educacional
        </p>
        """, unsafe_allow_html=True)

        usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="login_user")
        senha   = st.text_input("Senha", type="password", placeholder="Digite sua senha", key="login_pass")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Entrar", use_container_width=True, type="primary"):
            user_data = USERS.get(usuario)
            if user_data and user_data['password'] == senha:
                st.session_state['logged_in']  = True
                st.session_state['role']       = user_data['role']
                st.session_state['username']   = usuario
                st.session_state['aluno_key']  = user_data['aluno_key']
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

        st.markdown("""
        <p style="text-align:center; color:#4A6278;
                  font-size:0.75rem; margin-top:24px">
            Datathon Analytics — acesso restrito
        </p>
        <p style="text-align:center; color:#3A5A7A; font-size:0.72rem; margin-top:4px">
            admin / admin123 &nbsp;·&nbsp; aluno01–03 / 1234
        </p>
        """, unsafe_allow_html=True)


if not st.session_state.get('logged_in'):
    _render_login()
    st.stop()

if st.session_state.get('role') == 'aluno':
    from pages.aluno import render as _render_aluno
    aluno_key = st.session_state['aluno_key']
    aluno_data = ALUNOS_MOCK[aluno_key]
    with st.sidebar:
        st.image('assets/logo.png', use_container_width=True)
        st.markdown("---")
        st.markdown(f"""
        <div style='text-align:center; color:#C8CDD8; font-size:0.82rem; padding:0.5rem 0;'>
            👤 <strong>{aluno_data['nome']}</strong><br>
            <span style='opacity:0.6;'>{aluno_data['pedra']} · Fase {aluno_data['fase']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 Sair", key="logout_aluno"):
            for k in ['logged_in', 'role', 'username', 'aluno_key']:
                st.session_state.pop(k, None)
            st.rerun()
    _render_aluno(aluno_key, aluno_data)
    st.stop()

# =============================================================================
# CSS CUSTOMIZADO
# =============================================================================
st.markdown("""
<style>
    /* ═══ Remove navegação automática de pages/ — todas as versões ═══ */
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebarNav"] + div { display: none !important; }
    [data-testid="stSidebarNav"] + hr { display: none !important; }
    section[data-testid="stSidebar"] ul { display: none !important; }
    section[data-testid="stSidebar"] li { display: none !important; }
    section[data-testid="stSidebar"] a[href] { display: none !important; }
    nav[data-testid="stSidebarNav"] { display: none !important; }

    /* ═══ Google Fonts — Montserrat + Material Icons ═══ */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

    /* ═══ Variáveis de Design Passos Mágicos (site oficial) ═══ */
    :root {
        --pm-roxo: #2D325E;
        --pm-roxo-escuro: #1E2245;
        --pm-roxo-claro: #4A4F7A;
        --pm-amarelo: #F4B41A;
        --pm-amarelo-claro: #FFD740;
        --pm-laranja: #EE8133;
        --pm-vermelho: #D84C51;
        --pm-fundo: #FAFAFA;
        --pm-branco: #FFFFFF;
        --pm-texto: #333333;
        --pm-texto-leve: #555555;
        --pm-borda: #E0E0E0;
        --pm-sombra: rgba(45, 50, 94, 0.10);
    }

    /* ═══ Base & Tipografia ═══ */
    html, body, .main, .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Montserrat', sans-serif !important;
        background-color: var(--pm-fundo) !important;
    }

    .stApp {
        background: var(--pm-fundo) !important;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Montserrat', sans-serif !important;
        color: var(--pm-texto) !important;
        font-weight: 700 !important;
    }

    p, span, label, div, li, td, th {
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Correção de renderização de ícones do Streamlit (Material Icons) com alta especificidade */
    span.material-symbols-rounded, 
    div.material-symbols-rounded,
    .material-icons, 
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stIconMaterial"],
    .stIcon {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        font-feature-settings: 'liga' !important;
    }

    /* ═══ Header — Faixa Roxa Institucional ═══ */
    .main-header {
        background: linear-gradient(135deg, var(--pm-roxo) 0%, var(--pm-roxo-escuro) 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px var(--pm-sombra);
        position: relative;
        overflow: hidden;
    }

    .main-header::before {
        content: '✨';
        position: absolute;
        top: 12px;
        left: 20px;
        font-size: 2rem;
        opacity: 0.25;
    }

    .main-header::after {
        content: '⭐';
        position: absolute;
        bottom: 12px;
        right: 20px;
        font-size: 1.6rem;
        opacity: 0.25;
    }

    .main-header h1 {
        color: var(--pm-branco) !important;
        font-size: 2.4rem;
        margin: 0;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .main-header p {
        color: rgba(255,255,255,0.90);
        font-size: 1.05rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }

    /* ═══ KPI Cards — Branco + Roxo ═══ */
    .kpi-card {
        background: var(--pm-branco);
        border: 1px solid var(--pm-borda);
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 12px var(--pm-sombra);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px var(--pm-sombra);
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: var(--pm-roxo);
        margin: 0.5rem 0;
    }

    .kpi-label {
        color: var(--pm-texto-leve);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
    }

    /* ═══ Section Headers — Borda Roxa ═══ */
    .section-header {
        background: var(--pm-branco);
        border-left: 5px solid var(--pm-roxo);
        padding: 1rem 1.5rem;
        border-radius: 0 12px 12px 0;
        margin: 2rem 0 1rem;
        box-shadow: 0 2px 8px var(--pm-sombra);
    }

    .section-header h2 {
        color: var(--pm-roxo) !important;
        margin: 0;
        font-size: 1.4rem;
        font-weight: 700 !important;
    }

    /* ═══ Insight Box — Amarelo Dourado ═══ */
    .insight-box {
        background: linear-gradient(135deg, #FFFDE7 0%, #FFF8E1 100%);
        border: 1px solid var(--pm-amarelo);
        border-left: 5px solid var(--pm-amarelo);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
    }

    .insight-box p, .insight-box li {
        color: var(--pm-texto) !important;
        margin: 0;
        line-height: 1.6;
    }

    .insight-box strong {
        color: var(--pm-roxo-escuro) !important;
    }

    /* ═══ Risk Indicators ═══ */
    .risk-high {
        background: linear-gradient(135deg, var(--pm-vermelho) 0%, #C62828 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 14px;
        text-align: center;
        font-size: 1.4rem;
        font-weight: 700;
        box-shadow: 0 6px 20px rgba(229, 57, 53, 0.35);
    }

    .risk-low {
        background: linear-gradient(135deg, #43A047 0%, #2E7D32 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 14px;
        text-align: center;
        font-size: 1.4rem;
        font-weight: 700;
        box-shadow: 0 6px 20px rgba(46, 125, 50, 0.35);
    }

    /* ═══ Sidebar — Azul Marinho PM ═══ */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--pm-roxo) 0%, var(--pm-roxo-escuro) 100%) !important;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.15) !important;
    }

    /* ═══ Branding — Ocultar menu/footer/deploy ═══ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none !important;}

    /* ═══ Fix sidebar toggle button icon ═══ */
    [data-testid="collapsedControl"] span,
    [data-testid="stSidebarCollapsedControl"] span,
    button[data-testid="baseButton-header"] span {
        font-size: 0 !important;
        visibility: hidden;
    }
    [data-testid="collapsedControl"] span::after,
    [data-testid="stSidebarCollapsedControl"] span::after,
    button[data-testid="baseButton-header"] span::after {
        content: "☰";
        font-size: 1.4rem;
        visibility: visible;
        color: #2D325E;
    }
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        background: white !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
        border: 1px solid #E0E0E0 !important;
    }

    /* ═══ Metrics — Roxo ═══ */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: var(--pm-roxo) !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--pm-texto-leve) !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.75rem !important;
        letter-spacing: 0.5px;
    }

    /* ═══ Tabs — Roxo + Amarelo ═══ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: var(--pm-branco);
        border: 1px solid var(--pm-borda);
        border-radius: 10px;
        padding: 10px 20px;
        color: var(--pm-texto) !important;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        border-color: var(--pm-roxo-claro);
        color: var(--pm-roxo) !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--pm-roxo) !important;
        color: white !important;
        border-color: var(--pm-roxo) !important;
    }

    /* ═══ Buttons — Laranja PM Arredondado ═══ */
    .stButton > button {
        background: var(--pm-laranja) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(238, 129, 51, 0.25) !important;
    }

    .stButton > button:hover {
        background: #D9711F !important;
        box-shadow: 0 6px 20px rgba(238, 129, 51, 0.35) !important;
        transform: translateY(-2px);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--pm-laranja) 0%, #D9711F 100%) !important;
    }

    /* ═══ Sliders — Roxo ═══ */
    .stSlider > div > div > div > div {
        background-color: var(--pm-roxo) !important;
    }

    /* ═══ Radio Buttons — Roxo ═══ */
    .stRadio > div {
        color: var(--pm-texto) !important;
    }

    /* ═══ DataFrames — Branco limpo ═══ */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px var(--pm-sombra);
    }

    /* ═══ Blockquote / Perguntas ═══ */
    blockquote {
        border-left: 4px solid var(--pm-roxo) !important;
        background: #F3E5F5 !important;
        padding: 1rem 1.2rem !important;
        border-radius: 0 10px 10px 0 !important;
        color: var(--pm-texto) !important;
    }

    /* ═══ Links ═══ */
    a {
        color: var(--pm-roxo) !important;
    }

    /* ═══ Selectbox / Number Input ═══ */
    .stSelectbox, .stNumberInput {
        font-family: 'Montserrat', sans-serif !important;
    }

    /* ═══ Scrollbar sutil ═══ */
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-thumb {
        background: var(--pm-roxo-claro);
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HELPER: KPI ROW para sub-tabs
# =============================================================================
def render_kpi_row(kpis):
    """Renderiza uma linha de KPIs estilizados.
    kpis: lista de dicts com 'label', 'value', 'color' (opcional)
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        cor = kpi.get('color', '#2D325E')
        with col:
            st.markdown(f"""
            <div style='text-align:center; background: white; border-radius: 10px; padding: 0.8rem 0.5rem; 
                        border-left: 4px solid {cor}; box-shadow: 0 2px 8px rgba(0,0,0,0.06);'>
                <div style='font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 0.2rem;'>{kpi['label']}</div>
                <div style='font-size: 1.4rem; font-weight: 800; color: {cor};'>{kpi['value']}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")


# =============================================================================
# CACHE DE DADOS
# =============================================================================
@st.cache_data
def carregar_dados():
    """Carrega e prepara todos os dados necessários."""
    df_csv = carregar_dataset_csv()
    df_xlsx = carregar_dataset_xlsx()
    df_long = criar_dataset_longitudinal(df_csv, df_xlsx)
    df_modelo, features = criar_dataset_modelo(df_xlsx)
    return df_csv, df_xlsx, df_long, df_modelo, features


@st.cache_resource
def carregar_modelo_treinado():
    """Carrega modelo de risco de defasagem do disco."""
    try:
        return ModeloRiscoDefasagem.carregar_modelo('models/risco_defasagem.joblib')
    except Exception:
        return None


# =============================================================================
# HEADER COM LOGO + TITULO
# =============================================================================
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image('assets/logo.png', width=120)
with col_title:
    st.markdown("""
    <div style='padding-top: 0.5rem;'>
        <h1 style='margin: 0; font-size: 2rem; color: #2D325E !important; font-weight: 800; letter-spacing: 1px;'>PASSOS MÁGICOS</h1>
        <p style='margin: 0.2rem 0 0; color: #EE8133; font-weight: 600; font-size: 1rem;'>Datathon Analytics — Análise Educacional & Gestão de Risco Acadêmico</p>
        <p style='margin: 0; color: #888; font-size: 0.8rem;'>FIAP PosTech · Data Analytics · Fase 5</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Carregar dados
with st.spinner("Carregando dados..."):
    df_csv, df_xlsx, df_long, df_modelo, features = carregar_dados()

# =============================================================================
# SIDEBAR LATERAL
# =============================================================================
with st.sidebar:
    st.image('assets/logo.png', use_container_width=True)
    st.markdown("""
    <div style='text-align: center; margin-top: -0.5rem; margin-bottom: 0.5rem;'>
        <span style='font-size: 0.8rem; font-weight: 600; letter-spacing: 1.5px; opacity: 0.8;'>DATATHON ANALYTICS</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown(f"""
    <div style='text-align: center; padding: 0.5rem 0;'>
        <div style='font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.5; margin-bottom: 0.3rem;'>Dados Unificados</div>
        <div style='font-size: 1.4rem; font-weight: 800; color: #F4B41A;'>{df_long.shape[0]:,} registros</div>
        <div style='font-size: 0.72rem; opacity: 0.6; margin-top: 0.2rem;'>{df_csv.shape[0]:,} CSV + {df_xlsx.shape[0]:,} XLSX</div>
        <div style='font-size: 0.68rem; opacity: 0.45; margin-top: 0.15rem;'>2020 · 2021 · 2022 · 2024</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    pagina = st.radio(
        "Menu",
        ["📋 Apresentação", "📊 Visão Geral", "🔍 Análise por Indicador",
         "🤖 Modelos Preditivos", "🚨 Risco de Evasão",
         "👤 Visão 360° do Aluno", "🧑‍🎓 Predição Individual"],
        label_visibility="collapsed",
        key="nav_radio",
    )

    st.markdown("---")

    st.markdown("""
    <div style='text-align: center; color: rgba(255,255,255,0.45); font-size: 0.7rem; line-height: 1.6;'>
        Desenvolvido para o<br>
        <strong style='color: rgba(255,255,255,0.65);'>Datathon FIAP PosTech</strong><br>
        Data Analytics — Fase 5
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🚪 Sair", key="logout_admin"):
        for k in ['logged_in', 'role', 'username', 'aluno_key']:
            st.session_state.pop(k, None)
        st.rerun()


# =============================================================================
# BIG NUMBERS (KPIs) — FIXOS NO TOPO
# =============================================================================
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

inde_medio = df_xlsx['INDE'].mean()
taxa_pv = (df_xlsx['PONTO_VIRADA'] == 'Sim').mean() * 100
defasados = (df_xlsx['DEFASAGEM'] < 0).mean() * 100
ida_medio = df_xlsx['IDA'].mean()

with kpi1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total de Alunos</div>
        <div class="kpi-value">{df_xlsx.shape[0]}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Score Educ. Médio</div>
        <div class="kpi-value">{inde_medio:.2f}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Ponto de Virada</div>
        <div class="kpi-value">{taxa_pv:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)
with kpi4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Em Defasagem</div>
        <div class="kpi-value" style="color: var(--pm-vermelho);">{defasados:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)
with kpi5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Média Acadêmica</div>
        <div class="kpi-value">{ida_medio:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# =============================================================================
# NAVEGAÇÃO POR PÁGINAS (SIDEBAR)
# =============================================================================

# =============================================================================
# PÁGINA: VISÃO GERAL
# =============================================================================
if pagina == "📊 Visão Geral":
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Distribuição por Pedra
        pedra_counts = df_xlsx['PEDRA_2022'].value_counts().reset_index()
        pedra_counts.columns = ['Pedra', 'Contagem']
        fig = px.pie(
            pedra_counts, values='Contagem', names='Pedra',
            color='Pedra', color_discrete_map=CORES_PEDRAS,
            title='🏆 Distribuição por Classificação (Pedra) - 2022',
            template='plotly_white', hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        # Distribuição de INDE
        fig = px.histogram(
            df_xlsx, x='INDE', nbins=30,
            color_discrete_sequence=['#2D325E'],
            title='📊 Como os alunos estão distribuídos por nível educacional (2022)',
            template='plotly_white'
        )
        # Linhas de corte das pedras
        for nome, limite in [('Quartzo', 5.506), ('Ágata', 6.868), ('Ametista', 8.230)]:
            fig.add_vline(x=limite, line_dash='dash',
                         line_color=CORES_PEDRAS.get(nome, 'white'),
                         annotation_text=f'{nome}: {limite}')
        st.plotly_chart(fig, use_container_width=True)
    
    col_c, col_d = st.columns(2)
    
    with col_c:
        # Boxplot dos indicadores
        indicadores_df = df_xlsx[['IAA', 'IEG', 'IPS', 'IDA', 'IPV', 'IAN']].melt(
            var_name='Indicador', value_name='Valor'
        )
        fig = px.box(
            indicadores_df, x='Indicador', y='Valor',
            color='Indicador',
            title='📦 Panorama dos Indicadores Educacionais',
            template='plotly_white'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_d:
        # Gênero
        genero_counts = df_xlsx['GENERO'].value_counts().reset_index()
        genero_counts.columns = ['Gênero', 'Contagem']
        fig = px.pie(
            genero_counts, values='Contagem', names='Gênero',
            color='Gênero',
            color_discrete_map={'Menina': '#FF69B4', 'Menino': '#4169E1'},
            title='👫 Distribuição por Gênero',
            template='plotly_white', hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# PÁGINA: ANÁLISE POR INDICADOR
# =============================================================================
elif pagina == "🔍 Análise por Indicador":
    sub_ian, sub_ida, sub_ieg, sub_iaa, sub_ips, sub_ipp, sub_ipv, sub_multi = st.tabs([
        "IAN", "IDA", "IEG", "IAA", "IPS", "IPP", "IPV", "Multi"
    ])

    with sub_ian:
        st.markdown("""
        <div class="section-header">
            <h2>1. Adequação do Nível (IAN)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** Qual é o perfil geral de defasagem dos alunos (IAN) e como ele evolui ao longo do ano?
        """)
        render_kpi_row([
            {'label': 'IAN Médio', 'value': f"{df_xlsx['IAN'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'Adequados (≥8)', 'value': f"{(df_xlsx['IAN'] >= 8).sum()}", 'color': '#4CAF50'},
            {'label': 'Defasados (<5)', 'value': f"{(df_xlsx['IAN'] < 5).sum()}", 'color': '#D84C51'},
            {'label': 'Taxa Adequação', 'value': f"{(df_xlsx['IAN'] >= 8).mean()*100:.1f}%", 'color': '#EE8133'},
        ])
    
        resultado = analise_ian(df_long)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_ian_evolucao'], use_container_width=True)
        with col2:
            st.plotly_chart(resultado['fig_ian_media'], use_container_width=True)
    
        # Stats
        stats = resultado['stats_ian']
        st.markdown("### 📊 Estatísticas do IAN por Ano")
        st.dataframe(
            stats.style.format({'mean': '{:.2f}', 'median': '{:.2f}', 'std': '{:.2f}'}),
            use_container_width=True
        )
    
        # Distribuição atual (2022)
        df_2022 = df_xlsx.copy()
        df_2022['RISCO_IAN'] = df_2022['IAN'].apply(classificar_risco_ian)
        risco_dist = df_2022['RISCO_IAN'].value_counts()
    
        st.markdown("### 📋 Distribuição de Defasagem Atual (2022)")
        col_a, col_b, col_c, col_d = st.columns(4)
        for i, (risco, count) in enumerate(risco_dist.items()):
            with [col_a, col_b, col_c, col_d][i % 4]:
                pct = count / len(df_2022) * 100
                st.metric(risco, f"{count} ({pct:.1f}%)")
    
        st.markdown("""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> A maioria dos alunos apresenta algum grau de defasagem. 
            O IAN médio indica que há uma necessidade significativa de intervenções pedagógicas 
            para ajudar os alunos a se adequarem ao nível esperado. Alunos com IAN ≥ 8 são considerados 
            adequados, enquanto aqueles abaixo de 5 requerem atenção urgente.</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_ida:
        st.markdown("""
        <div class="section-header">
            <h2>2. Desempenho Acadêmico (IDA)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** O desempenho acadêmico médio (IDA) está melhorando, estagnado ou caindo ao longo das fases e anos?
        """)
        render_kpi_row([
            {'label': 'IDA Médio', 'value': f"{df_xlsx['IDA'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'Acima da Média', 'value': f"{(df_xlsx['IDA'] > df_xlsx['IDA'].mean()).sum()}", 'color': '#4CAF50'},
            {'label': 'Abaixo de 5', 'value': f"{(df_xlsx['IDA'] < 5).sum()}", 'color': '#D84C51'},
            {'label': 'Desvio Padrão', 'value': f"{df_xlsx['IDA'].std():.2f}", 'color': '#EE8133'},
        ])
    
        resultado = analise_ida(df_long)
    
        st.plotly_chart(resultado['fig_ida_evolucao'], use_container_width=True)
    
        if 'fig_ida_pedra' in resultado:
            st.plotly_chart(resultado['fig_ida_pedra'], use_container_width=True)
    
        stats = resultado['stats_ida']
    
        # Tendência
        if len(stats) >= 2:
            diff = stats['mean'].iloc[-1] - stats['mean'].iloc[0]
            trend = "📈 MELHORANDO" if diff > 0.1 else ("📉 CAINDO" if diff < -0.1 else "➡️ ESTAGNADO")
            st.markdown(f"""
            <div class="insight-box">
                <p>💡 <strong>Tendência:</strong> O desempenho acadêmico médio está <strong>{trend}</strong>.
                Variação de {stats['mean'].iloc[0]:.2f} ({int(stats['ANO'].iloc[0])}) para {stats['mean'].iloc[-1]:.2f} ({int(stats['ANO'].iloc[-1])}) 
                (Δ = {diff:+.2f}).</p>
            </div>
            """, unsafe_allow_html=True)


    with sub_ieg:
        st.markdown("""
        <div class="section-header">
            <h2>3. Engajamento nas Atividades (IEG)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** O grau de engajamento dos alunos (IEG) tem relação direta com seus indicadores de desempenho (IDA) e do ponto de virada (IPV)?
        """)
        render_kpi_row([
            {'label': 'IEG Médio', 'value': f"{df_xlsx['IEG'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'Alto Engajamento (≥8)', 'value': f"{(df_xlsx['IEG'] >= 8).sum()}", 'color': '#4CAF50'},
            {'label': 'Baixo Engajamento (<5)', 'value': f"{(df_xlsx['IEG'] < 5).sum()}", 'color': '#D84C51'},
            {'label': 'Mediana', 'value': f"{df_xlsx['IEG'].median():.2f}", 'color': '#EE8133'},
        ])
    
        resultado = analise_engajamento(df_long)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_ieg_ida'], use_container_width=True)
        with col2:
            st.plotly_chart(resultado['fig_ieg_ipv'], use_container_width=True)
    
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Correlação IEG ↔ IDA", f"{resultado['corr_ieg_ida']:.3f}")
        with col_b:
            st.metric("Correlação IEG ↔ IPV", f"{resultado['corr_ieg_ipv']:.3f}")
    
        st.markdown(f"""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> A correlação entre engajamento (IEG) e desempenho acadêmico (IDA) 
            é de <strong>{resultado['corr_ieg_ida']:.3f}</strong>, e com o ponto de virada (IPV) é de 
            <strong>{resultado['corr_ieg_ipv']:.3f}</strong>. 
            {'Há uma relação positiva significativa entre engajamento e desempenho.' if resultado['corr_ieg_ida'] > 0.3 else 'A relação é moderada, indicando que outros fatores também influenciam o desempenho.'}</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_iaa:
        st.markdown("""
        <div class="section-header">
            <h2>4. Autoavaliação (IAA)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** As percepções dos alunos sobre si mesmos (IAA) são coerentes com seu desempenho real (IDA) e engajamento (IEG)?
        """)
        render_kpi_row([
            {'label': 'IAA Médio', 'value': f"{df_xlsx['IAA'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'IDA Médio', 'value': f"{df_xlsx['IDA'].mean():.2f}", 'color': '#4A4F7A'},
            {'label': 'Gap (IAA-IDA)', 'value': f"{(df_xlsx['IAA'] - df_xlsx['IDA']).mean():+.2f}", 'color': '#EE8133'},
            {'label': 'Correlação', 'value': f"{df_xlsx['IAA'].corr(df_xlsx['IDA']):.3f}", 'color': '#F4B41A'},
        ])
    
        resultado = analise_autoavaliacao(df_long)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_iaa_ida_diff'], use_container_width=True)
        with col2:
            st.plotly_chart(resultado['fig_iaa_ida_scatter'], use_container_width=True)
    
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Correlação IAA ↔ IDA", f"{resultado['corr_iaa_ida']:.3f}")
        with col_b:
            st.metric("Diferença Média (IAA - IDA)", f"{resultado['media_diferenca']:+.2f}")
    
        st.markdown(f"""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> A diferença média entre autoavaliação e desempenho real é de 
            <strong>{resultado['media_diferenca']:+.2f}</strong>. 
            {'Os alunos tendem a se superestimar em relação ao desempenho real.' if resultado['media_diferenca'] > 0.5 else 'As autoavaliações são relativamente coerentes com o desempenho real.' if abs(resultado['media_diferenca']) < 0.5 else 'Os alunos tendem a se subestimar em relação ao desempenho real.'}
            A correlação entre IAA e IDA é de <strong>{resultado['corr_iaa_ida']:.3f}</strong>.</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_ips:
        st.markdown("""
        <div class="section-header">
            <h2>5. Aspectos Psicossociais (IPS)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** Há padrões psicossociais (IPS) que antecedem quedas de desempenho acadêmico ou de engajamento?
        """)
        render_kpi_row([
            {'label': 'IPS Médio', 'value': f"{df_xlsx['IPS'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'IPS Alto (≥8)', 'value': f"{(df_xlsx['IPS'] >= 8).sum()}", 'color': '#4CAF50'},
            {'label': 'IPS Crítico (<4)', 'value': f"{(df_xlsx['IPS'] < 4).sum()}", 'color': '#D84C51'},
            {'label': 'Corr IPS↔IDA', 'value': f"{df_xlsx['IPS'].corr(df_xlsx['IDA']):.3f}", 'color': '#EE8133'},
        ])
    
        resultado = analise_psicossocial(df_long)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_ips_ida'], use_container_width=True)
        with col2:
            st.plotly_chart(resultado['fig_ips_ieg'], use_container_width=True)
    
        st.plotly_chart(resultado['fig_ips_grupos'], use_container_width=True)
    
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Correlação IPS ↔ IDA", f"{resultado['corr_ips_ida']:.3f}")
        with col_b:
            st.metric("Correlação IPS ↔ IEG", f"{resultado['corr_ips_ieg']:.3f}")
    
        st.markdown(f"""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> Alunos com IPS muito baixo (≤ 4) apresentam desempenho acadêmico 
            significativamente inferior. A correlação IPS ↔ IDA de <strong>{resultado['corr_ips_ida']:.3f}</strong> 
            {'indica que aspectos psicossociais têm impacto relevante no desempenho' if resultado['corr_ips_ida'] > 0.2 else 'sugere uma relação moderada entre aspectos psicossociais e desempenho'}.
            Recomenda-se atenção especial ao suporte psicológico dos alunos com IPS baixo como medida preventiva.</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_ipp:
        st.markdown("""
        <div class="section-header">
            <h2>6. Aspectos Psicopedagógicos (IPP)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** As avaliações psicopedagógicas (IPP) confirmam ou contradizem a defasagem identificada pelo IAN?
        """)
        render_kpi_row([
            {'label': 'IPP Médio (Long.)', 'value': f"{df_long[df_long['IPP'].notna()]['IPP'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'IPP Mediana', 'value': f"{df_long[df_long['IPP'].notna()]['IPP'].median():.2f}", 'color': '#4A4F7A'},
            {'label': 'Corr IPP↔IAN', 'value': f"{df_long[['IPP','IAN']].dropna().corr().iloc[0,1]:.3f}", 'color': '#EE8133'},
            {'label': 'Registros', 'value': f"{df_long['IPP'].notna().sum()}", 'color': '#F4B41A'},
        ])
    
        resultado = analise_psicopedagogico(df_long)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_ipp_ian'], use_container_width=True)
        with col2:
            st.plotly_chart(resultado['fig_ipp_por_risco'], use_container_width=True)
    
        st.metric("Correlação IPP ↔ IAN", f"{resultado['corr_ipp_ian']:.3f}")
    
        confirma = "CONFIRMAM" if resultado['corr_ipp_ian'] > 0.2 else "são INDEPENDENTES de"
        st.markdown(f"""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> As avaliações psicopedagógicas (IPP) <strong>{confirma}</strong> 
            a defasagem identificada pelo IAN (correlação: {resultado['corr_ipp_ian']:.3f}). 
            Isto sugere que {'o IPP é um indicador útil e complementar ao IAN' if resultado['corr_ipp_ian'] > 0.2 else 'o IPP captura dimensões diferentes da defasagem, sendo complementar ao IAN'}.</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_ipv:
        st.markdown("""
        <div class="section-header">
            <h2>7. Ponto de Virada (IPV)</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** Quais comportamentos - acadêmicos, emocionais ou de engajamento - mais influenciam o IPV ao longo do tempo?
        """)
        render_kpi_row([
            {'label': 'IPV Médio', 'value': f"{df_xlsx['IPV'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'Atingiram PV', 'value': f"{(df_xlsx['PONTO_VIRADA'] == 'Sim').sum()}", 'color': '#4CAF50'},
            {'label': 'Taxa PV', 'value': f"{(df_xlsx['PONTO_VIRADA'] == 'Sim').mean()*100:.1f}%", 'color': '#EE8133'},
            {'label': 'IPV Mediana', 'value': f"{df_xlsx['IPV'].median():.2f}", 'color': '#F4B41A'},
        ])
    
        resultado = analise_ponto_virada(df_long)
    
        st.plotly_chart(resultado['fig_ipv_correlacoes'], use_container_width=True)
    
        if 'fig_ipv_comparacao' in resultado:
            st.plotly_chart(resultado['fig_ipv_comparacao'], use_container_width=True)
    
        # Top influenciadores
        corrs = resultado['correlacoes_ipv']
        top = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    
        st.markdown("### 🏆 Ranking de Influência no IPV")
        for i, (ind, corr) in enumerate(top):
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📊"
            st.markdown(f"{emoji} **{ind}**: correlação {corr:.3f}")
    
        st.markdown(f"""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> O indicador que mais influencia o Ponto de Virada é 
            <strong>{top[0][0]}</strong> (r = {top[0][1]:.3f}), seguido por 
            <strong>{top[1][0]}</strong> (r = {top[1][1]:.3f}). 
            Intervenções focadas nestes aspectos podem ter maior impacto na transformação dos alunos.</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_multi:
        st.markdown("""
        <div class="section-header">
            <h2>8. Multidimensionalidade dos Indicadores</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** Quais combinações de indicadores (IDA + IEG + IPS + IPP) elevam mais a nota global do aluno (INDE)?
        """)
        render_kpi_row([
            {'label': 'INDE Médio', 'value': f"{df_xlsx['INDE'].mean():.2f}", 'color': '#2D325E'},
            {'label': 'Topázio', 'value': f"{(df_xlsx['PEDRA_2022'] == 'Topázio').sum()}", 'color': '#F4B41A'},
            {'label': 'Ametista', 'value': f"{(df_xlsx['PEDRA_2022'] == 'Ametista').sum()}", 'color': '#9C27B0'},
            {'label': 'Quartzo', 'value': f"{(df_xlsx['PEDRA_2022'] == 'Quartzo').sum()}", 'color': '#D84C51'},
        ])
    
        resultado = analise_multidimensional(df_long)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_correlacao_matrix'], use_container_width=True)
        with col2:
            st.plotly_chart(resultado['fig_importancia_inde'], use_container_width=True)
    
        if 'fig_radar_pedra' in resultado:
            st.plotly_chart(resultado['fig_radar_pedra'], use_container_width=True)
    
        # Top contribuidores
        corr_inde = resultado['correlacao_inde']
        top = sorted(corr_inde.items(), key=lambda x: abs(x[1]), reverse=True)
    
        st.markdown(f"""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> Os indicadores que mais contribuem para o INDE são: 
            <strong>{top[0][0]}</strong> (r = {top[0][1]:.3f}), 
            <strong>{top[1][0]}</strong> (r = {top[1][1]:.3f}) e 
            <strong>{top[2][0]}</strong> (r = {top[2][1]:.3f}). 
            Programas que fortaleçam simultaneamente estas dimensões terão maior impacto no desenvolvimento global dos alunos.</p>
        </div>
        """, unsafe_allow_html=True)





# =============================================================================
# PÁGINA: MODELOS PREDITIVOS (3 abas)
# =============================================================================
elif pagina == "🤖 Modelos Preditivos":
    st.markdown("""
    <div class="section-header">
        <h2>Sistemas de Análise Preditiva</h2>
    </div>
    """, unsafe_allow_html=True)

    aba_def, aba_pedra, aba_pv, aba_churn = st.tabs([
        "⚠️ Risco de Defasagem",
        "💎 Classificação de Jornada",
        "✨ Momento de Virada",
        "🔔 Risco de Evasão",
    ])

    # ── ABA 1: RISCO DE DEFASAGEM ─────────────────────────────────────────────
    modelo = carregar_modelo_treinado()

    def _set_nav(page):
        st.session_state.nav_radio = page

    with aba_def:
        st.markdown("""
        <div style="background:#FFF8F0; border-left:5px solid #EE8133; border-radius:10px;
                    padding:28px 32px; margin-bottom:24px;">
            <div style="font-size:28px; margin-bottom:8px;">⚠️</div>
            <h3 style="color:#EE8133; margin:0 0 12px;">Identificação de Risco de Defasagem</h3>
            <p style="color:#444; font-size:15px; line-height:1.7; margin:0 0 16px;">
                Analisa o perfil atual do aluno e estima a chance de ele apresentar defasagem
                no próximo ciclo. Permite à equipe agir antes que o problema se instale,
                priorizando os casos que mais precisam de atenção.
            </p>
            <div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">
                <div style="background:#EE813320; border-radius:8px; padding:10px 20px; text-align:center;">
                    <div style="font-size:24px; font-weight:700; color:#EE8133;">70%</div>
                    <div style="font-size:12px; color:#666;">Taxa de Acerto</div>
                </div>
                <div style="background:#27AE6020; border-radius:8px; padding:10px 20px; text-align:center;">
                    <div style="font-size:24px; font-weight:700; color:#27AE60;">96%</div>
                    <div style="font-size:12px; color:#666;">Taxa de Identificação</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("→ Usar este sistema (Predição Individual)", key="btn_usar_def",
                     use_container_width=True, type="primary", on_click=_set_nav, args=("🧑‍🎓 Predição Individual",)):
            pass

        if modelo is not None and modelo.resultados:
            with st.expander("➕ Detalhes para equipe técnica"):
                best = modelo.resultados.get(modelo.melhor_nome, {})
                st.markdown(f"**Acurácia (validação):** {best.get('accuracy', 0):.1%}")
                st.markdown(f"**Precisão:** {best.get('precision', 0):.1%}")
                st.markdown(f"**Recall:** {best.get('recall', 0):.1%}")
                st.markdown(f"**F1-Score:** {best.get('f1_score', 0):.1%}")
                st.markdown(f"**AUC-ROC:** {best.get('roc_auc', 0):.1%}")
                st.markdown(f"**Threshold calibrado:** 0.36 (prioriza não perder alunos em risco)")
                if modelo.feature_importance is not None:
                    _LABEL_DEF = {
                        'IAA': 'Autoconfiança', 'IEG': 'Engajamento', 'IPS': 'Bem-estar',
                        'IDA': 'Desempenho', 'IPV': 'Fator Virada', 'FASE': 'Fase',
                        'ANOS_PM': 'Tempo no programa', 'MEDIA_NOTAS': 'Média Notas',
                        'MEDIA_INDICADORES': 'Média Indicadores', 'NOTA_MAT': 'Matemática',
                        'NOTA_PORT': 'Português', 'GENERO_FEMININO': 'Gênero',
                        'INSTITUICAO_COD': 'Instituição', 'EVOLUCAO_PEDRA': 'Evolução de Nível',
                    }
                    fi_def = modelo.feature_importance.copy()
                    fi_def['feature_label'] = fi_def['feature'].map(lambda x: _LABEL_DEF.get(x, x))
                    fig_fi = px.bar(fi_def.head(10), x='importance', y='feature_label', orientation='h',
                                    color='importance', color_continuous_scale='Oranges',
                                    title='Fatores mais relevantes para a análise',
                                    template='plotly_white')
                    fig_fi.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_fi, use_container_width=True)
        else:
            st.info("ℹ️ Sistema em processo de carregamento. Execute `python train_model.py` se necessário.")
    
    # ── ABA 2: CLASSIFICAÇÃO DE JORNADA (PEDRA) ──────────────────────────────
    _PEDRA_CORES_M = {
        'Quartzo': '#78909C', 'Agata': '#42A5F5', 'Ágata': '#42A5F5',
        'Ametista': '#AB47BC', 'Topazio': '#FFD740', 'Topázio': '#FFD740',
    }

    with aba_pedra:
        st.markdown("""
        <div style="background:#F0F4FF; border-left:5px solid #42A5F5; border-radius:10px;
                    padding:28px 32px; margin-bottom:24px;">
            <div style="font-size:28px; margin-bottom:8px;">💎</div>
            <h3 style="color:#1565C0; margin:0 0 12px;">Classificação da Jornada</h3>
            <p style="color:#444; font-size:15px; line-height:1.7; margin:0 0 16px;">
                Com base nos indicadores atuais, estima em qual nível da jornada
                (Quartzo → Ágata → Ametista → Topázio) o aluno estará no próximo período.
                Apoia o planejamento pedagógico de cada turma e auxilia na formação de grupos
                de acompanhamento.
            </p>
            <div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">
                <div style="background:#42A5F520; border-radius:8px; padding:10px 20px; text-align:center;">
                    <div style="font-size:24px; font-weight:700; color:#1565C0;">79%</div>
                    <div style="font-size:12px; color:#666;">Taxa de Acerto</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("→ Usar este sistema (Predição Individual)", key="btn_usar_pedra",
                     use_container_width=True, type="primary", on_click=_set_nav, args=("🧑‍🎓 Predição Individual",)):
            pass

        st.markdown("---")
        st.markdown("#### Como os alunos estão distribuídos hoje")

        df_pv = df_xlsx[['PEDRA_2022', 'FASE', 'INDE', 'IAA', 'IEG', 'IPS', 'IDA']].dropna(subset=['PEDRA_2022'])
        pedra_ct = df_pv['PEDRA_2022'].value_counts()
        total_p = len(df_pv)

        render_kpi_row([
            {'label': '⬜ Quartzo',   'value': f"{pedra_ct.get('Quartzo', 0)} ({pedra_ct.get('Quartzo', 0)/total_p*100:.0f}%)", 'color': '#78909C'},
            {'label': '🟣 Ágata',    'value': f"{pedra_ct.get('Agata', pedra_ct.get('Ágata', 0))} ({pedra_ct.get('Agata', pedra_ct.get('Ágata', 0))/total_p*100:.0f}%)", 'color': '#42A5F5'},
            {'label': '💜 Ametista', 'value': f"{pedra_ct.get('Ametista', 0)} ({pedra_ct.get('Ametista', 0)/total_p*100:.0f}%)", 'color': '#AB47BC'},
            {'label': '💎 Topázio',  'value': f"{pedra_ct.get('Topazio', pedra_ct.get('Topázio', 0))} ({pedra_ct.get('Topazio', pedra_ct.get('Topázio', 0))/total_p*100:.0f}%)", 'color': '#FFD740'},
        ])

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig = px.pie(df_pv, names='PEDRA_2022', color='PEDRA_2022',
                         color_discrete_map=_PEDRA_CORES_M, hole=0.4,
                         title='Distribuição atual por nível',
                         template='plotly_white',
                         category_orders={'PEDRA_2022': ['Quartzo', 'Agata', 'Ágata', 'Ametista', 'Topazio', 'Topázio']})
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        with col_p2:
            medias_p = df_pv.groupby('PEDRA_2022')[['INDE', 'IAA', 'IEG', 'IPS', 'IDA']].mean().reset_index()
            medias_melt = medias_p.melt(id_vars='PEDRA_2022', var_name='Indicador', value_name='Média')
            fig = px.bar(medias_melt, x='PEDRA_2022', y='Média', color='Indicador',
                         barmode='group', title='Perfil médio por nível educacional',
                         template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

        modelo_pedra_m = carregar_modelo_pedra()
        if modelo_pedra_m is not None:
            res_p = modelo_pedra_m.resultados
            with st.expander("➕ Detalhes para equipe técnica"):
                st.write(f"**Taxa de Acerto (validação):** {res_p.get('accuracy', 0):.1%}")
                st.write(f"**Poder de Previsão (AUC):** {res_p.get('roc_auc', 0):.1%}")
                st.write(f"**Consistência ponderada (F1):** {res_p.get('f1_weighted', 0):.1%}")
                st.write(f"**Taxa de Acerto (desenvolvimento):** {res_p.get('acc_treino', 0):.1%}")
                if modelo_pedra_m.feature_importance is not None:
                    fi_m = modelo_pedra_m.feature_importance.copy()
                    _LABEL_MAP = {'IAA': 'Autoconfiança', 'IEG': 'Engajamento', 'IPS': 'Bem-estar',
                                   'IDA': 'Desempenho', 'IPV': 'Fator Virada', 'FASE': 'Fase',
                                   'ANOS_PM': 'Tempo no programa', 'MEDIA_NOTAS': 'Média Notas',
                                   'MEDIA_INDICADORES': 'Média Indicadores', 'NOTA_MAT': 'Matemática',
                                   'NOTA_PORT': 'Português', 'GENERO_FEMININO': 'Gênero', 'INSTITUICAO_COD': 'Instituição'}
                    fi_m['feature_label'] = fi_m['feature'].map(lambda x: _LABEL_MAP.get(x, x))
                    fig = px.bar(fi_m.head(10), x='importance', y='feature_label', orientation='h',
                                 color='importance', color_continuous_scale='Blues',
                                 title='Fatores que mais influenciam a classificação de nível',
                                 template='plotly_white')
                    fig.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)

    # ── ABA 3: MOMENTO DE VIRADA (PONTO DE VIRADA) ────────────────────────────
    with aba_pv:
        st.markdown("""
        <div style="background:#F0FFF4; border-left:5px solid #27AE60; border-radius:10px;
                    padding:28px 32px; margin-bottom:24px;">
            <div style="font-size:28px; margin-bottom:8px;">✨</div>
            <h3 style="color:#1E8449; margin:0 0 12px;">Proximidade do Momento de Virada</h3>
            <p style="color:#444; font-size:15px; line-height:1.7; margin:0 0 16px;">
                Identifica quais alunos estão mais próximos de atingir o ponto de transformação
                do programa — o momento em que desenvolvem protagonismo e visão de futuro.
                Orienta onde concentrar mentoria e esforços pedagógicos para maximizar o impacto
                do acompanhamento individualizado.
            </p>
            <div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">
                <div style="background:#27AE6020; border-radius:8px; padding:10px 20px; text-align:center;">
                    <div style="font-size:24px; font-weight:700; color:#1E8449;">90%</div>
                    <div style="font-size:12px; color:#666;">Taxa de Acerto</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("→ Usar este sistema (Predição Individual)", key="btn_usar_pv",
                     use_container_width=True, type="primary", on_click=_set_nav, args=("🧑‍🎓 Predição Individual",)):
            pass

        modelo_pv_m = carregar_modelo_pv()
        if modelo_pv_m is not None:
            r_pv = modelo_pv_m.resultados
            n_atingiu = (df_xlsx['PONTO_VIRADA'] == 'Sim').sum()
            taxa_pv_pct = n_atingiu / len(df_xlsx) * 100

            st.markdown("---")
            st.markdown("#### Panorama atual do programa")
            render_kpi_row([
                {'label': 'Alunos que Atingiram o Momento de Virada',
                 'value': f"{n_atingiu} ({taxa_pv_pct:.1f}%)", 'color': '#4CAF50'},
            ])

            with st.expander("➕ Detalhes para equipe técnica"):
                st.write(f"**Taxa de Acerto (validação):** {r_pv.get('acc_teste', 0):.1%}")
                st.write(f"**Poder de Previsão (AUC):** {r_pv.get('roc_auc', 0):.1%}")
                st.write(f"**Taxa de Identificação (Recall):** {r_pv.get('recall', 0):.1%}")
                st.write(f"**Precisão:** {r_pv.get('precision', 0):.1%}")
                st.write(f"**Nota:** classe positiva representa apenas {taxa_pv_pct:.1f}% dos alunos — "
                         f"o sistema prioriza identificar corretamente quem está próximo do momento.")
                if modelo_pv_m.feature_importance is not None:
                    fi_pv = modelo_pv_m.feature_importance.copy()
                    _LBL = {'IAA': 'Autoconfiança', 'IEG': 'Engajamento', 'IPS': 'Bem-estar',
                            'IDA': 'Desempenho', 'IAN': 'Adequação de Nível', 'IPP': 'Avaliação Pedagógica',
                            'FASE': 'Fase', 'ANOS_PM': 'Tempo no programa', 'PEDRA_NUM': 'Nível Atual',
                            'MEDIA_NOTAS': 'Média Notas', 'MEDIA_INDICADORES': 'Média Indicadores',
                            'NOTA_MAT': 'Matemática', 'NOTA_PORT': 'Português', 'NOTA_ING': 'Inglês',
                            'GENERO_FEMININO': 'Gênero', 'INSTITUICAO_COD': 'Instituição'}
                    fi_pv['feature_label'] = fi_pv['feature'].map(lambda x: _LBL.get(x, x))
                    fig = px.bar(fi_pv.head(10), x='importance', y='feature_label', orientation='h',
                                 color='importance', color_continuous_scale='Greens',
                                 title='Fatores que mais indicam proximidade ao Momento de Virada',
                                 template='plotly_white')
                    fig.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ℹ️ Sistema em processo de carregamento. Execute `python train_model.py` se necessário.")

    # ── ABA 4: RISCO DE PERMANÊNCIA (CHURN) ───────────────────────────────────
    with aba_churn:
        modelo_churn_m = carregar_modelo_churn()
        _acc_churn_str = f"{modelo_churn_m.resultados.get('acc_teste', 0):.0%}" if modelo_churn_m else "—"

        st.markdown(f"""
        <div style="background:#FFF0F3; border-left:5px solid #D84C51; border-radius:10px;
                    padding:28px 32px; margin-bottom:24px;">
            <div style="font-size:28px; margin-bottom:8px;">🔔</div>
            <h3 style="color:#C0392B; margin:0 0 12px;">Análise de Risco de Evasão</h3>
            <p style="color:#444; font-size:15px; line-height:1.7; margin:0 0 16px;">
                Aprendeu com o histórico de alunos que realmente deixaram a Passos
                Mágicos em anos anteriores. Compara o perfil atual de cada aluno
                com esse histórico para estimar a probabilidade de evasão.
            </p>
            <div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">
                <div style="background:#D84C5120; border-radius:8px; padding:10px 20px; text-align:center;">
                    <div style="font-size:24px; font-weight:700; color:#C0392B;">{_acc_churn_str}</div>
                    <div style="font-size:12px; color:#666;">Taxa de Acerto</div>
                </div>
            </div>
            <p style="margin:16px 0 0; font-size:13px; color:#888;">
                ⚠️ Baseado em 499 casos históricos de evasão (2020-2022). A incorporação de
                dados contextuais (família, deslocamento, renda) pode ampliar ainda mais
                a precisão da análise.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("→ Ver análise completa (Risco de Evasão)", key="btn_usar_churn",
                     use_container_width=True, type="primary", on_click=_set_nav, args=("🚨 Risco de Evasão",)):
            pass

        if modelo_churn_m is not None:
            with st.expander("➕ Detalhes para equipe técnica"):
                rc = modelo_churn_m.resultados
                st.write(f"**Acurácia (validação):** {rc.get('acc_teste', 0):.1%}")
                st.write(f"**Poder de Previsão (AUC):** {rc.get('roc_auc', 0):.1%}")
                st.write(f"**Taxa de Identificação (Recall):** {rc.get('recall', 0):.1%}")
                st.write(f"**Precisão:** {rc.get('precision', 0):.1%}")
                st.write(f"**F1-Score:** {rc.get('f1_score', 0):.1%}")
                st.write("**Target:** evasão real — aluno presente em ano N e ausente em N+1 "
                         "(transições 2020→2021 e 2021→2022 do CSV longitudinal). "
                         f"499 casos históricos de evasão em 1.411 observações.")
                st.write("**Features:** IAA, IEG, IPS, IDA, IPV, IAN, FASE, ANOS_PM, "
                         "PEDRA_NUM, MEDIA_INDICADORES — indicadores do ano anterior à transição.")
                st.write("**Sem leakage:** target derivado de presença/ausência real, "
                         "não de regras construídas.")
                if modelo_churn_m.feature_importance is not None:
                    _LBL_C = {
                        'IAA': 'Autoconfiança', 'IEG': 'Engajamento',
                        'IPS': 'Aspecto Psicossocial', 'IDA': 'Desempenho Acadêmico',
                        'IPV': 'Fator Virada', 'IAN': 'Adequação de Nível',
                        'FASE': 'Fase', 'ANOS_PM': 'Tempo no programa',
                        'PEDRA_NUM': 'Nível Atual',
                        'MEDIA_INDICADORES': 'Média dos Indicadores',
                    }
                    fi_c = modelo_churn_m.feature_importance.copy()
                    fi_c['label'] = fi_c['feature'].map(lambda x: _LBL_C.get(x, x))
                    fig_fc = px.bar(fi_c.head(10), x='importance', y='label', orientation='h',
                                    color='importance', color_continuous_scale='Reds',
                                    title='Fatores que mais influenciam o risco de evasão',
                                    template='plotly_white')
                    fig_fc.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_fc, use_container_width=True)
        else:
            st.info("ℹ️ Modelo não encontrado. Execute `python train_model.py` para gerar churn.joblib.")


# =============================================================================
# PÁGINA: APRESENTAÇÃO (Resultados & Insights)
# =============================================================================
elif pagina == "📋 Apresentação":
    sub_storytelling, sub_efetividade, sub_insights = st.tabs([
        "Storytelling", "Efetividade do Programa", "Insights Adicionais"
    ])

    with sub_storytelling:
        st.markdown("""
        <div class="section-header">
            <h2>Storytelling</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <iframe src="" width="100%" height="700" style="border:none;" allowfullscreen>
            <p>Volte mais tarde.</p>
        </iframe>
        <p style="text-align: center; font-size: 0.9em; color: gray; margin-top: 10px;">
            Caso o conteúdo do iframe não carregue: <strong>Volte mais tarde.</strong>
        </p>
        """, unsafe_allow_html=True)

    with sub_efetividade:
        st.markdown("""
        <div class="section-header">
            <h2>10. Efetividade do Programa</h2>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("""
        > **Pergunta:** Os indicadores mostram melhora consistente ao longo do ciclo nas diferentes fases (Quartzo, Ágata, Ametista e Topázio)?
        """)
    
        resultado = analise_efetividade(df_long, df_xlsx)
    
        if 'fig_inde_pedra_evolucao' in resultado:
            st.plotly_chart(resultado['fig_inde_pedra_evolucao'], use_container_width=True)
    
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(resultado['fig_pedra_distribuicao'], use_container_width=True)
        with col2:
            if 'fig_taxa_pv' in resultado:
                st.plotly_chart(resultado['fig_taxa_pv'], use_container_width=True)
    
        st.markdown("""
        <div class="insight-box">
            <p>💡 <strong>Insight:</strong> A análise da distribuição das pedras ao longo dos anos permite 
            avaliar se o programa está conseguindo mover alunos para classificações superiores. 
            Um aumento na proporção de alunos em Ametista e Topázio indica efetividade do programa. 
            A taxa de Ponto de Virada é um indicador importante da transformação promovida pela Passos Mágicos.</p>
        </div>
        """, unsafe_allow_html=True)


    with sub_insights:
        st.markdown("""
        <div class="section-header">
            <h2>11. Insights e Criatividade</h2>
        </div>
        """, unsafe_allow_html=True)
    
        resultado = analise_insights(df_xlsx)
    
        if 'fig_genero' in resultado:
            st.plotly_chart(resultado['fig_genero'], use_container_width=True)
    
        col1, col2 = st.columns(2)
        with col1:
            if 'fig_anos_pm' in resultado:
                st.plotly_chart(resultado['fig_anos_pm'], use_container_width=True)
        with col2:
            if 'fig_idade' in resultado:
                st.plotly_chart(resultado['fig_idade'], use_container_width=True)
    
        if 'fig_fase' in resultado:
            st.plotly_chart(resultado['fig_fase'], use_container_width=True)
    
        if 'fig_bolsa' in resultado:
            st.plotly_chart(resultado['fig_bolsa'], use_container_width=True)
    
        st.markdown("""
        <div class="insight-box">
            <p>💡 <strong>Insights Adicionais:</strong></p>
            <ul>
                <li><strong>Gênero:</strong> Análise comparativa entre meninos e meninas mostra diferenças nos indicadores que merecem atenção</li>
                <li><strong>Tempo na PM:</strong> Alunos com mais tempo na Passos Mágicos tendem a apresentar melhores indicadores</li>
                <li><strong>Faixa etária:</strong> A distribuição de idades revela a diversidade de perfis atendidos</li>
                <li><strong>Fase:</strong> O progresso dos indicadores por fase mostra o impacto do programa em cada nível</li>
                <li><strong>Bolsa:</strong> Alunos indicados para bolsa apresentam desempenho diferenciado</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
        # Sugestões para a Passos Mágicos
        st.markdown("### 🎯 Sugestões para a Passos Mágicos")
        st.markdown("""
        Com base na análise completa dos dados, as seguintes sugestões são apresentadas:
    
        1. **Sistema de Alerta Preventivo**: Utilizar o modelo preditivo para identificar alunos em risco de defasagem **antes** que a queda ocorra
        2. **Programa de Mentoria**: Alunos Topázio podem servir como mentores para alunos Quartzo
        3. **Intervenção Psicossocial**: Fortalecer o suporte psicológico para alunos com IPS < 5
        4. **Gamificação do Engajamento**: Estimular o IEG com atividades mais interativas e recompensas
        5. **Calibração da Autoavaliação**: Trabalhar a percepção dos alunos para ser mais alinhada com o desempenho real
        6. **Personalização por Fase**: Adaptar as intervenções de acordo com a fase do aluno
        7. **Monitoramento Contínuo**: Dashboard como este para acompanhamento em tempo real dos indicadores
        """)

# =============================================================================
# PÁGINA: MONITORAMENTO DE PERMANÊNCIA
# =============================================================================
elif pagina == "🚨 Risco de Evasão":
    st.markdown("""
    <div class="section-header">
        <h2>Sistema de Monitoramento de Permanência</h2>
    </div>
    """, unsafe_allow_html=True)

    # ── Construir sinais (fora das colunas — usado por ambas) ─────────────────
    df_mon = df_xlsx.copy()
    _ORD_MON = {'Quartzo': 1, 'Agata': 2, 'Ágata': 2, 'Ametista': 3, 'Topazio': 4, 'Topázio': 4}
    df_mon['PEDRA_2022_N'] = df_mon['PEDRA_2022'].map(_ORD_MON)
    df_mon['PEDRA_2020_N'] = df_mon['PEDRA_2020'].map(_ORD_MON) if 'PEDRA_2020' in df_mon.columns else np.nan
    df_mon['EVOLUCAO_PEDRA'] = np.where(
        df_mon['PEDRA_2020_N'].notna() & df_mon['PEDRA_2022_N'].notna(),
        df_mon['PEDRA_2022_N'] - df_mon['PEDRA_2020_N'], 0.0)

    df_mon['S1_IEG_BAIXO']   = (df_mon['IEG'] < 5.5).astype(int)
    df_mon['S2_IPS_CRITICO'] = (df_mon['IPS'] < 5.0).astype(int)
    df_mon['S3_QUEDA_PEDRA'] = (df_mon['EVOLUCAO_PEDRA'] < 0).astype(int)
    df_mon['S4_IDA_BAIXO']   = (df_mon['IDA'] < 5.5).astype(int)
    df_mon['S5_ESTAGNACAO']  = ((df_mon['ANOS_PM'] > 4) & (df_mon['EVOLUCAO_PEDRA'] <= 0)).astype(int)
    df_mon['N_SINAIS'] = df_mon[['S1_IEG_BAIXO','S2_IPS_CRITICO','S3_QUEDA_PEDRA',
                                   'S4_IDA_BAIXO','S5_ESTAGNACAO']].sum(axis=1)
    df_mon['EM_ALERTA'] = (df_mon['N_SINAIS'] >= 2).astype(int)
    df_mon['NIVEL_ALERTA'] = df_mon['N_SINAIS'].apply(
        lambda n: '🔴 Crítico' if n >= 3 else (
                  '🟠 Atenção' if n >= 2 else (
                  '🟡 Observação' if n == 1 else '🟢 Nenhum')))

    n_alerta_mon  = int(df_mon['EM_ALERTA'].sum())
    n_critico_mon = int((df_mon['N_SINAIS'] >= 3).sum())
    total_mon     = len(df_mon)

    # ── Layout 2 colunas ─────────────────────────────────────────────────────
    col_regras, col_ia = st.columns([3, 2])

    # ─────────────────────────────────────────────────────────────────────────
    # COLUNA 1 — SISTEMA DE ALERTAS (5 sinais determinísticos)
    # ─────────────────────────────────────────────────────────────────────────
    with col_regras:
        st.markdown("""
        > **Sistema de Alertas:** 5 sinais de risco validados pedagogicamente
        > permitem identificar alunos que precisam de acompanhamento adicional.
        """)

        render_kpi_row([
            {'label': 'Total de Alunos',          'value': f"{total_mon}", 'color': '#2D325E'},
            {'label': '🟡 Em Observação (1 sinal)',
             'value': f"{int((df_mon['N_SINAIS']==1).sum())} ({(df_mon['N_SINAIS']==1).sum()/total_mon*100:.0f}%)",
             'color': '#F4B41A'},
            {'label': '🟠 Em Atenção (≥2 sinais)',
             'value': f"{n_alerta_mon} ({n_alerta_mon/total_mon*100:.0f}%)", 'color': '#EE8133'},
            {'label': '🔴 Crítico (≥3 sinais)',
             'value': f"{n_critico_mon} ({n_critico_mon/total_mon*100:.0f}%)", 'color': '#D84C51'},
        ])

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            nv_dist = df_mon['NIVEL_ALERTA'].value_counts().reset_index()
            nv_dist.columns = ['Nível', 'Alunos']
            cor_map = {'🔴 Crítico': '#D84C51', '🟠 Atenção': '#EE8133',
                       '🟡 Observação': '#F4B41A', '🟢 Nenhum': '#4CAF50'}
            fig_nv = px.bar(nv_dist, x='Nível', y='Alunos', color='Nível',
                            color_discrete_map=cor_map,
                            title='Distribuição por nível de atenção',
                            template='plotly_white', text_auto=True)
            fig_nv.update_layout(showlegend=False)
            st.plotly_chart(fig_nv, use_container_width=True)

        with col_m2:
            sinais_df_m = pd.DataFrame({
                'Sinal': ['S1 — Engajamento crítico (IEG<5.5)',
                          'S2 — Psicossocial crítico (IPS<5.0)',
                          'S3 — Regrediu de nível',
                          'S4 — Desempenho baixo (IDA<5.5)',
                          'S5 — Estagnação >4 anos'],
                'Alunos': [df_mon['S1_IEG_BAIXO'].sum(), df_mon['S2_IPS_CRITICO'].sum(),
                           df_mon['S3_QUEDA_PEDRA'].sum(), df_mon['S4_IDA_BAIXO'].sum(),
                           df_mon['S5_ESTAGNACAO'].sum()]
            }).sort_values('Alunos')
            fig_sin = px.bar(sinais_df_m, x='Alunos', y='Sinal', orientation='h',
                             title='Volume de alunos por tipo de sinal',
                             template='plotly_white', text_auto=True,
                             color_discrete_sequence=['#EE8133'])
            st.plotly_chart(fig_sin, use_container_width=True)

        dist_sinais_m = df_mon['N_SINAIS'].value_counts().sort_index().reset_index()
        dist_sinais_m.columns = ['Nº de Sinais', 'Alunos']
        fig_dist = px.bar(dist_sinais_m, x='Nº de Sinais', y='Alunos',
                          title='Quantos sinais cada aluno acumula',
                          template='plotly_white', text_auto=True,
                          color_discrete_sequence=['#2D325E'])
        st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("### 🔍 Consulta por Aluno")
        alunos_ev_lista = [""] + list(df_mon.sort_values('N_SINAIS', ascending=False)['NOME'])
        aluno_ev_sel = st.selectbox("Selecionar aluno para ver detalhes:", alunos_ev_lista, key="mon_sel_aluno")
        if aluno_ev_sel:
            row_mon = df_mon[df_mon['NOME'] == aluno_ev_sel].iloc[0]
            n_s_mon = int(row_mon['N_SINAIS'])
            nv_mon  = row_mon['NIVEL_ALERTA']
            cor_mon = {'🔴 Crítico': '#D84C51', '🟠 Atenção': '#EE8133',
                       '🟡 Observação': '#F4B41A', '🟢 Nenhum': '#4CAF50'}.get(nv_mon, '#2D325E')
            st.markdown(f"""
            <div style="background:{cor_mon}15; border-left:6px solid {cor_mon}; border-radius:8px; padding:16px;">
                <h3 style="color:{cor_mon}; margin:0;">{nv_mon} — {aluno_ev_sel}</h3>
                <p style="margin:6px 0 0; color:#555;">{n_s_mon} sinal(is) identificado(s)</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            detalhes_mon = []
            if row_mon['S1_IEG_BAIXO']:  detalhes_mon.append(("🔴 S1", "IEG < 5.5", "Engajamento crítico"))
            if row_mon['S2_IPS_CRITICO']: detalhes_mon.append(("🔴 S2", "IPS < 5.0", "Aspecto psicossocial crítico"))
            if row_mon['S3_QUEDA_PEDRA']: detalhes_mon.append(("🔴 S3", "Queda de pedra", "Regrediu de nível entre 2020 e 2022"))
            if row_mon['S4_IDA_BAIXO']:  detalhes_mon.append(("🔴 S4", "IDA < 5.5", "Desempenho acadêmico baixo"))
            if row_mon['S5_ESTAGNACAO']:  detalhes_mon.append(("🔴 S5", "Estagnação >4 anos", "Sem progressão de nível por período prolongado"))
            if detalhes_mon:
                for sinal, criterio, desc in detalhes_mon:
                    st.markdown(f"**{sinal} — {criterio}:** {desc}")
            else:
                st.success("Nenhum sinal de risco identificado para este aluno.")
            c_val1, c_val2, c_val3 = st.columns(3)
            c_val1.metric("IEG", f"{row_mon.get('IEG', '—'):.2f}" if not pd.isna(row_mon.get('IEG', np.nan)) else "—")
            c_val2.metric("IPS", f"{row_mon.get('IPS', '—'):.2f}" if not pd.isna(row_mon.get('IPS', np.nan)) else "—")
            c_val3.metric("IDA", f"{row_mon.get('IDA', '—'):.2f}" if not pd.isna(row_mon.get('IDA', np.nan)) else "—")

        st.markdown("### 📋 Alunos que Precisam de Atenção (≥ 2 sinais)")
        busca_mon = st.text_input("Buscar por nome:", key="busca_mon_tab")
        show_mon = df_mon[df_mon['EM_ALERTA'] == 1][
            ['NOME', 'N_SINAIS', 'NIVEL_ALERTA', 'IEG', 'IPS', 'IDA', 'ANOS_PM',
             'S1_IEG_BAIXO', 'S2_IPS_CRITICO', 'S3_QUEDA_PEDRA', 'S4_IDA_BAIXO', 'S5_ESTAGNACAO']
        ].copy()
        show_mon.columns = ['Nome', 'Sinais', 'Nível', 'IEG', 'IPS', 'IDA', 'Anos PM',
                            'S1', 'S2', 'S3', 'S4', 'S5']
        show_mon = show_mon.sort_values('Sinais', ascending=False)
        if busca_mon:
            show_mon = show_mon[show_mon['Nome'].str.contains(busca_mon.upper(), na=False)]
        st.dataframe(show_mon, use_container_width=True, height=350)

        with st.expander("➕ Sobre o sistema de 5 sinais"):
            st.markdown("""
            | Sinal | Critério | O que indica |
            |-------|----------|--------------|
            | S1 — Engajamento | IEG < 5.5 | Baixa participação e motivação |
            | S2 — Psicossocial | IPS < 5.0 | Vulnerabilidade socioemocional |
            | S3 — Queda de nível | Pedra 2022 < Pedra 2020 | Retrocesso no programa |
            | S4 — Desempenho | IDA < 5.5 | Dificuldade acadêmica persistente |
            | S5 — Estagnação | ANOS_PM > 4 e sem progressão | Falta de avanço prolongada |

            **Classificação:**
            - 🟢 0 sinais → Situação estável
            - 🟡 1 sinal → Observação (monitorar)
            - 🟠 2 sinais → Atenção (intervenção recomendada)
            - 🔴 3+ sinais → Crítico (intervenção urgente)
            """)

    # ─────────────────────────────────────────────────────────────────────────
    # COLUNA 2 — ANÁLISE POR INTELIGÊNCIA ARTIFICIAL
    # ─────────────────────────────────────────────────────────────────────────
    with col_ia:
        st.markdown("### 🤖 Análise por IA")

        modelo_churn_ev = carregar_modelo_churn()
        if modelo_churn_ev is not None:
            # ── Preparar features para toda a base ───────────────────────────
            df_ia = df_mon.copy()
            df_ia['PEDRA_NUM'] = df_ia['PEDRA_2022'].map(_ORD_MON).fillna(0)
            df_ia['MEDIA_INDICADORES'] = df_ia[['IAA', 'IEG', 'IPS', 'IDA', 'IPV', 'IAN']].mean(axis=1)
            for _fc in ['IAA', 'IEG', 'IPS', 'IDA', 'IPV', 'IAN', 'FASE', 'ANOS_PM']:
                if _fc not in df_ia.columns:
                    df_ia[_fc] = 0.0

            probs_ia = modelo_churn_ev.predizer_lote(df_ia)
            df_ia['PROB_CHURN'] = probs_ia

            n_estavel = int((df_ia['PROB_CHURN'] < 0.30).sum())
            n_acomp   = int(((df_ia['PROB_CHURN'] >= 0.30) & (df_ia['PROB_CHURN'] <= 0.60)).sum())
            n_atencao = int((df_ia['PROB_CHURN'] > 0.60).sum())
            total_ia  = len(df_ia)

            # ── Distribuição de risco por IA ─────────────────────────────────
            st.markdown(f"""
            <div style="display:grid; gap:10px; margin-bottom:16px;">
                <div style="background:#27AE6015; border-left:4px solid #27AE60; border-radius:8px;
                            padding:12px 16px; display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-size:13px; color:#444;">🟢 Situação Estável</div>
                    <div style="font-size:18px; font-weight:700; color:#27AE60;">{n_estavel}<br><span style="font-size:11px; font-weight:400;">({n_estavel/total_ia*100:.0f}%)</span></div>
                </div>
                <div style="background:#F4B41A15; border-left:4px solid #F4B41A; border-radius:8px;
                            padding:12px 16px; display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-size:13px; color:#444;">🟡 Acompanhamento Recomendado</div>
                    <div style="font-size:18px; font-weight:700; color:#EE8133;">{n_acomp}<br><span style="font-size:11px; font-weight:400;">({n_acomp/total_ia*100:.0f}%)</span></div>
                </div>
                <div style="background:#D84C5115; border-left:4px solid #D84C51; border-radius:8px;
                            padding:12px 16px; display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-size:13px; color:#444;">🔴 Atenção Necessária</div>
                    <div style="font-size:18px; font-weight:700; color:#D84C51;">{n_atencao}<br><span style="font-size:11px; font-weight:400;">({n_atencao/total_ia*100:.0f}%)</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Consulta individual ──────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### Consultar Aluno")
            _alunos_ia = [""] + list(
                df_ia.dropna(subset=['NOME']).sort_values('PROB_CHURN', ascending=False)['NOME']
            )
            _aluno_ia_sel = st.selectbox(
                "Selecionar aluno:", _alunos_ia, key="ia_sel_aluno"
            )

            if _aluno_ia_sel:
                _row_ia  = df_ia[df_ia['NOME'] == _aluno_ia_sel].iloc[0]
                _prob_ia = float(_row_ia['PROB_CHURN'])
                if _prob_ia < 0.30:
                    _cor_ia = '#27AE60'; _badge_ia = '🟢 Situação Estável'
                elif _prob_ia <= 0.60:
                    _cor_ia = '#EE8133'; _badge_ia = '🟡 Acompanhamento Recomendado'
                else:
                    _cor_ia = '#D84C51'; _badge_ia = '🔴 Atenção Necessária'
                st.markdown(f"""
                <div style="background:{_cor_ia}15; border-left:5px solid {_cor_ia};
                            border-radius:8px; padding:14px; margin-top:8px;">
                    <div style="font-size:11px; color:#666; font-weight:600;
                                text-transform:uppercase; margin-bottom:4px;">Análise por IA</div>
                    <div style="font-size:16px; font-weight:700; color:{_cor_ia};
                                margin-bottom:4px;">{_badge_ia}</div>
                    <div style="font-size:13px; color:#777;">
                        Probabilidade de risco: {_prob_ia:.0%}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── Texto explicativo ────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div style="background:#F5F5F5; border-radius:8px; padding:14px;
                        font-size:13px; color:#555; line-height:1.6;">
                Este modelo aprendeu com 499 casos reais de evasão registrados
                entre 2020 e 2022. Ele compara o perfil acadêmico atual de cada
                aluno com o padrão dos que deixaram o programa, sem depender de
                regras construídas manualmente.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Modelo de IA não disponível. Execute `python train_model.py` para gerar.")

    # ── Rodapé — seção colapsável ─────────────────────────────────────────────
    with st.expander("➕ Como melhorar esta análise"):
        st.markdown("""
        O modelo atual analisa indicadores acadêmicos e socioemocionais.
        A incorporação de dados complementares pode elevar significativamente
        a precisão desta análise. Recomendamos estruturar a coleta dos
        seguintes dados no próximo ciclo:

        - Situação de deslocamento até o programa
        - Faixa de renda familiar
        - Composição familiar e responsável principal
        - Histórico de ausências e motivos
        - Nível de participação em atividades extracurriculares
        - Frequência de contato com responsáveis

        Com esses dados, estima-se que a taxa de acerto desta análise
        pode alcançar **80%+**.
        """)


# =============================================================================
# PÁGINA: VISÃO 360° DO ALUNO
# =============================================================================
elif pagina == "👤 Visão 360° do Aluno":
    st.markdown("""
    <div class="section-header">
        <h2>Visão 360° do Aluno</h2>
    </div>
    """, unsafe_allow_html=True)

    nomes_lista = sorted(df_xlsx['NOME'].dropna().str.upper().unique())
    nome_sel = st.selectbox("Selecione o aluno:", nomes_lista)

    mask_nome = df_xlsx['NOME'].str.upper() == nome_sel
    if mask_nome.any():
        row = df_xlsx[mask_nome].iloc[0]

        pedra = str(row.get('PEDRA_2022', '—'))
        icone_pedra = _PEDRA_ICONE.get(pedra, '📚')
        cor_pedra   = _PEDRA_COR.get(pedra, '#2D325E')
        fase_val    = int(row['FASE']) if not pd.isna(row.get('FASE', np.nan)) else '—'
        anos_val    = int(row['ANOS_PM']) if not pd.isna(row.get('ANOS_PM', np.nan)) else '—'
        genero_val  = str(row.get('GENERO', '—'))
        pv_val      = str(row.get('PONTO_VIRADA', '—'))

        _col_hdr, _col_gauge = st.columns([1, 1])
        with _col_hdr:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg,{cor_pedra}22,#FAFAFA);
                        border-left:6px solid {cor_pedra}; border-radius:8px; padding:20px;
                        margin-bottom:20px; min-height:230px; display:flex; flex-direction:column; justify-content:center;">
                <h2 style="color:{cor_pedra}; margin:0;">{icone_pedra} {nome_sel}</h2>
                <p style="margin:8px 0 0; color:#555;">
                    <strong>Pedra:</strong> {pedra} &nbsp;|&nbsp;
                    <strong>Fase:</strong> {fase_val} &nbsp;|&nbsp;
                    <strong>Anos na PM:</strong> {anos_val} &nbsp;|&nbsp;
                    <strong>Gênero:</strong> {genero_val} &nbsp;|&nbsp;
                    <strong>Ponto de Virada:</strong> {pv_val}
                </p>
            </div>
            """, unsafe_allow_html=True)
        with _col_gauge:
            _inde_raw = row.get('INDE', np.nan)
            _score_360 = float(_inde_raw) if not pd.isna(_inde_raw) else 5.0
            if _score_360 <= 4:
                _msg_360 = "Requer atenção imediata"
            elif _score_360 <= 6:
                _msg_360 = "Em desenvolvimento — acompanhamento necessário"
            elif _score_360 <= 8:
                _msg_360 = "Progredindo bem"
            else:
                _msg_360 = "Excelente desenvolvimento"
            _fig_g360 = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=_score_360,
                title={'text': "Índice de Desenvolvimento Geral", 'font': {'size': 15, 'color': '#EE8133'}},
                delta={'reference': 7.0, 'increasing': {'color': '#27AE60'}, 'decreasing': {'color': '#D84C51'}},
                gauge={
                    'axis': {'range': [0, 10], 'tickcolor': '#555'},
                    'bar': {'color': '#EE8133'},
                    'bgcolor': 'rgba(0,0,0,0)',
                    'bordercolor': '#EE8133',
                    'steps': [
                        {'range': [0, 4], 'color': 'rgba(216, 76, 81, 0.1)'},
                        {'range': [4, 7], 'color': 'rgba(244, 180, 26, 0.1)'},
                        {'range': [7, 10], 'color': 'rgba(39, 174, 96, 0.1)'},
                    ],
                    'threshold': {'line': {'color': '#EE8133', 'width': 4}, 'thickness': 0.85, 'value': _score_360},
                }
            ))
            _fig_g360.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font={'color': '#333'},
                height=250,
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(_fig_g360, use_container_width=True)
            st.markdown(
                f"<p style='text-align:center; color:#666; font-size:13px; margin-top:-16px;'>{_msg_360}</p>",
                unsafe_allow_html=True,
            )

        # ── Indicadores ──────────────────────────────────────────────────────
        cols_ind = st.columns(5)
        for col_st, ind, label in zip(
            cols_ind,
            ['INDE', 'IDA', 'IEG', 'IAA', 'IPS'],
            ['INDE',  'IDA', 'IEG', 'IAA', 'IPS']
        ):
            val = row.get(ind, np.nan)
            v_str = f"{val:.2f}" if not pd.isna(val) else "—"
            cor_v = '#27AE60' if not pd.isna(val) and val >= 7 else (
                    '#EE8133' if not pd.isna(val) and val >= 5 else '#D84C51')
            col_st.markdown(f"""
            <div style="background:{cor_v}15; border:2px solid {cor_v}; border-radius:8px;
                        padding:14px; text-align:center; margin-bottom:8px;">
                <div style="font-size:22px; font-weight:700; color:{cor_v};">{v_str}</div>
                <div style="font-size:12px; color:#666; margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

        # ── Notas ─────────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        cols_nota = st.columns(3)
        for col_st, col_nota, label in zip(
            cols_nota,
            ['NOTA_MAT', 'NOTA_PORT', 'NOTA_ING'],
            ['Matemática', 'Português', 'Inglês']
        ):
            val = row.get(col_nota, np.nan)
            v_str = f"{val:.1f}" if not pd.isna(val) else "—"
            cor_v = '#27AE60' if not pd.isna(val) and val >= 7 else (
                    '#EE8133' if not pd.isna(val) and val >= 5 else '#D84C51')
            col_st.markdown(f"""
            <div style="background:#F5F5F5; border-radius:8px; padding:14px; text-align:center;">
                <div style="font-size:20px; font-weight:700; color:{cor_v};">{v_str}</div>
                <div style="font-size:13px; color:#666;">{label}</div>
            </div>""", unsafe_allow_html=True)

        # ── Preparar dados para modelos ────────────────────────────────────────
        def _safe(v, default=0.0):
            try: return float(v) if not pd.isna(v) else default
            except: return default

        genero_fem_360 = 1 if str(row.get('GENERO', '')) == 'Menina' else 0
        pedra_num_360  = _PEDRA_ORD.get(str(row.get('PEDRA_2022', '')), 0)
        p2020 = _PEDRA_ORD.get(str(row.get('PEDRA_2020', '')), 0)
        p2021 = _PEDRA_ORD.get(str(row.get('PEDRA_2021', '')), 0)
        p2022 = _PEDRA_ORD.get(str(row.get('PEDRA_2022', '')), 0)
        ref_360 = p2021 if p2021 > 0 else p2020
        ev_pedra_360 = p2022 - ref_360 if ref_360 > 0 else 0

        med_notas_360 = _safe(row.get('MEDIA_NOTAS'), (_safe(row.get('NOTA_MAT')) + _safe(row.get('NOTA_PORT')) + _safe(row.get('NOTA_ING'))) / 3)
        _iaa_360 = _safe(row.get('IAA')); _ieg_360 = _safe(row.get('IEG'))
        _ips_360 = _safe(row.get('IPS')); _ida_360 = _safe(row.get('IDA'))
        _ipv_360 = _safe(row.get('IPV')); _ian_360 = _safe(row.get('IAN'))
        med_ind_360 = (_iaa_360 + _ieg_360 + _ips_360 + _ida_360 + _ipv_360 + _ian_360) / 6

        dados_360 = {
            'IAA': _iaa_360, 'IEG': _ieg_360,
            'IPS': _ips_360, 'IDA': _ida_360,
            'IPV': _ipv_360, 'IAN': _ian_360,
            'IPP': _safe(row.get('IPP')),
            'FASE': _safe(row.get('FASE'), 1.0),
            'ANOS_PM': _safe(row.get('ANOS_PM')),
            'PEDRA_NUM': float(pedra_num_360),
            'NOTA_MAT':  _safe(row.get('NOTA_MAT'), 5.0),
            'NOTA_PORT': _safe(row.get('NOTA_PORT'), 5.0),
            'NOTA_ING':  _safe(row.get('NOTA_ING'), 5.0),
            'MEDIA_NOTAS': med_notas_360,
            'MEDIA_INDICADORES': med_ind_360,
            'GENERO_FEMININO': float(genero_fem_360),
            'GENERO_NUM': 1.0 - float(genero_fem_360),
            'INSTITUICAO_COD': 0.0,
            'EVOLUCAO_PEDRA': float(ev_pedra_360),
        }

        # ── Cards preditivos ──────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🤖 Análise Preditiva Completa")
        pc1, pc2, pc3, pc4 = st.columns(4)

        modelo_def_360 = carregar_modelo_treinado()
        with pc1:
            if modelo_def_360:
                try:
                    res_d = modelo_def_360.predizer_risco(dados_360)
                    prob_d = res_d['probabilidade_risco']
                    
                    if prob_d <= 0.20:
                        cor_d = '#27AE60' # Verde
                        status_d = '✅ Baixo Risco'
                    elif prob_d <= 0.50:
                        cor_d = '#F4B41A' # Amarelo
                        status_d = '🟡 Médio Risco'
                    else:
                        cor_d = '#D84C51' # Vermelho
                        status_d = '🔴 Alto Risco'
                        
                    st.markdown(f"""
                    <div style="background:{cor_d}15; border:2px solid {cor_d}; border-radius:10px;
                                padding:16px; text-align:center;">
                        <div style="font-size:12px; color:#555; font-weight:600;">RISCO DE DEFASAGEM</div>
                        <div style="font-size:22px; font-weight:700; color:{cor_d}; margin:8px 0;">
                            {status_d}</div>
                        <div style="font-size:12px; color:#777;">Prob: {prob_d:.0%}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception:
                    st.warning("Modelo indisponível")
            else:
                st.info("Modelo defasagem não carregado")

        modelo_pedra_360 = carregar_modelo_pedra()
        with pc2:
            if modelo_pedra_360:
                try:
                    res_pp = modelo_pedra_360.predizer_pedra(dados_360)
                    pp_pred = res_pp['pedra']
                    pp_conf = res_pp['confianca']
                    cor_pp  = _PEDRA_COR.get(pp_pred, '#2D325E')
                    ico_pp  = _PEDRA_ICONE.get(pp_pred, '📚')
                    st.markdown(f"""
                    <div style="background:{cor_pp}15; border:2px solid {cor_pp}; border-radius:10px;
                                padding:16px; text-align:center;">
                        <div style="font-size:12px; color:#555; font-weight:600;">CLASSIFICAÇÃO PREVISTA</div>
                        <div style="font-size:22px; font-weight:700; color:{cor_pp}; margin:8px 0;">
                            {ico_pp} {pp_pred}</div>
                        <div style="font-size:12px; color:#777;">Confiança: {pp_conf:.0%}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception:
                    st.warning("Modelo indisponível")
            else:
                st.info("Modelo pedra não carregado")

        modelo_pv_360 = carregar_modelo_pv()
        with pc3:
            if modelo_pv_360:
                try:
                    res_pv = modelo_pv_360.predizer_pv(dados_360)
                    prob_pv = res_pv['probabilidade']
                    atingiu_pv = res_pv['atingiu'] == 1
                    cor_pv = '#27AE60' if atingiu_pv else '#EE8133'
                    st.markdown(f"""
                    <div style="background:{cor_pv}15; border:2px solid {cor_pv}; border-radius:10px;
                                padding:16px; text-align:center;">
                        <div style="font-size:12px; color:#555; font-weight:600;">MOMENTO DE VIRADA</div>
                        <div style="font-size:20px; font-weight:700; color:{cor_pv}; margin:8px 0;">
                            {'✨ Próximo' if atingiu_pv else '📈 Em Desenvolvimento'}</div>
                        <div style="font-size:12px; color:#777;">Prob: {prob_pv:.0%}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception:
                    st.warning("Modelo indisponível")
            else:
                st.info("Modelo PV não carregado")

        with pc4:
            nivel_360, n_s_360, sinais_360 = calcular_alerta_evasao(dados_360)
            cor_360 = {'Alto': '#D84C51', 'Moderado': '#EE8133', 'Baixo': '#27AE60'}[nivel_360]
            ico_360 = {'Alto': '🔴', 'Moderado': '🟠', 'Baixo': '🟢'}[nivel_360]
            st.markdown(f"""
            <div style="background:{cor_360}15; border:2px solid {cor_360}; border-radius:10px;
                        padding:16px; text-align:center;">
                <div style="font-size:12px; color:#555; font-weight:600;">ALERTA DE EVASÃO</div>
                <div style="font-size:22px; font-weight:700; color:{cor_360}; margin:8px 0;">
                    {ico_360} {nivel_360}</div>
                <div style="font-size:12px; color:#777;">{n_s_360} sinal(is) ativo(s)</div>
            </div>""", unsafe_allow_html=True)

        if sinais_360:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("➕ Detalhes dos Sinais de Risco"):
                for s in sinais_360:
                    st.markdown(f"- ⚠️ {s}")

        # ── Histórico INDE ─────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📈 Evolução Histórica")
        hist_360 = df_long[df_long['NOME'].str.upper() == nome_sel].sort_values('ANO')
        if not hist_360.empty and 'INDE' in hist_360.columns and hist_360['INDE'].notna().any():
            fig_hist = px.line(
                hist_360, x='ANO', y='INDE', markers=True,
                title=f'Evolução do INDE — {nome_sel}',
                template='plotly_white', color_discrete_sequence=['#EE8133']
            )
            fig_hist.update_traces(line_width=3, marker_size=10)
            fig_hist.update_layout(yaxis_range=[0, 10], yaxis_title='INDE', xaxis_title='Ano')
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Histórico longitudinal não disponível para este aluno.")

        # ── Recomendação pedagógica ────────────────────────────────────────────
        st.markdown("### 💡 Recomendação Pedagógica")
        recs = []
        if dados_360['IEG'] < 5.5:
            recs.append("🎯 **Engajamento:** Propor atividades mais interativas e acompanhamento próximo.")
        if dados_360['IPS'] < 5.0:
            recs.append("🧠 **Psicossocial:** Encaminhar para suporte psicopedagógico.")
        if dados_360['IDA'] < 5.5:
            recs.append("📚 **Desempenho:** Reforço escolar em matemática e português.")
        if dados_360['IAA'] - dados_360['IDA'] > 2.0:
            recs.append("🔍 **Autoavaliação:** Trabalhar percepção realista do próprio desempenho.")
        if not recs:
            recs.append("✅ Indicadores adequados. Manter acompanhamento regular.")
        for r in recs:
            st.markdown(r)

    else:
        st.warning("Aluno não encontrado na base de dados.")


# =============================================================================
# PÁGINA: PREDIÇÃO INDIVIDUAL
# =============================================================================
elif pagina == "🧑‍🎓 Predição Individual":
    st.markdown("""
    <div class="section-header">
        <h2>Predição Individual</h2>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("> Insira os indicadores de um aluno para receber a análise preditiva completa dos 3 modelos e do sistema de alerta.")

    with st.form("form_predicao_individual"):
        fc1, fc2, fc3 = st.columns(3)

        with fc1:
            st.markdown("#### Indicadores Pedagógicos")
            f_iaa  = st.slider("IAA — Autoavaliação",       0.0, 10.0, 7.0, 0.1)
            f_ieg  = st.slider("IEG — Engajamento",         0.0, 10.0, 7.0, 0.1)
            f_ips  = st.slider("IPS — Psicossocial",        0.0, 10.0, 7.0, 0.1)
            f_ida  = st.slider("IDA — Desempenho Acadêm.",  0.0, 10.0, 7.0, 0.1)
            f_ipv  = st.slider("IPV — Ponto de Virada",     0.0, 10.0, 7.0, 0.1)
            f_ian  = st.slider("IAN — Nível Acadêmico",     0.0, 10.0, 7.0, 0.1)
            f_ipp  = st.slider("IPP — Psicopedagógico",     0.0, 10.0, 7.0, 0.1)

        with fc2:
            st.markdown("#### Notas e Trajetória")
            f_mat  = st.slider("Nota Matemática",  0.0, 10.0, 7.0, 0.1)
            f_port = st.slider("Nota Português",   0.0, 10.0, 7.0, 0.1)
            f_ing  = st.slider("Nota Inglês",      0.0, 10.0, 7.0, 0.1)
            f_fase = st.selectbox("Fase", list(range(1, 9)))
            f_anos = st.slider("Anos na Passos Mágicos", 1, 10, 3)

        with fc3:
            st.markdown("#### Perfil")
            f_pedra = st.selectbox("Pedra (classificação atual)", ['Quartzo', 'Ágata', 'Ametista', 'Topázio'])
            f_genero = st.selectbox("Gênero", ['Menino', 'Menina'])
            f_ev_pedra = st.slider("Evolução de Pedra (anos anteriores)", -3, 3, 0)

        submitted_f = st.form_submit_button("🔮 Analisar Aluno", use_container_width=True)

    if submitted_f:
        f_genero_fem  = 1 if f_genero == 'Menina' else 0
        f_genero_num  = 0 if f_genero == 'Menina' else 1
        f_pedra_num   = _PEDRA_ORD.get(f_pedra, 0)
        f_media_notas = (f_mat + f_port + f_ing) / 3
        f_media_ind   = (f_iaa + f_ieg + f_ips + f_ida + f_ipv + f_ian) / 6

        dados_form = {
            'IAA': f_iaa, 'IEG': f_ieg, 'IPS': f_ips, 'IDA': f_ida,
            'IPV': f_ipv, 'IAN': f_ian, 'IPP': f_ipp,
            'FASE': float(f_fase), 'ANOS_PM': float(f_anos),
            'PEDRA_NUM': float(f_pedra_num),
            'NOTA_MAT': f_mat, 'NOTA_PORT': f_port, 'NOTA_ING': f_ing,
            'MEDIA_NOTAS': f_media_notas, 'MEDIA_INDICADORES': f_media_ind,
            'GENERO_FEMININO': float(f_genero_fem),
            'GENERO_NUM': float(f_genero_num),
            'PV_NUM': 0.0,
            'INSTITUICAO_COD': 0.0,
            'EVOLUCAO_PEDRA': float(f_ev_pedra),
        }

        st.markdown("---")

        # ── Velocímetro no topo dos resultados ────────────────────────────────
        _col_res_info, _col_gauge_f = st.columns([1, 1])
        with _col_res_info:
            st.markdown("### 📊 Resultados da Análise")
            _score_form = round(f_media_ind, 2)
            if _score_form <= 4:
                _msg_f = "Requer atenção imediata"
            elif _score_form <= 6:
                _msg_f = "Em desenvolvimento — acompanhamento necessário"
            elif _score_form <= 8:
                _msg_f = "Progredindo bem"
            else:
                _msg_f = "Excelente desenvolvimento"
            st.markdown(
                f"<p style='color:#555; font-size:14px; margin-top:8px;'>"
                f"Perfil de desenvolvimento estimado com base nos indicadores inseridos.</p>",
                unsafe_allow_html=True,
            )
        with _col_gauge_f:
            _score_form = round(f_media_ind, 2)
            _fig_gf = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=_score_form,
                title={'text': "Índice de Desenvolvimento Geral", 'font': {'size': 15, 'color': '#EE8133'}},
                delta={'reference': 7.0, 'increasing': {'color': '#27AE60'}, 'decreasing': {'color': '#D84C51'}},
                gauge={
                    'axis': {'range': [0, 10], 'tickcolor': '#555'},
                    'bar': {'color': '#EE8133'},
                    'bgcolor': 'rgba(0,0,0,0)',
                    'bordercolor': '#EE8133',
                    'steps': [
                        {'range': [0, 4], 'color': 'rgba(216, 76, 81, 0.1)'},
                        {'range': [4, 7], 'color': 'rgba(244, 180, 26, 0.1)'},
                        {'range': [7, 10], 'color': 'rgba(39, 174, 96, 0.1)'},
                    ],
                    'threshold': {'line': {'color': '#EE8133', 'width': 4}, 'thickness': 0.85, 'value': _score_form},
                }
            ))
            _fig_gf.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font={'color': '#333'},
                height=250,
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(_fig_gf, use_container_width=True)
            if _score_form <= 4:
                _msg_f = "Requer atenção imediata"
            elif _score_form <= 6:
                _msg_f = "Em desenvolvimento — acompanhamento necessário"
            elif _score_form <= 8:
                _msg_f = "Progredindo bem"
            else:
                _msg_f = "Excelente desenvolvimento"
            st.markdown(
                f"<p style='text-align:center; color:#666; font-size:13px; margin-top:-16px;'>{_msg_f}</p>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        pr1, pr2, pr3, pr4 = st.columns(4)

        modelo_def_f = carregar_modelo_treinado()
        with pr1:
            if modelo_def_f:
                try:
                    res = modelo_def_f.predizer_risco(dados_form)
                    prob = res['probabilidade_risco']
                    em_risco_f = res['risco'] == 1
                    cor = '#D84C51' if em_risco_f else '#27AE60'
                    st.markdown(f"""
                    <div style="background:{cor}15; border:2px solid {cor}; border-radius:10px;
                                padding:16px; text-align:center;">
                        <div style="font-size:12px; color:#555; font-weight:600;">RISCO DE DEFASAGEM</div>
                        <div style="font-size:22px; font-weight:700; color:{cor}; margin:8px 0;">
                            {'⚠️ Em Risco' if em_risco_f else '✅ Sem Risco'}</div>
                        <div style="font-size:12px; color:#777;">Prob: {prob:.0%}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erro: {e}")
            else:
                st.info("Modelo não carregado")

        modelo_pedra_f = carregar_modelo_pedra()
        with pr2:
            if modelo_pedra_f:
                try:
                    res = modelo_pedra_f.predizer_pedra(dados_form)
                    pp = res['pedra']
                    conf = res['confianca']
                    cor = _PEDRA_COR.get(pp, '#2D325E')
                    ico = _PEDRA_ICONE.get(pp, '📚')
                    st.markdown(f"""
                    <div style="background:{cor}15; border:2px solid {cor}; border-radius:10px;
                                padding:16px; text-align:center;">
                        <div style="font-size:12px; color:#555; font-weight:600;">CLASSIFICAÇÃO PREVISTA</div>
                        <div style="font-size:22px; font-weight:700; color:{cor}; margin:8px 0;">
                            {ico} {pp}</div>
                        <div style="font-size:12px; color:#777;">Confiança: {conf:.0%}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erro: {e}")
            else:
                st.info("Modelo não carregado")

        modelo_pv_f = carregar_modelo_pv()
        with pr3:
            if modelo_pv_f:
                try:
                    res = modelo_pv_f.predizer_pv(dados_form)
                    prob = res['probabilidade']
                    atingiu_f = res['atingiu'] == 1
                    cor = '#27AE60' if atingiu_f else '#EE8133'
                    st.markdown(f"""
                    <div style="background:{cor}15; border:2px solid {cor}; border-radius:10px;
                                padding:16px; text-align:center;">
                        <div style="font-size:12px; color:#555; font-weight:600;">MOMENTO DE VIRADA</div>
                        <div style="font-size:20px; font-weight:700; color:{cor}; margin:8px 0;">
                            {'✨ Próximo' if atingiu_f else '📈 Em Desenvolvimento'}</div>
                        <div style="font-size:12px; color:#777;">Prob: {prob:.0%}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erro: {e}")
            else:
                st.info("Modelo não carregado")

        with pr4:
            nivel_f, n_s_f, sinais_f = calcular_alerta_evasao(dados_form)
            cor_f = {'Alto': '#D84C51', 'Moderado': '#EE8133', 'Baixo': '#27AE60'}[nivel_f]
            ico_f = {'Alto': '🔴', 'Moderado': '🟠', 'Baixo': '🟢'}[nivel_f]
            st.markdown(f"""
            <div style="background:{cor_f}15; border:2px solid {cor_f}; border-radius:10px;
                        padding:16px; text-align:center;">
                <div style="font-size:12px; color:#555; font-weight:600;">ALERTA DE EVASÃO</div>
                <div style="font-size:22px; font-weight:700; color:{cor_f}; margin:8px 0;">
                    {ico_f} {nivel_f}</div>
                <div style="font-size:12px; color:#777;">{n_s_f} sinal(is) ativo(s)</div>
            </div>""", unsafe_allow_html=True)

        if sinais_f:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("➕ Detalhes dos Sinais de Risco"):
                for s in sinais_f:
                    st.markdown(f"- ⚠️ {s}")
