import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gate In Analytics", layout="wide")
st.title("📦 Gate In / Total Vessel - Analytics")

uploaded = st.file_uploader("Glisse ton fichier Excel (.xlsx, .xlsb, .xlsm)", type=["xlsx","xlsb","xlsm"])

if not uploaded:
    st.info("Upload ton fichier pour commencer")
    st.stop()

@st.cache_data
def load_data(file):
    # On lit les 2 feuilles
    gate = pd.read_excel(file, sheet_name="Gate In", header=3) # header ligne 4
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4) # header ligne 5
    return gate, vessel

gate, vessel = load_data(uploaded)

# --- Nettoyage selon tes colonnes ---
# Gate In: C=2, U=20 (0-index)
# Total Vessel: F=5, P=15, Q=16
try:
    gate_cont = gate.iloc[:, 2].astype(str).str.strip().str.upper()
    gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')
    
    vessel_cont = vessel.iloc[:, 5].astype(str).str.strip().str.upper()
    
    # Comptage voyages
    gate['CONT'] = gate_cont
    gate['DATE'] = gate_date
    gate['VOYAGE_NUM'] = gate.groupby('CONT').cumcount() + 1
    
    vessel['CONT'] = vessel_cont
    vessel['VOYAGE_NUM'] = vessel.groupby('CONT').cumcount() + 1
    
    # Merge intelligent 2ème voyage
    merged = vessel.merge(gate[['CONT','VOYAGE_NUM','DATE']], on=['CONT','VOYAGE_NUM'], how='left')
    merged['STATUS'] = merged['DATE'].apply(lambda x: 'Transferred' if pd.notna(x) else 'Not Transferred')

    # KPIs
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Vessel", len(merged))
    c2.metric("Transferred", (merged['STATUS']=='Transferred').sum())
    c3.metric("Not Transferred", (merged['STATUS']=='Not Transferred').sum())
    c4.metric("2èmes Voyages", (merged['VOYAGE_NUM']>1).sum())
    
    st.divider()
    
    # Recherche
    st.subheader("🔍 Recherche conteneur")
    search = st.text_input("Tape un conteneur (ex: TEMU1007746)")
    if search:
        res = merged[merged['CONT']==search.strip().upper()]
        st.dataframe(res, use_container_width=True)
    else:
        st.dataframe(merged.head(200), use_container_width=True)
    
    # Graph
    st.subheader("📊 Volume Gate In par jour")
    daily = gate.dropna(subset=['DATE']).groupby(gate['DATE'].dt.date).size().reset_index(name='Volume')
    st.bar_chart(daily, x='DATE', y='Volume')
    
    # Download
    st.download_button("⬇️ Exporter analyse Excel", data=merged.to_csv(index=False).encode(), file_name="analyse_gate.csv")

except Exception as e:
    st.error(f"Erreur colonnes: {e}")
    st.write("Gate In colonnes:", gate.columns.tolist()[:10])
    st.write("Total Vessel colonnes:", vessel.columns.tolist()[:10])