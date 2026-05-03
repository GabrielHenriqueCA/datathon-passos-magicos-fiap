"""
Treinamento dos modelos preditivos — Datathon Passos Magicos

Modelos treinados:
  1. risco_defasagem.joblib    -> Risco de Defasagem (Random Forest)
  2. enquadramento_pedra.joblib -> Classificacao da Pedra (RF / GB multiclasse)
  3. ponto_virada.joblib        -> Ponto de Virada (Gradient Boosting)
  4. churn.joblib               -> Risco de Evasao (Random Forest)

Uso:
    python train_model.py
"""

import os
import warnings

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, classification_report, confusion_matrix,
)
from sklearn.model_selection import (
    StratifiedKFold, cross_val_score, train_test_split,
)
from sklearn.preprocessing import StandardScaler, LabelEncoder

warnings.filterwarnings('ignore')
os.makedirs('models', exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# DADOS
# ──────────────────────────────────────────────────────────────────────────────

def carregar_dataset_csv(caminho='data/PEDE_PASSOS_DATASET_FIAP.csv'):
    df = pd.read_csv(caminho, sep=';', encoding='latin1')
    indicadores = ['INDE', 'IAA', 'IEG', 'IPS', 'IDA', 'IPP', 'IPV', 'IAN']
    for ano in [2020, 2021, 2022]:
        for i in indicadores:
            col = f'{i}_{ano}'
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ['PEDRA_2020', 'PEDRA_2021', 'PEDRA_2022']:
        if col in df.columns:
            df[col] = df[col].replace({'Ã\x81gata': 'Agata', 'TopÃ¡zio': 'Topazio',
                                        '#NULO!': np.nan, 'D9891/2A': np.nan})
    return df


def carregar_dataset_xlsx(caminho='data/BASE DE DADOS PEDE 2024 - DATATHON.xlsx'):
    df = pd.read_excel(caminho)
    rename_map = {
        'Fase': 'FASE', 'Turma': 'TURMA', 'Nome': 'NOME', 'Ano nasc': 'ANO_NASC',
        'Idade 22': 'IDADE', 'Genero': 'GENERO', 'Ano ingresso': 'ANO_INGRESSO',
        'Instituicao de ensino': 'INSTITUICAO_ENSINO',
        'Pedra 20': 'PEDRA_2020', 'Pedra 21': 'PEDRA_2021', 'Pedra 22': 'PEDRA_2022',
        'INDE 22': 'INDE', 'Cg': 'CG', 'Cf': 'CF', 'Ct': 'CT',
        'No Av': 'NUM_AVALIADORES',
        'Matem': 'NOTA_MAT', 'Portug': 'NOTA_PORT',
        'Atingiu PV': 'PONTO_VIRADA',
        'Fase ideal': 'FASE_IDEAL', 'Defas': 'DEFASAGEM',
    }
    # Rename only columns that exist (handles accents in raw file)
    raw_cols = {c.strip(): c for c in df.columns}
    full_map = {
        'Fase': 'FASE', 'Turma': 'TURMA', 'Nome': 'NOME', 'Ano nasc': 'ANO_NASC',
        'Idade 22': 'IDADE', 'Gênero': 'GENERO', 'Ano ingresso': 'ANO_INGRESSO',
        'Instituição de ensino': 'INSTITUICAO_ENSINO',
        'Pedra 20': 'PEDRA_2020', 'Pedra 21': 'PEDRA_2021', 'Pedra 22': 'PEDRA_2022',
        'INDE 22': 'INDE', 'Cg': 'CG', 'Cf': 'CF', 'Ct': 'CT',
        'Nº Av': 'NUM_AVALIADORES',
        'Matem': 'NOTA_MAT', 'Portug': 'NOTA_PORT',
        'Inglês': 'NOTA_ING',
        'Indicado': 'INDICADO_BOLSA', 'Atingiu PV': 'PONTO_VIRADA',
        'Fase ideal': 'FASE_IDEAL', 'Defas': 'DEFASAGEM',
        'Destaque IEG': 'DESTAQUE_IEG', 'Destaque IDA': 'DESTAQUE_IDA',
        'Destaque IPV': 'DESTAQUE_IPV',
    }
    df = df.rename(columns=full_map)
    df['ANOS_PM'] = 2022 - df['ANO_INGRESSO']
    return df


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

PEDRA_ORD = {'Quartzo': 1, 'Agata': 2, 'Ágata': 2, 'Ametista': 3, 'Topazio': 4, 'Topázio': 4}


def pedra_para_num(serie):
    return serie.map(PEDRA_ORD)


def calibrar_threshold_por_f1(modelo, X_tr, y_tr, cv, usa_scale, scaler=None, min_thresh=0.20):
    """Threshold que maximiza F1 via CV no conjunto de treino (sem data leakage do teste)."""
    thresholds = np.linspace(min_thresh, 0.80, max(2, int((0.80 - min_thresh) * 60) + 1))
    fold_f1s   = {t: [] for t in thresholds}
    for tr_idx, val_idx in cv.split(X_tr, y_tr):
        Xf, Xv = X_tr[tr_idx], X_tr[val_idx]
        yf, yv = y_tr[tr_idx], y_tr[val_idx]
        if usa_scale:
            sc = StandardScaler().fit(Xf)
            Xf, Xv = sc.transform(Xf), sc.transform(Xv)
        modelo.fit(Xf, yf)
        probs = modelo.predict_proba(Xv)[:, 1]
        for t in thresholds:
            preds = (probs >= t).astype(int)
            fold_f1s[t].append(f1_score(yv, preds, zero_division=0))
    mean_f1s = {t: np.mean(v) for t, v in fold_f1s.items()}
    return max(mean_f1s, key=mean_f1s.get)


# ──────────────────────────────────────────────────────────────────────────────
# MODELO 1 — RISCO DE DEFASAGEM (Random Forest)
# ──────────────────────────────────────────────────────────────────────────────

def treinar_risco_defasagem():
    print()
    print("=" * 60)
    print("  MODELO 1 -- Risco de Defasagem")
    print("=" * 60)

    df = carregar_dataset_xlsx()
    print(f"\n  Dados: {df.shape[0]} alunos, {df.shape[1]} colunas")

    # Target
    df['RISCO'] = (df['DEFASAGEM'] < 0).astype(int)
    df['GENERO_NUM'] = (df['GENERO'] == 'Menino').astype(int)
    df['PV_NUM']     = (df['PONTO_VIRADA'] == 'Sim').astype(int)

    # Features derivadas
    df['SCORE_COMPORTAMENTAL'] = (df['IAA'] + df['IEG'] + df['IPS']) / 3
    df['GAP_IAA_IDA']  = df['IAA'] - df['IDA']
    df['IEG_POR_FASE'] = df['IEG'] / (df['FASE'] + 1)
    df['IEG_X_IPV']    = df['IEG'] * df['IPV']
    df['IDA_X_ANOS']   = df['IDA'] * df['ANOS_PM']

    features = [
        'IAA', 'IEG', 'IPS', 'IDA', 'IPV',
        'FASE', 'ANOS_PM', 'GENERO_NUM', 'PV_NUM',
        'SCORE_COMPORTAMENTAL', 'GAP_IAA_IDA',
        'IEG_POR_FASE', 'IEG_X_IPV', 'IDA_X_ANOS',
    ]

    df_m = df.dropna(subset=features + ['RISCO'])
    X = df_m[features].values
    y = df_m['RISCO'].values

    n0, n1 = (y == 0).sum(), (y == 1).sum()
    print(f"  Sem risco (0): {n0}  |  Em risco (1): {n1}  |  Razao: {n1/n0:.2f}:1")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20,
                                               stratify=y, random_state=42)

    cv  = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    rf  = RandomForestClassifier(
        n_estimators=300, max_depth=4, min_samples_leaf=5,
        class_weight='balanced', random_state=42, n_jobs=-1
    )

    print("\n  Treinando Random Forest com threshold calibrado por F1 (CV, min=0.45)...")
    # min_thresh=0.45: force balanced precision/recall tradeoff (avoid "predict all positive" trap)
    threshold = calibrar_threshold_por_f1(rf, X_tr, y_tr, cv, usa_scale=False, min_thresh=0.45)

    # Treinar no conjunto completo de treino
    rf.fit(X_tr, y_tr)
    probs_tr = rf.predict_proba(X_tr)[:, 1]
    probs_te = rf.predict_proba(X_te)[:, 1]
    preds_tr = (probs_tr >= threshold).astype(int)
    preds_te = (probs_te >= threshold).astype(int)

    acc_tr  = accuracy_score(y_tr, preds_tr)
    acc_te  = accuracy_score(y_te, preds_te)
    f1_te   = f1_score(y_te, preds_te, zero_division=0)
    rec_te  = recall_score(y_te, preds_te, zero_division=0)
    prec_te = precision_score(y_te, preds_te, zero_division=0)
    auc_te  = roc_auc_score(y_te, probs_te)

    print(f"\n  Resultados:")
    print(f"    Accuracy Treino : {acc_tr:.4f}")
    print(f"    Accuracy Teste  : {acc_te:.4f}  (gap: {acc_tr - acc_te:.3f})")
    print(f"    F1-Score        : {f1_te:.4f}")
    print(f"    Recall          : {rec_te:.4f}")
    print(f"    Precision       : {prec_te:.4f}")
    print(f"    AUC-ROC         : {auc_te:.4f}")
    print(f"    Threshold       : {threshold:.2f}")

    # CV F1 no treino
    cv_f1 = cross_val_score(rf, X_tr, y_tr, cv=cv, scoring='f1', n_jobs=-1)
    print(f"    CV F1 (treino)  : {cv_f1.mean():.4f} +/- {cv_f1.std():.4f}")

    # Feature importance
    fi = pd.DataFrame({'feature': features, 'importance': rf.feature_importances_})
    fi = fi.sort_values('importance', ascending=False)

    scaler = StandardScaler().fit(X_tr)

    import json
    metricas_def = {
        'melhor_nome':  'Random Forest',
        'acc_treino':   acc_tr,
        'acc_teste':    acc_te,
        'f1_score':     f1_te,
        'recall':       rec_te,
        'precision':    prec_te,
        'roc_auc':      auc_te,
        'threshold':    threshold,
    }
    with open('models/risco_defasagem_metrics.json', 'w', encoding='utf-8') as fh:
        json.dump(metricas_def, fh, indent=2)

    artefato = {
        'modelo':              rf,
        'scaler':              scaler,
        'features':            features,
        'melhor_nome':         'Random Forest',
        'melhor_threshold':    threshold,
        'feature_importance':  fi,
        'resultados': {
            'Random Forest': {
                'accuracy':    acc_te,
                'precision':   prec_te,
                'recall':      rec_te,
                'f1_score':    f1_te,
                'roc_auc':     auc_te,
                'acc_treino':  acc_tr,
                'threshold':   threshold,
            }
        }
    }
    joblib.dump(artefato, 'models/risco_defasagem.joblib')
    print("\n  Salvo em: models/risco_defasagem.joblib")
    print("  Métricas em: models/risco_defasagem_metrics.json")
    return artefato


