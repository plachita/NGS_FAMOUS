import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import seaborn as sns
import requests
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import base64
import plotly.express as px

# --------------------------
# Tabs
# --------------------------
with tabs[0]:
    st.title("Welcome to the NGS Reimbursement and Lab Optimization App")
    st.markdown("""
    This tool supports labs and stakeholders in evaluating:
    - 📊 Financial viability of NGS reimbursement strategies
    - ⚙️ Operational efficiency using streamlined workflows
    - 📁 Required documentation for CPT code and payer alignment

    Use the tabs above to navigate each section.
    """)
tabs = st.tabs(["🏠 Home", "Reimbursement Analysis", "Lab Workflow Optimization", "Documentation Checklist"])

with tabs[0]:
    # --------------------------
# Sidebar Inputs
# --------------------------
st.sidebar.markdown("### Optional Inputs")
zip_code = st.sidebar.text_input("Enter ZIP Code (for regional denial context):")
test_strategy = st.sidebar.radio("Test Strategy:", ["Panel Only", "Carve-out from WES", "Carve-out from WGS", "Carve-out from Large Panel"])

# --------------------------
# Step 1: Select Test Type
# --------------------------
st.markdown("## Step 1: Select Test Type")
test_type = st.selectbox("Choose a test type:", [
    "Solid Tumor – DNA", "Solid Tumor – RNA", "Solid Tumor – DNA + RNA",
    "Hematologic – DNA", "Hematologic – RNA", "Hematologic – DNA + RNA",
    "Liquid Biopsy", "Germline", "WES (Whole Exome)", "WGS (Whole Genome)"
])

# --------------------------
# Step 2: Select Panel Source
# --------------------------
st.markdown("## Step 2: Select Panel Source")
panel_source = st.radio("Select source:", ["SOPHiA Genetics", "General Category"])

# --------------------------
# Step 3: Select Specific Panel
# --------------------------
st.markdown("## Step 3: Select Specific Panel")
sophia_panels = {
    "Solid Tumor – DNA Panel (325 genes)": 325,
    "Solid Tumor – RNA Panel (50 genes)": 50,
    "Solid Tumor – DNA + RNA Panel (375 genes)": 375,
    "Hematologic – DNA Panel (65 genes)": 65,
    "Hematologic – RNA Panel (50 genes)": 50,
    "Hematologic – DNA + RNA Panel (115 genes)": 115,
    "Liquid Biopsy – ctDNA (500 genes)": 500,
    "Germline – Hereditary Cancer Panel (47 genes)": 47,
    "Germline – Cardiovascular/Metabolic Panel (60 genes)": 60,
    "Germline – Pediatric/Undiagnosed Disease Panel (160 genes)": 160,
    "WES – SOPHiA Exome Backbone (19000 genes)": 19000,
    "WGS – SOPHiA Genome Backbone (20000+ genes)": 20000,
    "General – Solid Tumor DNA Panel (<50 genes)": 45,
    "General – Solid Tumor RNA Panel (<50 genes)": 40,
    "General – Solid Tumor DNA+RNA Panel (<100 genes)": 90,
    "General – Heme DNA Panel (<50 genes)": 48,
    "General – Heme RNA Panel (<50 genes)": 45,
    "General – Heme DNA+RNA Panel (<100 genes)": 95,
    "General – Germline Panel (<50 genes)": 40,
    "General – Germline Panel (50-100 genes)": 75,
    "General – Germline Panel (>100 genes)": 150
}

if test_type in ["WES (Whole Exome)", "WGS (Whole Genome)"]:
    available_panels = [p for p in sophia_panels.keys() if test_type.split(" ")[0] in p]
elif panel_source == "SOPHiA Genetics":
    available_panels = [p for p in sophia_panels.keys() if test_type.split(" –")[0] in p and "General" not in p]
elif panel_source == "General Category":
    available_panels = [p for p in sophia_panels.keys() if test_type.split(" –")[0] in p and "General" in p]
