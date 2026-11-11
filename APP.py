import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Togo Terminal - Ops Max", layout="wide", page_icon="🚢")
st.title("🚢 TOGO TERMINAL - ANALYSE OPERATIONNELLE MAXIMALE")
st.caption("APP.py | Gate In + Total Vessel | Max Critères")

uploaded = st.file_uploader("📁 TEMPLATE.xlsb", type=["xlsx","xlsb","xlsm"])
if not uploaded:
    st.info("Upload ton fichier")
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

# ===== EXTRACTION =====
gate_cont = gate.iloc[:, 2].astype(str).str.upper().str.strip()
gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')

v_cont = vessel.iloc[:, 5].astype(str).str.upper().str.strip()
v_vessel = vessel.iloc[:, 1].astype(str)
v_ligne = vessel.iloc[:, 3].astype(str)
v_terminal = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"
v_iso = vessel.iloc[:, 8].astype(str) if vessel.shape[1] > 8 else vessel.iloc[:, 7].astype(str) if vessel.shape[1] > 7 else "STD"
v_arr = pd.to_datetime(vessel.iloc[:, 0], errors='coerce')

df_gate = pd.DataFrame({'CONTENEUR': gate_cont, 'DATE_GATE': gate_date})
df_gate['VOYAGE_NUM'] = df_gate.groupby('CONTENEUR').cumcount() + 1
df_gate = df_gate[df_gate['CONTENEUR']!='NAN']

df_vessel = pd.DataFrame({
    'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'LIGNE': v_ligne,
    'TERMINAL': v_terminal, 'ISO': v_iso, 'DATE_ARRIVEE': v_arr
})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1
df_vessel = df_vessel[df_vessel['CONTENEUR']!='NAN']

merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'En Stock')
merged['JOURS_TRANSFERT'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days
merged['JOURS_STOCK'] = (pd.Timestamp.now() - merged['DATE_ARRIVEE']).dt.days
merged['BLOQUE_7J'] = (merged['STATUS']=='En Stock') & (merged['JOURS_STOCK'] > 7)
merged['BLOQUE_14J'] = (merged['STATUS']=='En Stock') & (merged['JOURS_STOCK'] > 14)
merged['MOIS_GATE'] = merged['DATE_GATE'].dt.to_period('M').astype(str)
merged['JOUR_GATE'] = merged['DATE_GATE'].dt.date

trans = merged[merged['STATUS']=='Transféré'].copy()
stock = merged[merged['STATUS']=='En Stock'].copy()

# ===== KPI =====
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("📦 Total", f"{len(merged):,}")
k2.metric("✅ Transférés", f"{len(trans):,}", f"{len(trans)/len(merged)*100:.1f}%")
k3.metric("⏳ En Stock", f"{len(stock):,}")
k4.metric("🚫 Bloqué >7j", f"{merged['BLOQUE_7J'].sum():,}")
k5.metric("⏱️ Moy Transfert", f"{trans['JOURS_TRANSFERT'].mean():.1f} j" if trans['JOURS_TRANSFERT'].notna().sum()>0 else "N/A")

st.divider()

# 1 CONTRIBUTION LIGNE
st.subheader("1️⃣ Contribution de chaque Ligne Maritime")
contrib = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
st.plotly_chart(px.pie(contrib, values='NB', names='LIGNE', hole=0.5), use_container_width=True)
st.dataframe(contrib, use_container_width=True)

# 2 TRANSFERT PAR JOUR / LIGNE / ISO
st.subheader("2️⃣ Nombre transféré par jour par Ligne et ISO")
if not trans.empty:
    daily = trans.groupby('JOUR_GATE').size().reset_index(name='NB')
    st.plotly_chart(px.bar(daily, x='JOUR_GATE', y='NB', title="Total par jour"), use_container_width=True)
    
    daily_line = trans.groupby(['JOUR_GATE','LIGNE']).size().reset_index(name='NB')
    st.plotly_chart(px.bar(daily_line, x='JOUR_GATE', y='NB', color='LIGNE', title="Par jour par Ligne Maritime"), use_container_width=True)
    
    daily_iso = trans.groupby(['JOUR_GATE','ISO']).size().reset_index(name='NB')
    st.plotly_chart(px.bar(daily_iso, x='JOUR_GATE', y='NB', color='ISO', title="Par jour par ISO"), use_container_width=True)

# 3 RESTANTS
st.subheader("3️⃣ Nombre restants à transférer")
rest_par_ligne = stock.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
st.plotly_chart(px.bar(rest_par_ligne, x='LIGNE', y='NB', title="Restants par Ligne"), use_container_width=True)

# 4 BLOQUES
st.subheader("4️⃣ Nombre total bloqué")
bloq_par_ligne = merged[merged['BLOQUE_7J']].groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
if not bloq_par_ligne.empty:
    st.plotly_chart(px.bar(bloq_par_ligne, x='LIGNE', y='NB', color_discrete_sequence=['#ef4444'], title="Bloqués >7j par Ligne"), use_container_width=True)
else:
    st.info("Aucun bloqué >7j détecté (dates manquantes?) - on affiche tout le stock")
    st.plotly_chart(px.bar(rest_par_ligne, x='LIGNE', y='NB', title="Stock total par Ligne"), use_container_width=True)

# 5 MOYENNE
st.subheader("5️⃣ Moyenne du temps de transfert")
if trans['JOURS_TRANSFERT'].notna().sum()>0:
    st.plotly_chart(px.histogram(trans, x='JOURS_TRANSFERT', nbins=30, title="Distribution temps transfert"), use_container_width=True)
    perf_ligne = trans.groupby('LIGNE')['JOURS_TRANSFERT'].mean().reset_index().sort_values('JOURS_TRANSFERT')
    st.plotly_chart(px.bar(perf_ligne, x='LIGNE', y='JOURS_TRANSFERT', text_auto='.1f', title="Moyenne jours par Ligne"), use_container_width=True)

# 6 MENSUEL TERMINAL
st.subheader("6️⃣ Total transféré par mois et par Terminal")
if not trans.empty:
    monthly = trans.groupby(['MOIS_GATE','TERMINAL']).size().reset_index(name='NB')
    st.plotly_chart(px.bar(monthly, x='MOIS_GATE', y='NB', color='TERMINAL', barmode='group', title="Mensuel par Terminal"), use_container_width=True)

# 7 PERFORMANCE TERMINAL
st.subheader("7️⃣ Performance en jours de chaque Terminal")
if trans['JOURS_TRANSFERT'].notna().sum()>0:
    perf_term = trans.groupby('TERMINAL')['JOURS_TRANSFERT'].agg(['mean','median','count']).reset_index()
    st.dataframe(perf_term, use_container_width=True)
    st.plotly_chart(px.bar(perf_term, x='TERMINAL', y='mean', title="Jours moyens par Terminal"), use_container_width=True)
    st.plotly_chart(px.box(trans, x='TERMINAL', y='JOURS_TRANSFERT', title="Box Plot performance"), use_container_width=True)

# 8 RESUME NAVIRE
st.subheader("8️⃣ Résumé de chaque Navire")
resume = merged.groupby(['VESSEL','LIGNE','TERMINAL']).agg(
    TOTAL=('CONTENEUR','count'),
    TRANSFERES=('STATUS', lambda x: (x=='Transféré').sum()),
    STOCK=('STATUS', lambda x: (x=='En Stock').sum()),
    MOY_JOURS=('JOURS_TRANSFERT','mean')
).reset_index()
resume['TAUX%'] = (resume['TRANSFERES']/resume['TOTAL']*100).round(1)
resume = resume.sort_values('TOTAL', ascending=False)
st.dataframe(resume.head(50), use_container_width=True, height=400)
st.plotly_chart(px.bar(resume.head(15), x='VESSEL', y=['TRANSFERES','STOCK'], barmode='stack', title="Top 15 Navires"), use_container_width=True)
st.plotly_chart(px.scatter(resume, x='TOTAL', y='MOY_JOURS', color='LIGNE', size='TOTAL', hover_name='VESSEL', title="Volume vs Performance Navire"), use_container_width=True)

st.divider()
st.download_button("⬇️ Export Complet", merged.to_csv(index=False).encode(), "analyse_max_APP.csv", use_container_width=True)
