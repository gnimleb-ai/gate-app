import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Togo Terminal - Ops Max", layout="wide", page_icon="🚢")
st.title("🚢 TOGO TERMINAL - ANALYSE OPÉRATIONNELLE MAXIMALE")
st.caption("Exploitation complète Gate In + Total Vessel")

uploaded = st.file_uploader("📁 TEMPLATE.xlsb", type=["xlsx","xlsb","xlsm"])
if not uploaded:
    st.info("Upload ton fichier pour analyse complète")
    st.stop()

@st.cache_data
def load_all(file):
    xls = pd.ExcelFile(file)
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel, xls.sheet_names

gate, vessel, sheets = load_all(uploaded)
st.success(f"Feuilles détectées: {sheets} | Gate: {gate.shape} | Vessel: {vessel.shape}")

# ===== EXTRACTION MAXIMALE =====
# Gate In - toutes colonnes utiles
gate_cont = gate.iloc[:, 2].astype(str).str.upper().str.strip()
gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')
gate_iso = gate.iloc[:, 5].astype(str) if gate.shape[1] > 5 else "N/A"
gate_line = gate.iloc[:, 8].astype(str) if gate.shape[1] > 8 else "N/A"
gate_terminal = gate.iloc[:, 10].astype(str) if gate.shape[1] > 10 else "LCT"
gate_vessel = gate.iloc[:, 1].astype(str) if gate.shape[1] > 1 else "N/A"

# Total Vessel - toutes colonnes
v_cont = vessel.iloc[:, 5].astype(str).str.upper().str.strip()
v_vessel = vessel.iloc[:, 1].astype(str)
v_voyage = vessel.iloc[:, 2].astype(str) if vessel.shape[1] > 2 else "N/A"
v_ligne = vessel.iloc[:, 3].astype(str)
v_terminal = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"
v_iso = vessel.iloc[:, 7].astype(str) if vessel.shape[1] > 7 else vessel.iloc[:, 8].astype(str) if vessel.shape[1] > 8 else "N/A"
v_size = vessel.iloc[:, 6].astype(str) if vessel.shape[1] > 6 else "40"
v_status_v = vessel.iloc[:, 9].astype(str) if vessel.shape[1] > 9 else "N/A"
v_arr = pd.to_datetime(vessel.iloc[:, 0], errors='coerce')

# DataFrames enrichis
df_gate = pd.DataFrame({
    'CONTENEUR': gate_cont, 'DATE_GATE': gate_date, 'ISO_GATE': gate_iso,
    'LIGNE_GATE': gate_line, 'TERMINAL_GATE': gate_terminal, 'VESSEL_GATE': gate_vessel
})
df_gate['VOYAGE_NUM'] = df_gate.groupby('CONTENEUR').cumcount() + 1
df_gate = df_gate[df_gate['CONTENEUR'] != 'NAN']

df_vessel = pd.DataFrame({
    'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'VOYAGE': v_voyage,
    'LIGNE': v_ligne, 'TERMINAL': v_terminal, 'ISO': v_iso,
    'SIZE': v_size, 'DATE_ARRIVEE': v_arr
})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1
df_vessel = df_vessel[df_vessel['CONTENEUR'] != 'NAN']