else:
    available_panels = list(sophia_panels.keys())

selected_panels = st.multiselect("Available Panels:", available_panels)

# --------------------------
# Step 4: Risk Filter
# --------------------------
st.markdown("## Step 4: Risk Filter")
risk_notes = {
    "General – Germline Panel (50-100 genes)": {
        "risk_level": "Medium",
        "billing_note": "Consider billing with 81455. Denial risk may increase if policy requires <50 genes. Ensure strong documentation of medical necessity."
    },
    "General – Germline Panel (>100 genes)": {
        "risk_level": "High",
        "billing_note": "Most commercial payers do not cover panels >50 genes. Must use 81455. Recommend Z-code registration and MAC pre-check."
    },
    "Solid Tumor – DNA Panel (325 genes)": {
        "risk_level": "High",
        "billing_note": "Panels >300 genes typically require billing with 81455. Ensure strong rationale and clinical documentation to justify extent of profiling."
    },
    "Solid Tumor – DNA + RNA Panel (375 genes)": {
        "risk_level": "High",
        "billing_note": "High complexity assay – may not be reimbursed by all commercial payers. Use 81455 and document clearly why combined profiling was medically necessary."
    },
    "Liquid Biopsy – ctDNA (500 genes)": {
        "risk_level": "Very High",
        "billing_note": "Very few payers reimburse for ctDNA panels >300 genes. Consider alternatives or seek pre-authorization. Billing typically requires 81455."
    },
    "WES – SOPHiA Exome Backbone (19000 genes)": {
        "risk_level": "Very High",
        "billing_note": "Exome sequencing is rarely reimbursed as first-line test. Pairing with carved-out panels may help justify clinical utility and improve ROI."
    },
    "WGS – SOPHiA Genome Backbone (20000+ genes)": {
        "risk_level": "Very High",
        "billing_note": "Whole genome sequencing is high-cost and low reimbursement unless bundled with additional diagnostic or carved-out reportable panels."
    }
}

filter_risk = st.multiselect("Filter panels by risk level:", options=["Low", "Medium", "High", "Very High"])
filtered_panels = [p for p in available_panels if not filter_risk or risk_notes.get(p, {}).get("risk_level") in filter_risk]

# --------------------------
# Step 5-7: Display Analysis and ROI
# --------------------------
report_records = []
for selected_panel in selected_panels:
    if selected_panel not in filtered_panels:
        st.warning(f"{selected_panel} does not meet current risk filter.")

    st.markdown(f"### Analysis for {selected_panel}")
    panel_gene_count = sophia_panels[selected_panel]
    risk_level = risk_notes.get(selected_panel, {}).get("risk_level", "Not Specified")
    billing_note = risk_notes.get(selected_panel, {}).get("billing_note", "Standard documentation applies.")

    badge_color = {
        "Low": "✅", "Medium": "🟡", "High": "🔴", "Very High": "🚨"
    }.get(risk_level, "⚠️")
    st.markdown(f"#### {badge_color} Risk Level: {risk_level}")
    st.info(billing_note)

    cpt_mapping = {"<50": "81450", "50-100": "81455", ">100": "81455"}
    if panel_gene_count <= 50:
        suggested_cpt = cpt_mapping["<50"]
    elif 50 < panel_gene_count <= 100:
        suggested_cpt = cpt_mapping["50-100"]
    else:
        suggested_cpt = cpt_mapping[">100"]

    st.markdown(f"**CPT Code Recommendation: {suggested_cpt}**")
    st.markdown(f"**Billing Note:** {billing_note}")

    report_records.append({
        "Panel": selected_panel,
        "Genes": panel_gene_count,
        "Risk": risk_level,
        "CPT Code": suggested_cpt,
        "Billing Guidance": billing_note
    })

    if test_strategy.startswith("Carve-out"):
        st.markdown("### ROI Simulation for Carve-out")
        cost = st.number_input(f"{selected_panel} – Total Cost of Backbone Test ($):", min_value=500, max_value=3000, value=1200)
        reimbursement_per_panel = st.number_input(f"{selected_panel} – Avg Reimbursement per Carve-Out Panel ($):", min_value=100, max_value=2000, value=400)
        max_panels = st.slider(f"{selected_panel} – Number of Panel Reports:", min_value=1, max_value=10, value=5)

        break_even_panels = cost / reimbursement_per_panel
        actual_revenue = [n * reimbursement_per_panel for n in range(1, max_panels + 1)]
        profit = [rev - cost for rev in actual_revenue]

        df = pd.DataFrame({
            "# Panels": list(range(1, max_panels + 1)),
            "Revenue ($)": actual_revenue,
            "Profit ($)": profit
        })

        fig, ax = plt.subplots()
        sns.barplot(data=df, x="# Panels", y="Profit ($)", ax=ax, palette="coolwarm")
        ax.axhline(0, color='gray', linestyle='--')
        ax.set_title("Profitability Based on Carve-Out Strategy")
        st.pyplot(fig)

        st.markdown(f"➡️ To break even, you need **{break_even_panels:.1f}** panel reports per sample.")

