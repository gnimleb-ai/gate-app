import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Togo Terminal - Fusion", layout="wide")
st.title("🚢 TOGO TERMINAL - Fusion de 2 fichiers")
st.caption("APP.py | Fusion sans écrasement + 2 voyages conservés")

st.markdown("""
**Principe de fusion :**
- On empile les 2 fichiers l'un après l'autre
- On NE supprime PAS les doublons de conteneurs
- Si un conteneur a fait 2 voyages, il garde `VOYAGE_NUM = 1 et 2`
- Tout est conservé dans `Total Vessel`
""")

file1 = st.file_uploader("📁 Fichier 1 (ancien)", type=["xlsx","xlsb","xlsm"], key="f1")
file2 = st.file_uploader("📁 Fichier 2 (suite / nouveau)", type=["xlsx","xlsb","xlsm"], key="f2")

if not file1 or not file2:
    st.info("Upload les 2 fichiers TEMPLATE pour fusionner")
    st.stop()

@st.cache_data
def load_both(f1, f2):
    gate1 = pd.read_excel(f1, sheet_name="Gate In", header=3)
    vessel1 = pd.read_excel(f1, sheet_name="Total Vessel", header=4)
    
    # On doit recharger le file_uploader
    f2.seek(0)
    gate2 = pd.read_excel(f2, sheet_name="Gate In", header=3)
    f2.seek(0)
    vessel2 = pd.read_excel(f2, sheet_name="Total Vessel", header=4)
    return gate1, vessel1, gate2, vessel2

gate1, vessel1, gate2, vessel2 = load_both(file1, file2)

st.success(f"Fichier 1: Gate {gate1.shape} | Vessel {vessel1.shape}")
st.success(f"Fichier 2: Gate {gate2.shape} | Vessel {vessel2.shape}")

# ===== FUSION SANS ECRASEMENT =====
# On empile tout simplement
gate_fusion = pd.concat([gate1, gate2], ignore_index=True)
vessel_fusion = pd.concat([vessel1, vessel2], ignore_index=True)

# On enlève les vraies lignes vides uniquement
gate_fusion = gate_fusion.dropna(subset=[gate_fusion.columns[2]], how='all') # Col C conteneur vide
vessel_fusion = vessel_fusion.dropna(subset=[vessel_fusion.columns[5]], how='all') # Col F conteneur vide

st.divider()
st.subheader(f"✅ Fusionnée: Gate {gate_fusion.shape} | Vessel {vessel_fusion.shape}")

# ===== TRAITEMENT CLASSIQUE APRES FUSION =====
gate_cont = gate_fusion.iloc[:, 2].astype(str).str.upper().str.strip()
gate_date = pd.to_datetime(gate_fusion.iloc[:, 20], errors='coerce')

v_cont = vessel_fusion.iloc[:, 5].astype(str).str.upper().str.strip()
v_vessel = vessel_fusion.iloc[:, 1].astype(str)
v_ligne = vessel_fusion.iloc[:, 3].astype(str)
v_terminal = vessel_fusion.iloc[:, 4].astype(str) if vessel_fusion.shape[1] > 4 else "LCT"
v_iso = vessel_fusion.iloc[:, 8].astype(str) if vessel_fusion.shape[1] > 8 else "STD"
v_arr = pd.to_datetime(vessel_fusion.iloc[:, 0], errors='coerce')

df_gate = pd.DataFrame({'CONTENEUR': gate_cont, 'DATE_GATE': gate_date})
df_gate['VOYAGE_NUM'] = df_gate.groupby('CONTENEUR').cumcount() + 1

df_vessel = pd.DataFrame({
    'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'LIGNE': v_ligne,
    'TERMINAL': v_terminal, 'ISO': v_iso, 'DATE_ARRIVEE': v_arr
})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1

# On garde les conteneurs qui ne sont pas 'NAN'
df_gate = df_gate[df_gate['CONTENEUR']!='NAN']
df_vessel = df_vessel[df_vessel['CONTENEUR']!='NAN']

merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'En Stock')

# Stats fusion
doubles = merged[merged['VOYAGE_NUM']>1]
st.info(f"📌 Conteneurs avec 2 voyages ou plus conservés: {len(doubles):,} | Exemple 2ème voyage: {doubles['CONTENEUR'].iloc[0] if not doubles.empty else 'Aucun'}")

# Dashboard rapide
trans = merged[merged['STATUS']=='Transféré']
stock = merged[merged['STATUS']=='En Stock']

k1,k2,k3 = st.columns(3)
k1.metric("Total après fusion", f"{len(merged):,}")
k2.metric("Transférés", f"{len(trans):,}")
k3.metric("En Stock", f"{len(stock):,}")

st.subheader("🥧 Contribution Ligne après fusion")
contrib = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
st.plotly_chart(px.pie(contrib, values='NB', names='LIGNE', hole=0.5), use_container_width=True)

st.subheader("🚢 Résumé Navire après fusion")
resume = merged.groupby('VESSEL').size().reset_index(name='TOTAL').sort_values('TOTAL', ascending=False)
st.dataframe(resume.head(20), use_container_width=True)

# EXPORTS
st.divider()
# Créer un fichier fusionné à télécharger
from io import BytesIO
output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    gate_fusion.to_excel(writer, sheet_name='Gate In', index=False)
    vessel_fusion.to_excel(writer, sheet_name='Total Vessel', index=False)
    
st.download_button("⬇️ Télécharger le fichier FUSIONNÉ (Excel)", output.getvalue(), "TEMPLATE_FUSIONNE.xlsx", use_container_width=True)
st.download_button("⬇️ Export Analyse CSV", merged.to_csv(index=False).encode(), "analyse_fusionnee.csv")