# MERGE OPERATIONNEL
merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'En Stock')
merged['JOURS_TRANSFERT'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days
merged['JOURS_STOCK'] = (pd.Timestamp.now() - merged['DATE_ARRIVEE']).dt.days
merged['BLOQUE_7J'] = (merged['STATUS']=='En Stock') & (merged['JOURS_STOCK'] > 7)
merged['BLOQUE_14J'] = (merged['STATUS']=='En Stock') & (merged['JOURS_STOCK'] > 14)
merged['BLOQUE_30J'] = (merged['STATUS']=='En Stock') & (merged['JOURS_STOCK'] > 30)
merged['MOIS_ARR'] = merged['DATE_ARRIVEE'].dt.to_period('M').astype(str)
merged['MOIS_GATE'] = merged['DATE_GATE'].dt.to_period('M').astype(str)
merged['JOUR_GATE'] = merged['DATE_GATE'].dt.date
merged['SEMAINE_GATE'] = merged['DATE_GATE'].dt.isocalendar().week

trans = merged[merged['STATUS']=='Transféré'].copy()
stock = merged[merged['STATUS']=='En Stock'].copy()

# ===== KPI MAX =====
k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("📦 Total Arrivé", f"{len(merged):,}")
k2.metric("✅ Transféré", f"{len(trans):,}", f"{len(trans)/len(merged)*100:.1f}%")
k3.metric("⏳ En Stock", f"{len(stock):,}")
k4.metric("🚫 >7j", f"{merged['BLOQUE_7J'].sum():,}", delta_color="inverse")
k5.metric("🔴 >14j", f"{merged['BLOQUE_14J'].sum():,}", delta_color="inverse")
k6.metric("⏱️ Moy Transfert", f"{trans['JOURS_TRANSFERT'].mean():.1f} j" if trans['JOURS_TRANSFERT'].notna().sum()>0 else "N/A")

st.divider()

# ===== 1. CONTRIBUTION LIGNE + ISO + SIZE =====
colA, colB, colC = st.columns(3)
with colA:
    st.subheader("1️⃣ Contribution Ligne")
    c = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
    st.plotly_chart(px.pie(c, values='NB', names='LIGNE', hole=0.5, title="Par Ligne"), use_container_width=True)
    st.dataframe(c, use_container_width=True)

with colB:
    st.subheader("2️⃣ Contribution ISO")
    c_iso = merged.groupby('ISO').size().reset_index(name='NB').sort_values('NB', ascending=False)
    st.plotly_chart(px.pie(c_iso, values='NB', names='ISO', hole=0.5, title="Par ISO Type"), use_container_width=True)
    st.dataframe(c_iso, use_container_width=True)

with colC:
    st.subheader("3️⃣ Contribution Terminal")
    c_term = merged.groupby('TERMINAL').size().reset_index(name='NB')
    st.plotly_chart(px.bar(c_term, x='TERMINAL', y='NB', color='TERMINAL', title="Par Terminal"), use_container_width=True)
    st.dataframe(c_term, use_container_width=True)

# ===== 4. TRANSFERT PAR JOUR =====
st.divider()
st.subheader("4️⃣ Transferts par Jour / Ligne / ISO / Terminal")
if not trans.empty:
    r1, r2 = st.columns(2)
    with r1:
        daily = trans.groupby('JOUR_GATE').size().reset_index(name='NB')
        st.plotly_chart(px.line(daily, x='JOUR_GATE', y='NB', markers=True, title="Volume journalier total"), use_container_width=True)
    with r2:
        daily_line = trans.groupby(['JOUR_GATE','LIGNE']).size().reset_index(name='NB')
        st.plotly_chart(px.bar(daily_line, x='JOUR_GATE', y='NB', color='LIGNE', title="Journalier par Ligne"), use_container_width=True)
    
    r3, r4 = st.columns(2)
    with r3:
        daily_iso = trans.groupby(['JOUR_GATE','ISO']).size().reset_index(name='NB')
        st.plotly_chart(px.bar(daily_iso, x='JOUR_GATE', y='NB', color='ISO', title="Journalier par ISO"), use_container_width=True)
    with r4:
        daily_term = trans.groupby(['JOUR_GATE','TERMINAL']).size().reset_index(name='NB')
        st.plotly_chart(px.bar(daily_term, x='JOUR_GATE', y='NB', color='TERMINAL', title="Journalier par Terminal"), use_container_width=True)

# ===== 5. MENSUEL =====
st.divider()
st.subheader("5️⃣ Mensuel & Hebdo")
if not trans.empty:
    c1, c2 = st.columns(2)
    with c1:
        monthly = trans.groupby(['MOIS_GATE','TERMINAL']).size().reset_index(name='NB')
        st.plotly_chart(px.bar(monthly, x='MOIS_GATE', y='NB', color='TERMINAL', barmode='group', title="Mensuel par Terminal"), use_container_width=True)
    with c2:
        weekly = trans.groupby('SEMAINE_GATE').size().reset_index(name='NB')
        st.plotly_chart(px.bar(weekly, x='SEMAINE_GATE', y='NB', title="Hebdomadaire"), use_container_width=True)

# ===== 6. PERFORMANCE TERMINAL =====
st.divider()
st.subheader("6️⃣ Performance Terminal (jours de transfert)")
if not trans.empty and trans['JOURS_TRANSFERT'].notna().sum()>0:
    perf = trans.groupby('TERMINAL')['JOURS_TRANSFERT'].agg(['mean','median','min','max','count','std']).reset_index()
    perf.columns = ['TERMINAL','Moyenne','Médiane','Min','Max','Volume','Ecart-Type']
    st.dataframe(perf, use_container_width=True)
    st.plotly_chart(px.bar(perf, x='TERMINAL', y='Moyenne', color='TERMINAL', text_auto='.1f', title="Moyenne jours par Terminal"), use_container_width=True)
    st.plotly_chart(px.box(trans, x='TERMINAL', y='JOURS_TRANSFERT', color='TERMINAL', title="Distribution temps de transfert"), use_container_width=True)

# ===== 7. ANALYSE BLOQUES =====
st.divider()
st.subheader("7️⃣ Analyse Bloqués - Vieillissement Stock")
col_b1, col_b2 = st.columns(2)
with col_b1:
    aging = stock.groupby('LIGNE').agg(TOTAL=('CONTENEUR','count'), BLOQ7=('BLOQUE_7J','sum'), BLOQ14=('BLOQUE_14J','sum'), BLOQ30=('BLOQUE_30J','sum')).reset_index()
    st.dataframe(aging.sort_values('TOTAL', ascending=False), use_container_width=True)
    st.plotly_chart(px.bar(aging, x='LIGNE', y=['BLOQ7','BLOQ14','BLOQ30'], title="Bloqués par Ligne"), use_container_width=True)
with col_b2:
    if not stock.empty:
        hist_stock = stock['JOURS_STOCK'].dropna()
        st.plotly_chart(px.histogram(hist_stock, x=hist_stock, nbins=30, title="Distribution âge stock (jours)"), use_container_width=True)

# ===== 8. RESUME NAVIRE =====
st.divider()
st.subheader("8️⃣ Résumé par Navire - Performance Opérationnelle")
resume = merged.groupby(['VESSEL','LIGNE','TERMINAL']).agg(
    TOTAL=('CONTENEUR','count'),
    TRANSFERES=('STATUS', lambda x: (x=='Transféré').sum()),
    STOCK=('STATUS', lambda x: (x=='En Stock').sum()),
    BLOQ7=('BLOQUE_7J','sum'),
    MOY_JOURS=('JOURS_TRANSFERT','mean'),
    MED_JOURS=('JOURS_TRANSFERT','median'),
    MIN_JOURS=('JOURS_TRANSFERT','min'),
    MAX_JOURS=('JOURS_TRANSFERT','max')
).reset_index()
resume['TAUX_TRANSFERT%'] = (resume['TRANSFERES']/resume['TOTAL']*100).round(1)
resume = resume.sort_values('TOTAL', ascending=False)
st.dataframe(resume, use_container_width=True, height=400)
st.plotly_chart(px.bar(resume.head(20), x='VESSEL', y=['TRANSFERES','STOCK'], barmode='stack', color_discrete_sequence=['#10b981','#ef4444'], title="Top 20 Navires - Transfert vs Stock"), use_container_width=True)
st.plotly_chart(px.scatter(resume, x='TOTAL', y='MOY_JOURS', size='TOTAL', color='LIGNE', hover_name='VESSEL', title="Volume vs Performance par Navire"), use_container_width=True)

# ===== 9. DOUBLE VOYAGE & ANOMALIES =====
st.divider()
st.subheader("9️⃣ Doubles Voyages & Anomalies")
doubles = merged[merged['VOYAGE_NUM']>1]
st.metric("Conteneurs en 2ème voyage ou plus", f"{len(doubles):,}")
if not doubles.empty:
    st.dataframe(doubles[['VESSEL','CONTENEUR','VOYAGE_NUM','LIGNE','ISO','STATUS','JOURS_TRANSFERT']].head(100), use_container_width=True)

# ===== EXPORT FINAL =====
st.divider()
st.download_button("⬇️ Export COMPLET (toutes analyses)", merged.to_csv(index=False).encode(), "analyse_operationnelle_max.csv", use_container_width=True)
st.download_button("⬇️ Export Résumé Navires", resume.to_csv(index=False).encode(), "resume_navires.csv")
