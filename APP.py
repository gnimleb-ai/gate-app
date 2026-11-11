import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Togo Terminal - Ultimate Dashboard", layout="wide", page_icon="🚢")

# ===== DESIGN ULTIMATE =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.kpi {
    background: white; border-radius: 16px; padding: 22px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border-left: 6px solid;
    transition: transform 0.2s;
}
.kpi:hover { transform: translateY(-3px); }
.kpi h3 { font-size: 14px; color: #6b7280; margin:0; font-weight:600; text-transform:uppercase; }
.kpi h1 { font-size: 32px; margin: 8px 0 0 0; font-weight:700; color: #111827; }
.kpi p { font-size: 13px; margin:4px 0 0 0; }
.card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='margin-bottom:0'>🚢 TOGO TERMINAL - PERFORMANCE DASHBOARD</h1><p style='color:#6b7280'>Gate In • Transfert • Bloqués • Terminal • Navire</p>", unsafe_allow_html=True)

uploaded = st.file_uploader("📁 Dépose ton TEMPLATE.xlsb", type=["xlsx","xlsb","xlsm"])

if not uploaded:
    st.info("En attente du fichier TEMPLATE...")
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

# --- PARSING ROBUSTE ---
gate_c = gate.iloc[:, 2].astype(str).str.strip().str.upper()
gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')
gate_iso = gate.iloc[:, 5].astype(str).str.strip().str.upper() if gate.shape[1] > 5 else "N/A"

v_cont = vessel.iloc[:, 5].astype(str).str.strip().str.upper()
v_vessel = vessel.iloc[:, 1].astype(str)
v_ligne = vessel.iloc[:, 3].astype(str) if vessel.shape[1] > 3 else vessel.iloc[:, 2].astype(str)
v_iso = vessel.iloc[:, 8].astype(str).str.strip().str.upper() if vessel.shape[1] > 8 else gate_iso
v_terminal = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"
v_arrivee = pd.to_datetime(vessel.iloc[:, 0], errors='coerce')

# DataFrames
df_gate = pd.DataFrame({'CONTENEUR': gate_c, 'DATE_GATE': gate_date, 'ISO_GATE': gate_iso})
df_gate['VOYAGE_NUM'] = df_gate.groupby('CONTENEUR').cumcount() + 1

df_vessel = pd.DataFrame({
    'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'LIGNE': v_ligne,
    'ISO': v_iso, 'TERMINAL': v_terminal, 'DATE_ARRIVEE': v_arrivee
})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1

merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'Reste')
merged['JOURS_TRANSFERT'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days
merged['JOURS_ATTENTE'] = (pd.Timestamp.now() - merged['DATE_ARRIVEE']).dt.days
merged['BLOQUE'] = (merged['STATUS']=='Reste') & (merged['JOURS_ATTENTE'] > 7)

trans = merged[merged['STATUS']=='Transféré']
rest = merged[merged['STATUS']=='Reste']
bloq = merged[merged['BLOQUE']==True]

# ===== 1. KPI TOP =====
k1,k2,k3,k4,k5 = st.columns(5)
with k1: st.markdown(f"<div class='kpi' style='border-color:#10b981'><h3>✅ Transférés</h3><h1>{len(trans):,}</h1><p style='color:#10b981'>{(len(trans)/len(merged)*100):.1f}% du total</p></div>", unsafe_allow_html=True)
with k2: st.markdown(f"<div class='kpi' style='border-color:#f59e0b'><h3>⏳ Restants</h3><h1>{len(rest):,}</h1><p style='color:#f59e0b'>À transférer</p></div>", unsafe_allow_html=True)
with k3: st.markdown(f"<div class='kpi' style='border-color:#ef4444'><h3>🚫 Bloqués >7j</h3><h1>{len(bloq):,}</h1><p style='color:#ef4444'>{(len(bloq)/len(rest)*100 if len(rest)>0 else 0):.1f}% des restants</p></div>", unsafe_allow_html=True)
with k4: 
    moy = trans['JOURS_TRANSFERT'].mean() if not trans.empty else 0
    st.markdown(f"<div class='kpi' style='border-color:#3b82f6'><h3>⏱️ Moy. Transfert</h3><h1>{moy:.1f} j</h1><p>Temps moyen arrivée → gate</p></div>", unsafe_allow_html=True)
with k5: st.markdown(f"<div class='kpi' style='border-color:#8b5cf6'><h3>📦 Total</h3><h1>{len(merged):,}</h1><p>{merged['LIGNE'].nunique()} lignes • {merged['VESSEL'].nunique()} navires</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ===== 2. CONTRIBUTION LIGNE + TRANSFERT PAR JOUR ISO =====
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 📅 Conteneurs transférés par jour / Ligne / ISO")
    if not trans.empty:
        trans['JOUR'] = trans['DATE_GATE'].dt.date
        daily = trans.groupby(['JOUR','LIGNE','ISO']).size().reset_index(name='NB')
        fig = px.bar(daily, x='JOUR', y='NB', color='LIGNE', facet_col='ISO', 
                     color_discrete_sequence=px.colors.qualitative.Bold,
                     category_orders={"ISO": sorted(daily['ISO'].unique())})
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 🥧 Contribution de chaque Ligne Maritime")
    contrib = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
    fig_pie = px.pie(contrib, values='NB', names='LIGNE', hole=0.55, 
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(height=400, showlegend=True)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ===== 3. MENSUEL + PERFORMANCE TERMINAL =====
c3, c4 = st.columns(2)
with c3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 📊 Total Transféré par Mois et par Terminal")
    if not trans.empty:
        trans['MOIS'] = trans['DATE_GATE'].dt.to_period('M').astype(str)
        monthly = trans.groupby(['MOIS','TERMINAL']).size().reset_index(name='NB')
        fig_m = px.bar(monthly, x='MOIS', y='NB', color='TERMINAL', barmode='group',
                       color_discrete_sequence=['#6366f1','#06b6d4','#f59e0b'])
        fig_m.update_layout(height=380, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_m, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### ⚡ Performance en jours de chaque Terminal")
    if not trans.empty and trans['JOURS_TRANSFERT'].notna().sum()>0:
        perf = trans.groupby('TERMINAL')['JOURS_TRANSFERT'].agg(['mean','median','count']).reset_index()
        fig_perf = px.bar(perf, x='TERMINAL', y='mean', color='TERMINAL',
                          text_auto='.1f',
                          color_discrete_sequence=px.colors.qualitative.Set3)
        fig_perf.update_layout(height=380, yaxis_title="Jours moyens", showlegend=False)
        st.plotly_chart(fig_perf, use_container_width=True)
        st.dataframe(perf.rename(columns={'mean':'Moyenne','median':'Médiane','count':'Volume'}), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ===== 4. RESUME CHAQUE NAVIRE =====
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("#### 🚢 Résumé de chaque Navire")
resume_navire = merged.groupby('VESSEL').agg(
    LIGNE=('LIGNE','first'),
    TERMINAL=('TERMINAL','first'),
    TOTAL=('CONTENEUR','count'),
    TRANSFERES=('STATUS', lambda x: (x=='Transféré').sum()),
    RESTANTS=('STATUS', lambda x: (x=='Reste').sum()),
    BLOQUES=('BLOQUE','sum'),
    MOY_JOURS=('JOURS_TRANSFERT','mean')
).reset_index().sort_values('TOTAL', ascending=False)

resume_navire['TAUX'] = (resume_navire['TRANSFERES']/resume_navire['TOTAL']*100).round(1)
resume_navire['MOY_JOURS'] = resume_navire['MOY_JOURS'].round(1)

fig_nav = px.bar(resume_navire.head(20), x='VESSEL', y=['TRANSFERES','RESTANTS'], 
                 title="Top 20 Navires - Transférés vs Restants",
                 color_discrete_sequence=['#10b981','#f59e0b'])
fig_nav.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_nav, use_container_width=True)
st.dataframe(resume_navire, use_container_width=True, height=400)
st.markdown("</div>", unsafe_allow_html=True)

# ===== EXPORT =====
st.download_button("⬇️ Exporter tout le Dashboard (CSV)", merged.to_csv(index=False).encode(), "ultimate_dashboard.csv", use_container_width=True)
