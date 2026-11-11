import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Togo Terminal - Fusion", layout="wide")
st.title("🚢 TOGO TERMINAL - Fusion de 2 fichiers")
st.caption("APP.py | Fusion sans écrasement")

file1 = st.file_uploader("📁 Fichier 1 (ancien)", type=["xlsx","xlsb","xlsm"], key="f1")
file2 = st.file_uploader("📁 Fichier 2 (suite)", type=["xlsx","xlsb","xlsm"], key="f2")

if not file1 or not file2:
    st.info("Upload les 2 fichiers TEMPLATE pour fusionner")
    st.stop()

@st.cache_data
def load_both(f1, f2):
    g1 = pd.read_excel(f1, sheet_name="Gate In", header=3)
    v1 = pd.read_excel(f1, sheet_name="Total Vessel", header=4)
    f2.seek(0)
    g2 = pd.read_excel(f2, sheet_name="Gate In", header=3)
    f2.seek(0)
    v2 = pd.read_excel(f2, sheet_name="Total Vessel", header=4)
    return g1, v1, g2, v2

gate1, vessel1, gate2, vessel2 = load_both(file1, file2)

gate_fusion = pd.concat([gate1, gate2], ignore_index=True)
vessel_fusion = pd.concat([vessel1, vessel2], ignore_index=True)
gate_fusion = gate_fusion.dropna(subset=[gate_fusion.columns[2]])
vessel_fusion = vessel_fusion.dropna(subset=[vessel_fusion.columns[5]])

# Traitement
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
df_vessel = pd.DataFrame({'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'LIGNE': v_ligne, 'TERMINAL': v_terminal, 'ISO': v_iso, 'DATE_ARRIVEE': v_arr})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1

df_gate = df_gate[df_gate['CONTENEUR']!='NAN']
df_vessel = df_vessel[df_vessel['CONTENEUR']!='NAN']
merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'En Stock')

st.success(f"Fusion OK: Gate {len(gate_fusion)} | Vessel {len(vessel_fusion)} | Doubles: {(merged['VOYAGE_NUM']>1).sum()}")
k1,k2,k3 = st.columns(3)
k1.metric("Total", f"{len(merged):,}")
k2.metric("Transférés", f"{(merged['STATUS']=='Transféré').sum():,}")
k3.metric("En Stock", f"{(merged['STATUS']=='En Stock').sum():,}")

# Graph
st.subheader("🥧 Contribution Ligne")
contrib = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
st.plotly_chart(px.pie(contrib, values='NB', names='LIGNE', hole=0.5), use_container_width=True)

# EXPORTS
st.divider()
st.subheader("⬇️ Exports")

# Bouton 1 CSV - marche toujours
st.download_button(
    label="⬇️ 1. Export Analyse CSV",
    data=merged.to_csv(index=False).encode('utf-8'),
    file_name="analyse_fusionnee.csv",
    mime="text/csv",
    use_container_width=True
)

# Bouton 2 Excel
try:
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        gate_fusion.to_excel(writer, sheet_name='Gate In', index=False)
        vessel_fusion.to_excel(writer, sheet_name='Total Vessel', index=False)
    output.seek(0)
    st.download_button(
        label=f"⬇️ 2. Télécharger FUSIONNÉ Excel ({len(vessel_fusion)} conteneurs)",
        data=output.getvalue(),
        file_name="TEMPLATE_FUSIONNE.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
except Exception as e:
    st.error(f"Erreur Excel: {e}")
    st.info("Vérifie que requirements.txt contient: openpyxl")
