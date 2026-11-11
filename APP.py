import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gate In Analytics Pro", layout="wide")
st.title("📦 Gate In / Total Vessel - Pro")

uploaded = st.file_uploader("Glisse ton fichier TEMPLATE (.xlsx, .xlsb)", type=["xlsx","xlsb","xlsm"])

if not uploaded:
    st.info("Upload ton TEMPLATE.xlsb")
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

# Mapping propre
gate_cont = gate.iloc[:, 2].astype(str).str.strip().str.upper()
gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')
vessel_cont = vessel.iloc[:, 5].astype(str).str.strip().str.upper()
vessel_vessel = vessel.iloc[:, 1].astype(str)

gate['CONTENEUR'] = gate_cont
gate['DATE_GATE'] = gate_date
gate['VOYAGE_NUM'] = gate.groupby('CONTENEUR').cumcount() + 1

vessel['CONTENEUR'] = vessel_cont
vessel['VESSEL'] = vessel_vessel
vessel['VOYAGE_NUM'] = vessel.groupby('CONTENEUR').cumcount() + 1

merged = vessel.merge(gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transferred' if pd.notna(x) else 'Not Transferred')

# KPIs
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Vessel", len(merged))
c2.metric("Transferred", (merged['STATUS']=='Transferred').sum())
c3.metric("Not Transferred", (merged['STATUS']=='Not Transferred').sum())
c4.metric("2èmes Voyages", (merged['VOYAGE_NUM']>1).sum())

st.divider()

# Filtres
colA, colB = st.columns(2)
with colA:
    vessel_filter = st.selectbox("Filtrer par Vessel", ["Tous"] + sorted(merged['VESSEL'].dropna().unique().tolist()[:50]))
with colB:
    status_filter = st.selectbox("Filtrer par Status", ["Tous","Transferred","Not Transferred"])

filtered = merged.copy()
if vessel_filter != "Tous":
    filtered = filtered[filtered['VESSEL']==vessel_filter]
if status_filter != "Tous":
    filtered = filtered[filtered['STATUS']==status_filter]

st.subheader(f"🔍 Résultats: {len(filtered)} conteneurs")
search = st.text_input("Recherche rapide conteneur")
if search:
    filtered = filtered[filtered['CONTENEUR'].str.contains(search.strip().upper(), na=False)]

# Affichage propre avec seulement les colonnes utiles
cols_show = ['VESSEL','CONTENEUR','VOYAGE_NUM','DATE_GATE','STATUS']
# Garde seulement celles qui existent
cols_show = [c for c in cols_show if c in filtered.columns]
st.dataframe(filtered[cols_show], use_container_width=True, height=400)

st.download_button("⬇️ Exporter CSV filtré", data=filtered[cols_show].to_csv(index=False).encode(), file_name="analyse_gate.csv")

st.subheader("📊 Not Transferred par Vessel")
nt = filtered[filtered['STATUS']=='Not Transferred']['VESSEL'].value_counts().head(20).reset_index()
nt.columns = ['VESSEL','Nb Not Transferred']
st.bar_chart(nt, x='VESSEL', y='Nb Not Transferred')