# --------------------------
# Step 8: Regional Denial Rates
# --------------------------
st.markdown("## Step 8: Regional Denial Rates")
st.markdown("Use the interactive map below to educate labs on payer-specific NGS denial risks by region.")

state_data = {
    "State": ["California", "Texas", "Florida", "New York", "Illinois", "Georgia", "Pennsylvania", "Ohio", "North Carolina", "Michigan"],
    "Denial Rate (%)": [12, 18, 15, 10, 17, 14, 13, 16, 11, 19]
}
df_states = pd.DataFrame(state_data)

fig = px.choropleth(
    df_states,
    locations="State",
    locationmode="USA-states",
    color="Denial Rate (%)",
    color_continuous_scale="Reds",
    scope="usa",
    title="Estimated NGS Denial Rates by State"
)
st.plotly_chart(fig, use_container_width=True)

# --------------------------
# Step 9: Export Summary Report
# --------------------------
summary_data = pd.DataFrame(report_records)
summary_data.insert(0, "ZIP Code", zip_code)
summary_data.insert(1, "Test Strategy", test_strategy)
summary_data.insert(2, "Test Type", test_type)

csv = summary_data.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download CSV Report", data=csv, file_name="ngs_full_report.csv", mime="text/csv")

pdf_buffer = BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=letter)
c.drawString(100, 750, "NGS Reimbursement Report")
y = 720
for col in summary_data.columns:
    c.drawString(100, y, f"{col}:")
    for val in summary_data[col]:
        y -= 15
        c.drawString(120, y, str(val))
    y -= 25
c.save()
pdf = pdf_buffer.getvalue()
st.download_button("⬇️ Download PDF Report", data=pdf, file_name="ngs_full_report.pdf", mime="application/pdf")

st.success("✅ App restored with enhanced analysis, ROI simulation, denial map, and export capabilities.")

with tabs[3]:
    st.markdown("# Documentation Checklist")
    st.markdown("This section provides guidance to ensure all required documentation is prepared for successful reimbursement.")

    checklist = [
        "✅ Test order form with clear medical indication",
        "✅ Pathology report or clinical summary",
        "✅ Physician's letter of medical necessity",
        "✅ Z-code (MolDX) registration",
        "✅ CPT code alignment based on panel size and type",
        "✅ Proof of genetic counseling (for some germline panels)",
        "✅ Previous negative/inconclusive results (if reflexed)"
    ]
    for item in checklist:
        st.markdown(f"- {item}")

    st.markdown("### CPT Code Notes")
    st.markdown("""
    - **81450**: Targeted DNA/RNA analysis for solid tumors (<50 genes)
    - **81455**: Large NGS panel (>50 genes), most commonly used for CGPs
    - **81445**: Hereditary cancer panels (5–50 genes)
    - **81479**: Unlisted molecular pathology procedure (use with caution)
    """)

