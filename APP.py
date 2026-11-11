# ===== EXPORTS - VERSION QUI MARCHE SUR STREAMLIT CLOUD =====
st.divider()
st.subheader("⬇️ Exports")

# 1. CSV toujours visible
st.download_button(
    label="⬇️ 1. Export Analyse CSV (sûr)",
    data=merged.to_csv(index=False).encode('utf-8'),
    file_name="analyse_fusionnee.csv",
    mime="text/csv",
    use_container_width=True
)

# 2. Excel fusionné - avec try pour voir l'erreur
try:
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        gate_fusion.to_excel(writer, sheet_name='Gate In', index=False)
        vessel_fusion.to_excel(writer, sheet_name='Total Vessel', index=False)
    
    output.seek(0) # <--- c'était ça qui manquait
    
    st.download_button(
        label=f"⬇️ 2. Télécharger FUSIONNÉ Excel ({len(gate_fusion)+len(vessel_fusion)} lignes)",
        data=output.getvalue(),
        file_name="TEMPLATE_FUSIONNE.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
except Exception as e:
    st.error(f"Erreur Excel: {e}")
    st.warning("Ajoute `openpyxl` dans requirements.txt")
    st.code("openpyxl\npandas\nstreamlit\nplotly\npyxlsb", language="text")
