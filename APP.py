import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Togo Terminal Dashboard", layout="wide", page_icon="🚢")

# ===== DESIGN CSS PRO =====
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 15px;
    color: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
.kpi-box {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border-left: 5px solid #667eea;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.stPlotlyChart { background: white; border-radius: 12px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🚢 TOGO TERMINAL - Gate Analytics")
st.markdown("### Dashboard Temps Réel | Lome Port")

uploaded = st.file_uploader("📁 Dépose ton TEMPLATE.xlsb ici", type=["xlsx","xlsb","xlsm"])

if not uploaded:
    st.markdown("""
    <div style='text-align:center; padding:50px; background:#f8f9ff; border-radius:15px; border: 2px dashed #667eea;'>
        <h3>👋 En attente de ton fichier</h3>
        <p>Glisse ton fichier Excel pour générer le dashboard design</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

# --- DATA ---
gate_clean = pd.DataFrame()
gate_clean['CONTENEUR'] = gate.iloc[:, 2].astype(str).str.strip().str.upper()
gate_clean['DATE_GATE'] = pd.to_datetime(gate.iloc[:, 20], errors='coerce')
gate_clean['VOYAGE_NUM'] = gate_clean.groupby('CONTENEUR').cumcount() + 1

vessel_clean = pd.DataFrame()
vessel_clean['CONTENEUR'] = vessel.iloc[:, 5].astype(str).str.strip().str.upper()
vessel_clean['VESSEL'] = vessel.iloc[:, 1].astype(str)
vessel_clean['LIGNE'] = vessel.iloc[:, 3].astype(str) if vessel.shape[1] > 3 else "N/A"
vessel_clean['TYPE'] = vessel.iloc[:, 8].astype(str) if vessel.shape[1] > 8 else "40HC"
vessel_clean['TERMINAL'] = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"
vessel_clean['DATE_ARRIVEE'] = pd.to_datetime(vessel.iloc[:, 0], errors='coerce')
vessel_clean['VOYAGE_NUM'] = vessel_clean.groupby('CONTENEUR').cumcount() + 1

merged = vessel_clean.merge(gate_clean[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'Reste')
merged['JOURS'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days

transferred = merged[merged['STATUS']=='Transféré']
restants = merged[merged['STATUS']=='Reste']
bloques = restants[restants['DATE_ARRIVEE'] < (pd.Timestamp.now() - pd.Timedelta(days=7))]

# ===== KPI CARDS DESIGN =====
c1,c2,c3,c4,c5 = st.columns(5)
with c1:
    st.markdown(f"<div class='kpi-box'><h4>✅ Transféré</h4><h2>{len(transferred):,}</h2><p style='color:green'>{(len(transferred)/len(merged)*100):.1f}%</p></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='kpi-box' style='border-left-color:#ff9800'><h4>⏳ Restants</h4><h2>{len(restants):,}</h2><p style='color:orange'>À transférer</p></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='kpi-box' style='border-left-color:#f44336'><h4>🚫 Bloqués</h4><h2>{len(bloques):,}</h2><p style='color:red'>> 7 jours</p></div>", unsafe_allow_html=True)
with c4:
    moy = transferred['JOURS'].mean() if not transferred.empty else 0
    st.markdown(f"<div class='kpi-box' style='border-left-color:#2196f3'><h4>⏱️ Moy. Transfert</h4><h2>{moy:.1f} j</h2><p>Temps moyen</p></div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='kpi-box' style='border-left-color:#9c27b0'><h4>📦 Total</h4><h2>{len(merged):,}</h2><p>Conteneurs</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ===== GRAPHIQUES DESIGN =====
row1_col1, row1_col2 = st.columns([2,1])

with row1_col1:
    st.markdown("#### 📅 Conteneurs Transférés par Jour / Ligne / Type")
    if not transferred.empty:
        transferred['JOUR'] = transferred['DATE_GATE'].dt.date
        daily = transferred.groupby(['JOUR','LIGNE']).size().reset_index(name='NB')
        fig = px.area(daily, x='JOUR', y='NB', color='LIGNE', 
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      title="")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350)
        st.plotly_chart(fig, use_container_width=True)

with row1_col2:
    st.markdown("#### 🚫 Répartition Bloqués par Ligne")
    if not restants.empty:
        bloq = restants.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False).head(8)
        fig2 = px.pie(bloq, values='NB', names='LIGNE', hole=0.6,
                      color_discrete_sequence=px.colors.sequential.RdBu)
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("#### 📊 Total Transféré par Mois et par Terminal")
    if not transferred.empty:
        transferred['MOIS'] = transferred['DATE_GATE'].dt.strftime('%Y-%m')
        monthly = transferred.groupby(['MOIS','TERMINAL']).size().reset_index(name='NB')
        fig3 = px.bar(monthly, x='MOIS', y='NB', color='TERMINAL', barmode='group',
                      color_discrete_sequence=['#667eea','#764ba2','#f093fb'])
        fig3.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig3, use_container_width=True)

with row2_col2:
    st.markdown("#### ⏱️ Moyenne Temps de Transfert (jours)")
    if not transferred.empty and transferred['JOURS'].notna().sum() > 0:
        fig4 = px.histogram(transferred, x='JOURS', nbins=25, 
                            color_discrete_sequence=['#667eea'],
                            title="")
        fig4.add_vline(x=transferred['JOURS'].mean(), line_dash="dash", line_color="red", annotation_text=f"Moy: {transferred['JOURS'].mean():.1f}j")
        fig4.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig4, use_container_width=True)

# ===== TABLEAU + EXPORT =====
st.divider()
st.markdown("#### 🔍 Détail & Recherche")
col_f1, col_f2, col_f3 = st.columns(3)
ligne_f = col_f1.selectbox("Ligne Maritime", ["Toutes"] + sorted(merged['LIGNE'].dropna().unique().tolist()[:20]))
type_f = col_f2.selectbox("Type Conteneur", ["Tous"] + sorted(merged['TYPE'].dropna().unique().tolist()[:20]))
search = col_f3.text_input("🔎 Conteneur")

df_show = merged.copy()
if ligne_f != "Toutes": df_show = df_show[df_show['LIGNE']==ligne_f]
if type_f != "Tous": df_show = df_show[df_show['TYPE']==type_f]
if search: df_show = df_show[df_show['CONTENEUR'].str.contains(search.upper())]

st.dataframe(df_show[['VESSEL','CONTENEUR','LIGNE','TYPE','TERMINAL','STATUS','DATE_GATE','JOURS']], use_container_width=True, height=350)
st.download_button("⬇️ Exporter en CSV", df_show.to_csv(index=False).encode(), "dashboard_togo_terminal.csv", use_container_width=True)