with tabs[2]:
    st.markdown("# Lab Workflow Optimization")
    st.markdown("### Comparing Current Dual Workflow vs. SOPHiA CGP v2")

    st.markdown("**Current Lab Workflow:**")
    st.markdown("- Running **Archer FusionPlex Sarcoma** for RNA (FDA-approved)")
    st.markdown("- Running **Separate DNA assay** for solid tumors")
    st.markdown("- Two workflows: higher tech time, increased reagents, separate validation and QA")

    st.markdown("**SOPHiA CGP v2 Workflow:**")
    st.markdown("- Single unified DNA+RNA assay")
    st.markdown("- Same-day prep, fewer consumables, and lower overall tech burden")
    st.markdown("- Streamlined QA and validation")

    st.markdown("### Input Cost Comparison")
    archer_rna_cost = st.number_input("Cost of Archer RNA Assay per Sample ($)", min_value=0, value=650)
    separate_dna_cost = st.number_input("Cost of Separate DNA Assay per Sample ($)", min_value=0, value=550)
    sophiacgp_cost = st.number_input("Cost of SOPHiA CGP v2 per Sample ($)", min_value=0, value=950)

    archer_total = archer_rna_cost + separate_dna_cost
    savings = archer_total - sophiacgp_cost

    st.markdown(f"**Current Dual Assay Cost:** ${archer_total:.2f}")
    st.markdown(f"**SOPHiA CGP v2 Cost:** ${sophiacgp_cost:.2f}")

    if savings > 0:
        st.success(f"✅ SOPHiA CGP v2 reduces per-sample cost by ${savings:.2f}")
    else:
        st.warning(f"⚠️ SOPHiA CGP v2 is currently more expensive by ${-savings:.2f}")

    st.markdown("### Operational Efficiency")
    st.markdown("- **Tech Time per Workflow:** 2 workflows = double setup, cleanup, and QC time")
    st.markdown("- **SOPHiA CGP v2** enables consolidated run and reduces turnaround time")
    st.markdown("**Time Savings Estimate**")
    tech_time_dual = st.slider("Total Tech Time for Dual Workflows (hours/sample)", 1, 10, 4)
    tech_time_sophia = st.slider("Total Tech Time for SOPHiA CGP v2 (hours/sample)", 1, 10, 2)
    hours_saved = tech_time_dual - tech_time_sophia

    st.markdown(f"🕒 Estimated **Tech Time Saved per Sample:** {hours_saved} hours")

    # Visual comparison chart
    df_compare = pd.DataFrame({
        "Workflow": ["Current (Archer + DNA)", "SOPHiA CGP v2"],
        "Cost ($)": [archer_total, sophiacgp_cost],
        "Tech Time (hrs)": [tech_time_dual, tech_time_sophia]
    })

    st.markdown("### Visual Comparison")
    fig, ax = plt.subplots(figsize=(6, 4))
    df_compare.set_index("Workflow")["Cost ($)"].plot(kind="bar", ax=ax, color=["#d62728", "#2ca02c"])
    ax.set_ylabel("Cost ($)")
    ax.set_title("Cost Comparison per Sample")
    st.pyplot(fig)

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    df_compare.set_index("Workflow")["Tech Time (hrs)"].plot(kind="bar", ax=ax2, color=["#1f77b4", "#ff7f0e"])
    ax2.set_ylabel("Tech Time (hrs)")
    ax2.set_title("Tech Time Comparison per Sample")
    st.pyplot(fig2)

    st.markdown("### Final Considerations")
    st.markdown("- FDA approval ensures reimbursement **but** comes at a **higher total operational cost**.")
    st.markdown("- Consolidating into one streamlined SOPHiA workflow reduces tech time, validation, training, and QC complexity.")
    st.markdown("- More cost-effective at scale and reduces bottlenecks in lab operations.")
