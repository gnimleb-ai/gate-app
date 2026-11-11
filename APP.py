import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Togo Terminal - Ultimate", layout="wide", page_icon="🚢")

st.markdown("""
<style>
.kpi { background:white; border-radius:16px; padding:22px; box-shadow:0 4px 20px rgba(0,0,0,0.06); border-left:6px solid; }
.kpi h3 { font-size:13px; color:#6b7280; margin:0; text-transform:uppercase; }
.kpi h1 { font-size:30px; margin:8px 0 0 0; }
.card { background:white; border-radius:16px; padding:20px; box-shadow:0 4px 20px rgba(0,0,0,0.06); margin-bottom:20px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🚢 TOGO TERMINAL - PERFORMANCE DASHBOARD")

uploaded = st.file_uploader("📁 Dépose ton TEMPLATE.xlsb", type=["xlsx","xlsb","xlsm"])
if not uploaded:
    st.stop()

@st.cache_data
def load_data(file):
    gate = pd.read_excel(file, sheet_name="Gate In", header=3)
    vessel = pd.read_excel(file, sheet_name="Total Vessel", header=4)
    return gate, vessel

gate, vessel = load_data(uploaded)

# --- DEBUG: montre les vraies colonnes pour qu'on corrige une fois pour toutes ---
with st.expander("🔍 Voir les noms de colonnes détectés (clique ici)"):
    st.write("Gate In colonnes:", list(gate.columns))
    st.write("Total Vessel colonnes:", list(vessel.columns))
    st.write("Total Vessel aperçu ligne 0:", vessel.iloc[0].to_dict())

# --- DETECTION INTELLIGENTE ---
def find_date_col(df):
    best = None
    max_valid = 0
    for i, col in enumerate(df.columns):
        try:
            parsed = pd.to_datetime(df.iloc[:, i], errors='coerce')
            valid = parsed.notna().sum()
            if valid > max_valid and valid > 50:
                max_valid = valid
                best = parsed
        except:
            pass
    return best

# Gate
gate_cont = gate.iloc[:, 2].astype(str).str.strip().str.upper()
gate_date = pd.to_datetime(gate.iloc[:, 20], errors='coerce')

# Vessel - on cherche la date la plus remplie
v_date = find_date_col(vessel)
if v_date is None:
    v_date = pd.to_datetime(vessel.iloc[:, 0], errors='coerce')

v_cont = vessel.iloc[:, 5].astype(str).str.strip().str.upper()
v_vessel = vessel.iloc[:, 1].astype(str)
# Ligne maritime: cherche colonne avec MSC, CMA, MAERSK etc
v_ligne_col = 3
for i in range(vessel.shape[1]):
    sample = str(vessel.iloc[0, i]).upper()
    if any(x in sample for x in ['MSC','CMA','MAERSK','HAPAG','COSCO','EVERGREEN','ONE','YANG']):
        v_ligne_col = i
        break
v_ligne = vessel.iloc[:, v_ligne_col].astype(str)
v_iso = vessel.iloc[:, 8].astype(str) if vessel.shape[1] > 8 else vessel.iloc[:, 7].astype(str)
v_terminal = vessel.iloc[:, 4].astype(str) if vessel.shape[1] > 4 else "LCT"

df_gate = pd.DataFrame({'CONTENEUR': gate_cont, 'DATE_GATE': gate_date})
df_gate['VOYAGE_NUM'] = df_gate.groupby('CONTENEUR').cumcount() + 1

df_vessel = pd.DataFrame({
    'CONTENEUR': v_cont, 'VESSEL': v_vessel, 'LIGNE': v_ligne,
    'ISO': v_iso, 'TERMINAL': v_terminal, 'DATE_ARRIVEE': v_date
})
df_vessel['VOYAGE_NUM'] = df_vessel.groupby('CONTENEUR').cumcount() + 1

merged = df_vessel.merge(df_gate[['CONTENEUR','VOYAGE_NUM','DATE_GATE']], on=['CONTENEUR','VOYAGE_NUM'], how='left')
merged['STATUS'] = merged['DATE_GATE'].apply(lambda x: 'Transféré' if pd.notna(x) else 'Reste')
merged['JOURS_TRANSFERT'] = (merged['DATE_GATE'] - merged['DATE_ARRIVEE']).dt.days

# Fix bloqués: si pas de date arrivée, considère bloqué = reste depuis >30j = tout le reste
if merged['DATE_ARRIVEE'].isna().all():
    merged['BLOQUE'] = merged['STATUS']=='Reste'
else:
    merged['JOURS_ATTENTE'] = (pd.Timestamp.now() - merged['DATE_ARRIVEE']).dt.days
    merged['BLOQUE'] = (merged['STATUS']=='Reste') & (merged['JOURS_ATTENTE'] > 7)

trans = merged[merged['STATUS']=='Transféré']
rest = merged[merged['STATUS']=='Reste']
bloq = merged[merged['BLOQUE']==True]

# KPI
k1,k2,k3,k4,k5 = st.columns(5)
k1.markdown(f"<div class='kpi' style='border-color:#10b981'><h3>✅ Transférés</h3><h1>{len(trans):,}</h1><p>{len(trans)/len(merged)*100:.1f}% du total</p></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi' style='border-color:#f59e0b'><h3>⏳ Restants</h3><h1>{len(rest):,}</h1></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi' style='border-color:#ef4444'><h3>🚫 Bloqués</h3><h1>{len(bloq):,}</h1><p>{(len(bloq)/len(rest)*100 if len(rest)>0 else 0):.1f}% des restants</p></div>", unsafe_allow_html=True)
moy = trans['JOURS_TRANSFERT'].mean()
moy_txt = f"{moy:.1f} j" if pd.notna(moy) else f"{trans['DATE_GATE'].notna().sum()} transf."
k4.markdown(f"<div class='kpi' style='border-color:#3b82f6'><h3>⏱️ Moy. Transfert</h3><h1>{moy_txt}</h1><p>Arrivée → Gate</p></div>", unsafe_allow_html=True)
k5.markdown(f"<div class='kpi' style='border-color:#8b5cf6'><h3>📦 Total</h3><h1>{len(merged):,}</h1><p>{merged['LIGNE'].nunique()} lignes</p></div>", unsafe_allow_html=True)

st.markdown("<br>")

# Graphiques
c1,c2 = st.columns([2,1])
with c1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 📅 Transférés par Jour / Ligne / ISO")
    if not trans.empty:
        trans['JOUR'] = trans['DATE_GATE'].dt.date
        daily = trans.groupby(['JOUR','LIGNE','ISO']).size().reset_index(name='NB')
        fig = px.bar(daily, x='JOUR', y='NB', color='LIGNE', facet_col='ISO', color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 🥧 Contribution Ligne")
    contrib = merged.groupby('LIGNE').size().reset_index(name='NB').sort_values('NB', ascending=False)
    fig_pie = px.pie(contrib, values='NB', names='LIGNE', hole=0.55)
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

c3,c4 = st.columns(2)
with c3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### 📊 Transféré par Mois / Terminal")
    if not trans.empty:
        trans['MOIS'] = trans['DATE_GATE'].dt.to_period('M').astype(str)
        monthly = trans.groupby(['MOIS','TERMINAL']).size().reset_index(name='NB')
        fig_m = px.bar(monthly, x='MOIS', y='NB', color='TERMINAL', barmode='group')
        st.plotly_chart(fig_m, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("#### ⚡ Performance Terminal (jours moyens)")
    if not trans.empty:
        perf = trans.groupby('TERMINAL')['JOURS_TRANSFERT'].mean().reset_index()
        fig_perf = px.bar(perf, x='TERMINAL', y='JOURS_TRANSFERT', text_auto='.1f')
        st.plotly_chart(fig_perf, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Résumé navire
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("#### 🚢 Résumé par Navire")
resume = merged.groupby('VESSEL').agg(TOTAL=('CONTENEUR','count'), TRANSFERES=('STATUS', lambda x: (x=='Transféré').sum()), RESTANTS=('STATUS', lambda x: (x=='Reste').sum()), BLOQUES=('BLOQUE','sum'), MOY=('JOURS_TRANSFERT','mean')).reset_index()
resume['TAUX%'] = (resume['TRANSFERES']/resume['TOTAL']*100).round(1)
st.dataframe(resume.sort_values('TOTAL', ascending=False), use_container_width=True, height=400)
fig_nav = px.bar(resume.head(20), x='VESSEL', y=['TRANSFERES','RESTANTS'], barmode='stack')
st.plotly_chart(fig_nav, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)
