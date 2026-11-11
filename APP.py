import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Togo Terminal - Dashboard", layout="wide")
st.title("📊 Togo Terminal - Gate In Dashboard")
st.caption("Analyse complète: Transfert / Bloqué / Moyenne")

uploaded = st.file_uploader("Glisse ton TEMPLATE.xlsb", type=["xlsx","xlsb","xlsm"])

if not uploaded:
    st.info("📁 Upload le fichier pour générer le dashboard")
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

# --- DETECTION INTELLIGENTE DES COLONNES ---
# On cherche les colonnes par nom, pas juste par position
def find_col(df, keywords):
    for col in df.columns:
        name = str(col).lower()
        for kw in keywords:
            if kw in name:
                return col
    return None

# Gate In
g_cont = gate.iloc[:, 2]
g_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')

# Total Vessel - on devine
v_cont = vessel.iloc[:, 5]
v_vessel = vessel.iloc[:, 1]
v_line = vessel.iloc[:, 3] if vessel.shape[1] > 3 else vessel.iloc[:, 2] # Ligne maritime MSC, etc
v_type = vessel.iloc[:, 8] if vessel.shape[1] > 8 else None # Type 20GP, 40HC etc - ajuste si besoin
v_terminal = vessel.iloc[:, 4] if vessel.shape[1] > 4 else None
v_date_arrival = None
# cherche une colonne date dans Total Vessel
for i in range(vessel.shape[1]):
    try:
        if pd.to_datetime(vessel.iloc[:, i], errors='coerce').notna().sum() > 100:
            v_date_arrival = pd.to_datetime(vessel.iloc[:, i], errors='coerce')
            break
    except:
        pass

# Préparation
gate_clean = pd.DataFrame()
gate_clean['CONTENEUR'] = g_cont.astype(str).str.strip().str.upper()
gate_clean['DATE_GATE'] = g_date
gate_clean['VOYAGE_NUM'] = gate_clean.groupby('CONTENEUR').cumcount() + 1

vessel_clean = pd.DataFrame()
vessel_clean['CONTENEUR'] = v_cont.astype(str).str.strip().str.upper()
vessel_clean['VESSEL'] = v_vessel.astype(str)
vessel_clean['LIGNE'] = v_line.astype(str) if v_line is not None else "N/A"
vessel_clean['TYPE'] = vessel.iloc[:, 8].astype(str) if vessel.shape[1] > 8 else "N/A"
vessel_clean['TERMINAL'] = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"
vessel_clean['DATE_ARRIVEE'] = v_date_arrival
vessel_clean['VOYAGE_NUM'] = vessel_clean.groupby('CONTENEUR').cumcount() + 1

merged = vessel_clean.merge(gate_clean[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'Reste à transférer')
merged['DATE_GATE'] = pd.to_datetime(merged['DATE_GATE'])
merged['JOURS_TRANSFERT'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days if merged['DATE_ARRIVEE'] is not None else None

# Définition Bloqué = Not Transferred depuis > 7 jours
today = pd.Timestamp.now()
merged['JOURS_ATTENTE'] = (today - merged['DATE_ARRIVEE']).dt.days if merged['DATE_ARRIVEE'] is not None else 0
merged['BLOQUE'] = (merged['STATUS'] == 'Reste à transférer') & (merged['JOURS_ATTENTE'] > 7)

# ===== KPI EN HAUT =====
transferred = merged[merged['STATUS']=='Transféré']
restants = merged[merged['STATUS']=='Reste à transférer']
bloques = merged[merged['BLOQUE']==True]

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("✅ Total Transféré", len(transferred))
k2.metric("⏳ Restants à transférer", len(restants))
k3.metric("🚫 Total Bloqué (>7j)", len(bloques), delta=f"{len(bloques)/len(restants)*100:.1f}% des restants" if len(restants)>0 else "")
k4.metric("⏱️ Moyenne temps transfert", f"{transferred['JOURS_TRANSFERT'].mean():.1f} j" if transferred['JOURS_TRANSFERT'].notna().sum()>0 else "N/A")
k5.metric("🔁 2èmes Voyages", (merged['VOYAGE_NUM']>1).sum())

st.divider()

# ===== GRAPHIQUES =====
col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Transférés par jour / Ligne / Type")
    if not transferred.empty:
        transferred['JOUR'] = transferred['DATE_GATE'].dt.date
        daily = transferred.groupby(['JOUR','LIGNE','TYPE']).size().reset_index(name='NB')
        fig = px.bar(daily, x='JOUR', y='NB', color='LIGNE', facet_col='TYPE', title="Transfert journalier")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Pas de données transférées")

with col2:
    st.subheader("📅 Total transféré par Mois et Terminal")
    if not transferred.empty:
        transferred['MOIS'] = transferred['DATE_GATE'].dt.to_period('M').astype(str)
        monthly = transferred.groupby(['MOIS','TERMINAL']).size().reset_index(name='NB')
        fig2 = px.bar(monthly, x='MOIS', y='NB', color='TERMINAL', barmode='group', title="Mensuel par Terminal")
        st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.subheader("🚫 Bloqués par Ligne")
    if not bloques.empty:
        bloq_line = bloques.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
        fig3 = px.pie(bloq_line, values='NB', names='LIGNE', hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("⏱️ Distribution temps de transfert")
    if transferred['JOURS_TRANSFERT'].notna().sum() > 0:
        fig4 = px.histogram(transferred, x='JOURS_TRANSFERT', nbins=20, title="Jours entre Arrivée et Gate In")
        st.plotly_chart(fig4, use_container_width=True)

# Table finale
st.divider()
st.subheader("📋 Détail - Filtre")
f1,f2,f3 = st.columns(3)
ligne_f = f1.selectbox("Ligne", ["Toutes"] + sorted(merged['LIGNE'].unique().tolist()))
status_f = f2.selectbox("Status", ["Tous","Transféré","Reste à transférer","Bloqué"])
search = f3.text_input("Conteneur")

df_show = merged.copy()
if ligne_f != "Toutes":
    df_show = df_show[df_show['LIGNE']==ligne_f]
if status_f == "Transféré":
    df_show = df_show[df_show['STATUS']=='Transféré']
elif status_f == "Reste à transférer":
    df_show = df_show[df_show['STATUS']=='Reste à transférer']
elif status_f == "Bloqué":
    df_show = df_show[df_show['BLOQUE']==True]
if search:
    df_show = df_show[df_show['CONTENEUR'].str.contains(search.upper())]

st.dataframe(df_show[['VESSEL','CONTENEUR','LIGNE','TYPE','TERMINAL','STATUS','DATE_GATE','JOURS_TRANSFERT']].head(500), use_container_width=True, height=400)
st.download_button("⬇️ Exporter Dashboard CSV", df_show.to_csv(index=False).encode(), "dashboard_gate.csv")
