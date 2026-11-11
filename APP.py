import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Togo Terminal", layout="wide")
st.title("🚢 TOGO TERMINAL - PERFORMANCE DASHBOARD")

uploaded = st.file_uploader("Dépose TEMPLATE.xlsb", type=["xlsx","xlsb","xlsm"])
if not uploaded:
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

gate_cont = gate.iloc[:, 2].astype(str).str.upper().str.strip()
gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')
v_cont = vessel.iloc[:, 5].astype(str).str.upper().str.strip()
v_vessel = vessel.iloc[:, 1].astype(str)
v_ligne = vessel.iloc[:, 3].astype(str)
v_iso = vessel.iloc[:, 8].astype(str) if vessel.shape[1] > 8 else vessel.iloc[:, 7].astype(str)
v_terminal = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"
v_arr = pd.to_datetime(vessel.iloc[:, 0], errors='coerce')

df_gate = pd.DataFrame({'CONTENEUR': gate_cont, 'DATE_GATE': gate_date})
df_gate['VOYAGE_NUM'] = df_gate.groupby('CONTENEUR').cumcount() + 1
df_vessel = pd.DataFrame({'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'LIGNE': v_ligne, 'ISO': v_iso, 'TERMINAL': v_terminal, 'DATE_ARRIVEE': v_arr})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1

merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'Reste')
merged['JOURS'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days

trans = merged[merged['STATUS']=='Transféré'].copy()
rest = merged[merged['STATUS']=='Reste'].copy()

c1,c2,c3,c4 = st.columns(4)
c1.metric("✅ Transférés", f"{len(trans):,}")
c2.metric("⏳ Restants", f"{len(rest):,}")
c3.metric("🚫 Bloqués", f"{len(rest):,}")
c4.metric("⏱️ Moy", f"{trans['JOURS'].mean():.1f} j" if trans['JOURS'].notna().sum()>0 else "OK")

# 1 CONTRIBUTION
st.divider()
st.subheader("1️⃣ Contribution de chaque Ligne Maritime")
contrib = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
st.plotly_chart(px.pie(contrib, values='NB', names='LIGNE', hole=0.5), use_container_width=True)

# 2 PAR JOUR LIGNE ISO - SANS FACET
st.subheader("2️⃣ Transféré par jour / Ligne / ISO")
if not trans.empty:
    trans['JOUR'] = trans['DATE_GATE'].dt.date
    daily = trans.groupby('JOUR').size().reset_index(name='NB')
    st.plotly_chart(px.bar(daily, x='JOUR', y='NB', title="Par jour (total)"), use_container_width=True)
    daily_line = trans.groupby(['JOUR','LIGNE']).size().reset_index(name='NB')
    st.plotly_chart(px.bar(daily_line, x='JOUR', y='NB', color='LIGNE', title="Par jour par Ligne"), use_container_width=True)
    daily_iso = trans.groupby(['JOUR','ISO']).size().reset_index(name='NB')
    st.plotly_chart(px.bar(daily_iso, x='JOUR', y='NB', color='ISO', title="Par jour par ISO"), use_container_width=True)

# 3-4-5
st.subheader("3️⃣ Total par Mois et Terminal")
if not trans.empty:
    trans['MOIS'] = trans['DATE_GATE'].dt.to_period('M').astype(str)
    monthly = trans.groupby(['MOIS','TERMINAL']).size().reset_index(name='NB')
    st.plotly_chart(px.bar(monthly, x='MOIS', y='NB', color='TERMINAL', barmode='group'), use_container_width=True)

st.subheader("4️⃣ Performance Terminal (jours)")
perf = trans.groupby('TERMINAL')['JOURS'].mean().reset_index().dropna()
if not perf.empty:
    st.plotly_chart(px.bar(perf, x='TERMINAL', y='JOURS', text_auto='.1f'), use_container_width=True)

st.subheader("5️⃣ Résumé par Navire")
resume = merged.groupby('VESSEL').agg(TOTAL=('CONTENEUR','count'), TRANSFERES=('STATUS', lambda x: (x=='Transféré').sum()), RESTANTS=('STATUS', lambda x: (x=='Reste').sum())).reset_index().sort_values('TOTAL', ascending=False)
st.dataframe(resume.head(30), use_container_width=True)
st.plotly_chart(px.bar(resume.head(15), x='VESSEL', y=['TRANSFERES','RESTANTS'], barmode='stack'), use_container_width=True)

st.download_button("⬇️ Export CSV", merged.to_csv(index=False).encode(), "dashboard.csv")