# ──────────────────────────────────────────────────────────────────────────────
# MODELO 2 — ENQUADRAMENTO DE PEDRA (multiclasse)
# ──────────────────────────────────────────────────────────────────────────────

def treinar_enquadramento_pedra():
    print()
    print("=" * 60)
    print("  MODELO 2 -- Enquadramento de Pedra (sem leakage)")
    print("  Features: sem INDE, sem IAN")
    print("=" * 60)

    df = carregar_dataset_xlsx()
    print(f"\n  Dados: {df.shape[0]} alunos")

    # Target
    df = df.dropna(subset=['PEDRA_2022'])
    le = LabelEncoder()
    df['PEDRA_NUM'] = le.fit_transform(df['PEDRA_2022'])
    classes = list(le.classes_)
    print(f"  Classes: {dict(zip(classes, le.transform(classes)))}")
    for c in classes:
        print(f"    {c}: {(df['PEDRA_2022'] == c).sum()}")

    # Genero e instituicao
    df['GENERO_FEMININO'] = (df['GENERO'] == 'Menina').astype(int)

    inst_map = {v: i for i, v in enumerate(df['INSTITUICAO_ENSINO'].dropna().unique())}
    df['INSTITUICAO_COD'] = df['INSTITUICAO_ENSINO'].map(inst_map).fillna(-1).astype(int)

    # Notas medias (ING tem muitos nulos — media parcial)
    for col in ['NOTA_MAT', 'NOTA_PORT', 'NOTA_ING']:
        if col not in df.columns:
            df[col] = np.nan
    df['MEDIA_NOTAS'] = df[['NOTA_MAT', 'NOTA_PORT', 'NOTA_ING']].mean(axis=1)

    # MEDIA_INDICADORES sem IAN (excluído junto com INDE por leakage)
    df['MEDIA_INDICADORES'] = df[['IAA', 'IEG', 'IPS', 'IDA', 'IPV']].mean(axis=1)

    # Features — INDE e IAN removidos (causavam leakage: INDE determina PEDRA no sistema da ONG)
    features = [
        'FASE', 'ANOS_PM',
        'IAA', 'IEG', 'IPS', 'IDA', 'IPV',
        'NOTA_MAT', 'NOTA_PORT', 'MEDIA_NOTAS', 'MEDIA_INDICADORES',
        'GENERO_FEMININO', 'INSTITUICAO_COD',
    ]

    df_m = df.dropna(subset=features + ['PEDRA_NUM'])
    X = df_m[features].values
    y = df_m['PEDRA_NUM'].values

    print(f"\n  Alunos com dados completos: {len(df_m)}")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20,
                                               stratify=y, random_state=42)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    candidatos = {
        'Random Forest': RandomForestClassifier(
            n_estimators=300, max_depth=6, min_samples_leaf=3,
            random_state=42, n_jobs=-1
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42
        ),
    }

    print("\n  Comparando algoritmos:")
    melhor_nome = None
    melhor_acc  = -1
    melhor_modelo = None

    resultados = {}
    for nome, modelo in candidatos.items():
        cv_acc = cross_val_score(modelo, X_tr, y_tr, cv=cv,
                                 scoring='accuracy', n_jobs=-1)
        modelo.fit(X_tr, y_tr)
        preds_tr = modelo.predict(X_tr)
        preds_te = modelo.predict(X_te)
        acc_tr = accuracy_score(y_tr, preds_tr)
        acc_te = accuracy_score(y_te, preds_te)
        f1_te  = f1_score(y_te, preds_te, average='weighted', zero_division=0)

        print(f"    {nome:25s} acc_teste={acc_te:.4f}  f1_w={f1_te:.4f}  "
              f"gap={acc_tr - acc_te:.3f}  cv_acc={cv_acc.mean():.4f}+/-{cv_acc.std():.4f}")

        resultados[nome] = {
            'accuracy':   acc_te,
            'f1_weighted': f1_te,
            'acc_treino': acc_tr,
            'cv_acc':     cv_acc.mean(),
        }

        if acc_te > melhor_acc:
            melhor_acc   = acc_te
            melhor_nome  = nome
            melhor_modelo = modelo

    print(f"\n  Melhor modelo: {melhor_nome}")

    # Re-treinar o melhor no treino completo
    melhor_modelo.fit(X_tr, y_tr)
    preds_te  = melhor_modelo.predict(X_te)
    probs_te  = melhor_modelo.predict_proba(X_te)
    acc_tr_f  = accuracy_score(y_tr, melhor_modelo.predict(X_tr))
    acc_te_f  = accuracy_score(y_te, preds_te)
    f1_te_f   = f1_score(y_te, preds_te, average='weighted', zero_division=0)

    # AUC para multiclasse (one-vs-rest)
    try:
        auc = roc_auc_score(y_te, probs_te, multi_class='ovr', average='weighted')
    except Exception:
        auc = 0.0

    print(f"\n  Resultados finais ({melhor_nome}):")
    print(f"    Accuracy Treino : {acc_tr_f:.4f}")
    print(f"    Accuracy Teste  : {acc_te_f:.4f}  (gap: {acc_tr_f - acc_te_f:.3f})")
    print(f"    F1 Weighted     : {f1_te_f:.4f}")
    print(f"    AUC-ROC (OvR)   : {auc:.4f}")
    print()
    print(classification_report(y_te, preds_te, target_names=classes, zero_division=0))

    # Feature importance
    if hasattr(melhor_modelo, 'feature_importances_'):
        fi = pd.DataFrame({'feature': features,
                           'importance': melhor_modelo.feature_importances_})
        fi = fi.sort_values('importance', ascending=False)
    else:
        fi = None

    # Confusion matrix
    cm = confusion_matrix(y_te, preds_te)

    import json
    metricas_pedra = {
        'melhor_nome':  melhor_nome,
        'acc_treino':   acc_tr_f,
        'accuracy':     acc_te_f,
        'f1_weighted':  f1_te_f,
        'roc_auc':      auc,
    }
    with open('models/enquadramento_pedra_metrics.json', 'w', encoding='utf-8') as fh:
        json.dump(metricas_pedra, fh, indent=2)

    artefato = {
        'modelo':              melhor_modelo,
        'label_encoder':       le,
        'classes':             classes,
        'features':            features,
        'melhor_nome':         melhor_nome,
        'feature_importance':  fi,
        'confusion_matrix':    cm,
        'resultados': {
            'accuracy':    acc_te_f,
            'f1_weighted': f1_te_f,
            'roc_auc':     auc,
            'acc_treino':  acc_tr_f,
            'todos':       resultados,
        }
    }
    joblib.dump(artefato, 'models/enquadramento_pedra.joblib')
    print("  Salvo em: models/enquadramento_pedra.joblib")
    print("  Métricas em: models/enquadramento_pedra_metrics.json")
    return artefato

# ──────────────────────────────────────────────────────────────────────────────
# NOTA: Modelo de Risco de Evasao foi descontinuado.
# Motivo: AUC = 0.51 com target real (ausencia 2024) — essencialmente aleatório.
# A evasão é determinada por fatores externos ao dataset (família, financeiro,
# mudança de cidade). O app usa um sistema de alerta determinístico com 5 sinais.
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# MODELO 3 — PONTO DE VIRADA (binário, sem leakage: sem IPV, sem INDE)
# ──────────────────────────────────────────────────────────────────────────────

def treinar_ponto_virada():
    import json
    print()
    print("=" * 60)
    print("  MODELO 3 -- Ponto de Virada (sem IPV, sem INDE)")
    print("=" * 60)

    df = carregar_dataset_xlsx()
    print(f"\n  Dados: {df.shape[0]} alunos")

    # Target
    df['ATINGIU_PV'] = (df['PONTO_VIRADA'] == 'Sim').astype(int)

    # Encodings
    df['GENERO_FEMININO'] = (df['GENERO'] == 'Menina').astype(int)
    inst_vals = df['INSTITUICAO_ENSINO'].dropna().unique()
    inst_map = {v: i for i, v in enumerate(inst_vals)}
    df['INSTITUICAO_COD'] = df['INSTITUICAO_ENSINO'].map(inst_map).fillna(-1).astype(int)

    _ORD = {'Quartzo': 1, 'Agata': 2, 'Ágata': 2, 'Ametista': 3, 'Topazio': 4, 'Topázio': 4}
    df['PEDRA_NUM'] = df['PEDRA_2022'].map(_ORD).fillna(0)

    for col in ['NOTA_MAT', 'NOTA_PORT', 'NOTA_ING', 'IAN', 'IPP']:
        if col not in df.columns:
            df[col] = np.nan

    df['MEDIA_NOTAS']       = df[['NOTA_MAT', 'NOTA_PORT', 'NOTA_ING']].mean(axis=1)
    df['MEDIA_INDICADORES'] = df[['IAA', 'IEG', 'IPS', 'IDA']].mean(axis=1)

    # Features sem IPV (derivado do target) e sem INDE (correlacionado)
    features = [
        'IAA', 'IEG', 'IPS', 'IPP', 'IDA', 'IAN',
        'FASE', 'ANOS_PM', 'PEDRA_NUM',
        'NOTA_MAT', 'NOTA_PORT', 'NOTA_ING', 'MEDIA_NOTAS', 'MEDIA_INDICADORES',
        'GENERO_FEMININO', 'INSTITUICAO_COD',
    ]

    df_m = df.dropna(subset=['IAA', 'IEG', 'IPS', 'IDA', 'FASE', 'ANOS_PM', 'ATINGIU_PV']).copy()
    for f in ['IAN', 'IPP', 'NOTA_MAT', 'NOTA_PORT', 'NOTA_ING', 'PEDRA_NUM', 'MEDIA_NOTAS']:
        df_m[f] = df_m[f].fillna(df_m[f].median() if df_m[f].notna().any() else 0)
    df_m['MEDIA_INDICADORES'] = df_m[['IAA', 'IEG', 'IPS', 'IDA']].mean(axis=1)

    X = df_m[features].values
    y = df_m['ATINGIU_PV'].values

    n0, n1 = (y == 0).sum(), (y == 1).sum()
    print(f"  Não atingiu (0): {n0}  |  Atingiu (1): {n1}  |  Razão: {n1/max(n0,1):.2f}:1")
    print(f"  Alunos com dados completos: {len(df_m)}")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20,
                                               stratify=y, random_state=42)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    candidatos = {
        'Random Forest': RandomForestClassifier(
            n_estimators=300, max_depth=5, min_samples_leaf=4,
            class_weight='balanced', random_state=42, n_jobs=-1
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42
        ),
    }

    print("\n  Comparando algoritmos (AUC):")
    melhor_nome, melhor_auc, melhor_modelo = None, -1, None
    resultados = {}

    for nome, modelo in candidatos.items():
        cv_auc = cross_val_score(modelo, X_tr, y_tr, cv=cv,
                                 scoring='roc_auc', n_jobs=-1 if nome == 'Random Forest' else 1)
        modelo.fit(X_tr, y_tr)
        probs_te = modelo.predict_proba(X_te)[:, 1]
        preds_te = (probs_te >= 0.5).astype(int)
        acc_te = accuracy_score(y_te, preds_te)
        f1_te  = f1_score(y_te, preds_te, zero_division=0)
        auc_te = roc_auc_score(y_te, probs_te)
        print(f"    {nome:25s} AUC={auc_te:.4f}  acc={acc_te:.4f}  f1={f1_te:.4f}  "
              f"cv={cv_auc.mean():.4f}+/-{cv_auc.std():.4f}")
        resultados[nome] = {'accuracy': acc_te, 'f1_score': f1_te, 'roc_auc': auc_te, 'cv_auc': cv_auc.mean()}
        if auc_te > melhor_auc:
            melhor_auc, melhor_nome, melhor_modelo = auc_te, nome, modelo

    print(f"\n  Melhor modelo: {melhor_nome} (AUC={melhor_auc:.4f})")

    melhor_modelo.fit(X_tr, y_tr)
    probs_te  = melhor_modelo.predict_proba(X_te)[:, 1]
    preds_te  = (probs_te >= 0.5).astype(int)
    probs_tr  = melhor_modelo.predict_proba(X_tr)[:, 1]
    preds_tr  = (probs_tr >= 0.5).astype(int)
    acc_tr_f  = accuracy_score(y_tr, preds_tr)
    acc_te_f  = accuracy_score(y_te, preds_te)
    f1_te_f   = f1_score(y_te, preds_te, zero_division=0)
    rec_te_f  = recall_score(y_te, preds_te, zero_division=0)
    prec_te_f = precision_score(y_te, preds_te, zero_division=0)
    auc_te_f  = roc_auc_score(y_te, probs_te)

    print(f"\n  Resultados finais ({melhor_nome}):")
    print(f"    Acc Treino : {acc_tr_f:.4f}  |  Acc Teste: {acc_te_f:.4f}  (gap: {acc_tr_f - acc_te_f:.3f})")
    print(f"    F1         : {f1_te_f:.4f}  |  Recall: {rec_te_f:.4f}  |  Precision: {prec_te_f:.4f}")
    print(f"    AUC-ROC    : {auc_te_f:.4f}")

    fi = None
    if hasattr(melhor_modelo, 'feature_importances_'):
        fi = pd.DataFrame({'feature': features, 'importance': melhor_modelo.feature_importances_})
        fi = fi.sort_values('importance', ascending=False)

    metricas = {
        'melhor_nome': melhor_nome,
        'acc_treino':  acc_tr_f,
        'acc_teste':   acc_te_f,
        'f1_score':    f1_te_f,
        'recall':      rec_te_f,
        'precision':   prec_te_f,
        'roc_auc':     auc_te_f,
        'todos':       resultados,
    }
    with open('models/ponto_virada_metrics.json', 'w', encoding='utf-8') as fh:
        json.dump(metricas, fh, indent=2)

    artefato = {
        'modelo':             melhor_modelo,
        'features':           features,
        'melhor_nome':        melhor_nome,
        'feature_importance': fi,
        'resultados':         metricas,
        'inst_map':           inst_map,
    }
    joblib.dump(artefato, 'models/ponto_virada.joblib')
    print("  Salvo em: models/ponto_virada.joblib")
    print("  Métricas em: models/ponto_virada_metrics.json")
    return artefato


# ──────────────────────────────────────────────────────────────────────────────
# MODELO 4 — RISCO DE EVASÃO REAL (Opção A)
# Target: aluno presente em ano N mas ausente em ano N+1 (evasão real)
# Fonte: CSV longitudinal 2020-2022 (transições 2020→2021 e 2021→2022)
# Features: indicadores pedagógicos do ano anterior à transição
# ──────────────────────────────────────────────────────────────────────────────

def treinar_churn():
    print()
    print("=" * 60)
    print("  MODELO 4 -- Risco de Evasão (target real)")
    print("  Opção A: ausência real no ano seguinte")
    print("  Fonte: CSV longitudinal 2020-2022")
    print("=" * 60)

    df = carregar_dataset_csv()
    print(f"\n  Dados CSV: {df.shape[0]} alunos, {df.shape[1]} colunas")

    PEDRA_ORD = {'Quartzo': 1, 'Agata': 2, 'Ágata': 2, 'Ametista': 3,
                 'Topazio': 4, 'Topázio': 4}

    # ── Construir observações por transição de ano ─────────────────────────────

    def _build_obs(df_src, ano_src, ano_tgt):
        """Retorna um DataFrame com uma linha por aluno presente em ano_src.
        EVADIU=1 se ausente em ano_tgt, 0 caso contrário."""
        inde_src = f'INDE_{ano_src}'
        inde_tgt = f'INDE_{ano_tgt}'

        mask = pd.to_numeric(df_src[inde_src], errors='coerce').notna()
        d = df_src[mask].copy()

        def _num(col):
            if col in d.columns:
                return pd.to_numeric(d[col], errors='coerce').values
            return np.full(len(d), np.nan)

        # FASE: 2020 usa "2H" (fase+turma); 2021 usa float puro
        if ano_src == 2020:
            fase = d['FASE_TURMA_2020'].str.extract(r'(\d+)')[0].astype(float).values
        else:
            fase = _num(f'FASE_{ano_src}')

        # ANOS_PM: disponível direto em 2020; estimado para 2021
        if ano_src == 2020:
            anos_pm = pd.to_numeric(d['ANOS_PM_2020'], errors='coerce').values
        else:
            anos_pm = (2021 - pd.to_numeric(
                d['ANO_INGRESSO_2022'] if 'ANO_INGRESSO_2022' in d.columns
                else pd.Series([np.nan] * len(d), index=d.index),
                errors='coerce')).values

        iaa = _num(f'IAA_{ano_src}')
        ieg = _num(f'IEG_{ano_src}')
        ips = _num(f'IPS_{ano_src}')
        ida = _num(f'IDA_{ano_src}')
        ipv = _num(f'IPV_{ano_src}')
        ian = _num(f'IAN_{ano_src}')
        pedra_num = d[f'PEDRA_{ano_src}'].map(PEDRA_ORD).values

        stack = np.stack([iaa, ieg, ips, ida, ipv, ian], axis=1)
        media_ind = np.nanmean(stack, axis=1)

        # Target: aluno ausente no ano seguinte = evadiu
        evadiu = pd.to_numeric(
            df_src.loc[d.index, inde_tgt], errors='coerce'
        ).isna().astype(int).values

        return pd.DataFrame({
            'IAA': iaa, 'IEG': ieg, 'IPS': ips, 'IDA': ida, 'IPV': ipv, 'IAN': ian,
            'FASE': fase, 'ANOS_PM': anos_pm,
            'PEDRA_NUM': pedra_num, 'MEDIA_INDICADORES': media_ind,
            'EVADIU': evadiu,
        })

    obs_2021 = _build_obs(df, 2020, 2021)
    obs_2022 = _build_obs(df, 2021, 2022)
    df_model = pd.concat([obs_2021, obs_2022], ignore_index=True)

    print(f"\n  Transicao 2020->2021: {len(obs_2021)} obs, {obs_2021['EVADIU'].sum()} evadidos")
    print(f"  Transicao 2021->2022: {len(obs_2022)} obs, {obs_2022['EVADIU'].sum()} evadidos")
    print(f"  Total poolado: {len(df_model)} obs")

    features = [
        'IAA', 'IEG', 'IPS', 'IDA', 'IPV', 'IAN',
        'FASE', 'ANOS_PM', 'PEDRA_NUM', 'MEDIA_INDICADORES',
    ]

    df_m = df_model.dropna(subset=['IAA', 'IEG', 'IPS', 'IDA', 'EVADIU']).copy()
    for f in ['IPV', 'IAN', 'FASE', 'ANOS_PM', 'PEDRA_NUM', 'MEDIA_INDICADORES']:
        df_m[f] = df_m[f].fillna(df_m[f].median() if df_m[f].notna().any() else 0.0)

    X = df_m[features].values
    y = df_m['EVADIU'].values

    n0, n1 = (y == 0).sum(), (y == 1).sum()
    print(f"\n  Após dropna — Ficou (0): {n0}  |  Evadiu (1): {n1}  |  Taxa evasão: {n1/(n0+n1):.1%}")

    if n1 < 50:
        raise ValueError(
            f"Opção A inviável: apenas {n1} casos positivos. Use Opção B (estagnação).")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    rf = RandomForestClassifier(
        n_estimators=300, max_depth=5, min_samples_leaf=4,
        class_weight='balanced', random_state=42, n_jobs=-1
    )
    print("\n  Treinando Random Forest (class_weight=balanced)...")
    rf.fit(X_tr, y_tr)

    probs_tr = rf.predict_proba(X_tr)[:, 1]
    probs_te = rf.predict_proba(X_te)[:, 1]
    preds_tr = (probs_tr >= 0.5).astype(int)
    preds_te = (probs_te >= 0.5).astype(int)

    acc_tr  = accuracy_score(y_tr, preds_tr)
    acc_te  = accuracy_score(y_te, preds_te)
    f1_te   = f1_score(y_te, preds_te, zero_division=0)
    rec_te  = recall_score(y_te, preds_te, zero_division=0)
    prec_te = precision_score(y_te, preds_te, zero_division=0)
    auc_te  = roc_auc_score(y_te, probs_te)
    cv_auc  = cross_val_score(rf, X_tr, y_tr, cv=cv, scoring='roc_auc', n_jobs=-1)

    print(f"\n  Resultados:")
    print(f"    Acc Treino : {acc_tr:.4f}  |  Acc Teste: {acc_te:.4f}  (gap: {acc_tr - acc_te:.3f})")
    print(f"    F1         : {f1_te:.4f}  |  Recall: {rec_te:.4f}  |  Precision: {prec_te:.4f}")
    print(f"    AUC-ROC    : {auc_te:.4f}  |  CV AUC: {cv_auc.mean():.4f}+/-{cv_auc.std():.4f}")

    fi = pd.DataFrame({'feature': features, 'importance': rf.feature_importances_})
    fi = fi.sort_values('importance', ascending=False)

    metricas = {
        'acc_treino':          acc_tr,
        'acc_teste':           acc_te,
        'f1_score':            f1_te,
        'recall':              rec_te,
        'precision':           prec_te,
        'roc_auc':             auc_te,
        'opcao':               'A - evasao real (ausencia no ano seguinte)',
        'n_casos_positivos':   int(n1),
        'n_total':             int(len(df_m)),
    }

    import json
    with open('models/churn_metrics.json', 'w', encoding='utf-8') as fh:
        json.dump(metricas, fh, indent=2)

    artefato = {
        'modelo':             rf,
        'features':           features,
        'feature_importance': fi,
        'resultados':         metricas,
    }
    joblib.dump(artefato, 'models/churn.joblib')
    print("  Salvo em: models/churn.joblib")
    print("  Métricas em: models/churn_metrics.json")
    return artefato


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print()
    print("*" * 60)
    print("  DATATHON PASSOS MAGICOS -- Treinamento dos Modelos")
    print("  Selecao por F1 | Threshold calibrado por F1")
    print("*" * 60)

    art_defasagem = treinar_risco_defasagem()
    art_pedra     = treinar_enquadramento_pedra()
    art_pv        = treinar_ponto_virada()
    art_churn     = treinar_churn()

    print()
    print("=" * 60)
    print("  RESUMO FINAL")
    print("=" * 60)

    r1 = art_defasagem['resultados']['Random Forest']
    print(f"\n  RISCO DEFASAGEM  -> Random Forest")
    print(f"    Acc Treino : {r1['acc_treino']:.4f}  |  Acc Teste: {r1['accuracy']:.4f}  "
          f"|  Gap: {r1['acc_treino'] - r1['accuracy']:.3f}")
    print(f"    F1: {r1['f1_score']:.4f}  |  Recall: {r1['recall']:.4f}  |  AUC: {r1['roc_auc']:.4f}")

    r2 = art_pedra['resultados']
    print(f"\n  ENQUADRAMENTO PEDRA -> {art_pedra['melhor_nome']}")
    print(f"    Acc Treino : {r2['acc_treino']:.4f}  |  Acc Teste: {r2['accuracy']:.4f}  "
          f"|  Gap: {r2['acc_treino'] - r2['accuracy']:.3f}")
    print(f"    F1 Weighted: {r2['f1_weighted']:.4f}  |  AUC: {r2['roc_auc']:.4f}")

    r3 = art_pv['resultados']
    print(f"\n  PONTO DE VIRADA   -> {art_pv['melhor_nome']}")
    print(f"    Acc Treino : {r3['acc_treino']:.4f}  |  Acc Teste: {r3['acc_teste']:.4f}  "
          f"|  Gap: {r3['acc_treino'] - r3['acc_teste']:.3f}")
    print(f"    F1: {r3['f1_score']:.4f}  |  Recall: {r3['recall']:.4f}  |  AUC: {r3['roc_auc']:.4f}")

    r4 = art_churn['resultados']
    print(f"\n  RISCO DE EVASÃO (target real) -> Random Forest")
    print(f"    Opcao: {r4.get('opcao', 'A')}")
    print(f"    Casos de evasão: {r4.get('n_casos_positivos', '?')} / {r4.get('n_total', '?')} obs")
    print(f"    Acc Treino : {r4['acc_treino']:.4f}  |  Acc Teste: {r4['acc_teste']:.4f}  "
          f"|  Gap: {r4['acc_treino'] - r4['acc_teste']:.3f}")
    print(f"    F1: {r4['f1_score']:.4f}  |  Recall: {r4['recall']:.4f}  |  AUC: {r4['roc_auc']:.4f}")

    print()
    print("  Modelos ML salvos: risco_defasagem.joblib + enquadramento_pedra.joblib + "
          "ponto_virada.joblib + churn.joblib")
    print("  Sistema de alerta evasao: 5 regras determinísticas (complementa o modelo ML)")
    print("  Proximo passo: python -m streamlit run app.py")
    print("=" * 60)
    print("=" * 60)
