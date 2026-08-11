import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import eurostat

st.set_page_config(
    page_title="AZAKI - Magyarország vs EU Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🇭🇺 Magyarország vs. EU gazdasági összehasonlítás (1990-től)")
st.caption("Adatforrás: Eurostat | Elemzés és vizualizáció: **azaki.eu**")

# -----------------------------------------------------------------------------
# METADATA & SZŰRŐK
# -----------------------------------------------------------------------------
INDICATORS = {
    "GDP egy főre (PPS / EU27=100%)": {
        "code": "nama_10_pc",
        "unit": "PC_EU27_2020_HAB_MPPS_CP",
        "na_item": "B1GQ",
        "desc": "Vásárlóerő-paritáson mért egy főre jutó GDP (EU27_2020 átlag = 100%)",
        "higher_is_better": True
    },
    "Reál GDP növekedés (%)": {
        "code": "nama_10_gdp",
        "unit": "CLV_PCH_PRE",
        "na_item": "B1GQ",
        "desc": "Előző évhez képesti reál GDP változás %-ban",
        "higher_is_better": True
    },
    "Infláció (HICP / CPI %)": {
        "code": "prc_hicp_aind",
        "unit": "RCH_A_AVG",
        "coicop": "CP00",
        "desc": "Harmonizált fogyasztói árindex éves átlagos változása (%)",
        "higher_is_better": False
    },
    "Munkanélküliségi ráta (%)": {
        "code": "une_rt_a",
        "unit": "PC_ACT",
        "age": "Y15-74",
        "sex": "T",
        "desc": "Munkanélküliségi ráta a 15-74 éves népesség körében (%)",
        "higher_is_better": False
    },
    "Foglalkoztatási ráta (%)": {
        "code": "lfsi_emp_a",
        "unit": "PC_POP",
        "age": "Y20-64",
        "sex": "T",
        "wstatus": "EMP_LFS",
        "indi": "EMPM",
        "desc": "Foglalkoztatási ráta a 20-64 éves népesség körében (%)",
        "higher_is_better": True
    },
    "Államadósság (% GDP)": {
        "code": "gov_10dd_edpt1",
        "unit": "PC_GDP",
        "sector": "S13",
        "na_item": "GD",
        "desc": "Bruttó államadósság a GDP százalékában (S13 szektor)",
        "higher_is_better": False
    },
    "Hosszú távú kamatláb / Állampapírhozam (%)": {
        "code": "irt_lt_mcby_a",
        "unit": "PC",
        "int_rt": "MCBY",
        "desc": "10 éves államkötvények másodlagos piaci hozama (%)",
        "higher_is_better": False
    }
}

EU13_CODES = ["CY", "CZ", "EE", "PL", "LV", "LT", "HU", "MT", "SK", "SI", "BG", "RO", "HR"]
EU27_CODES = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", 
              "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]

EU_COUNTRIES = {
    "HU": "Magyarország",
    "EU27_2020": "EU27 Átlag",
    "EU13_AVG": "EU13 Átlag",
    "PL": "Lengyelország",
    "RO": "Románia",
    "AT": "Ausztria",
    "BE": "Belgium",
    "BG": "Bulgária",
    "CY": "Ciprus",
    "CZ": "Csehország",
    "DK": "Dánia",
    "EE": "Észtország",
    "FI": "Finnország",
    "FR": "Franciaország",
    "GR": "Görögország",
    "HR": "Horvátország",
    "IE": "Írország",
    "LV": "Lettország",
    "LT": "Litvánia",
    "LU": "Luxemburg",
    "MT": "Málta",
    "DE": "Németország",
    "IT": "Olaszország",
    "PT": "Portugália",
    "ES": "Spanyolország",
    "SE": "Svédország",
    "SK": "Szlovákia",
    "SI": "Szlovénia",
    "NL": "Hollandia"
}

SORT_ORDER = ["Magyarország", "EU27 Átlag", "EU13 Átlag", "Lengyelország", "Románia"]

# -----------------------------------------------------------------------------
# EMBED DIALOGUS
# -----------------------------------------------------------------------------
@st.dialog("🔗 Ábra beágyazása a weboldaladra / cikkedbe")
def show_embed_modal(label_text, code_key):
    st.write("Másold ki az alábbi HTML kódot, és illeszd be a tartalomkezelődbe (WordPress, CMS, HTML):")
    embed_code = f'<iframe src="https://azaki.eu?indicator={code_key}" width="100%" height="820" frameborder="0" scrolling="no"></iframe>\n<p style="font-size: 12px; color: #666;">Forrás: <a href="https://azaki.eu" target="_blank">azaki.eu</a> / Eurostat</p>'
    st.code(embed_code, language="html")
    st.info("💡 A beágyazott grafikon megőrzi az interaktivitását, a helyezési táblázatot és az akciógombokat is!")

# -----------------------------------------------------------------------------
# ADATLETÖLTÉS & CACHING
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600*24)
def load_eurostat_dataset(code):
    try:
        df = eurostat.get_data_df(code, flags=False)
        return df
    except Exception:
        return pd.DataFrame()

def prepare_clean_df(raw_df, info):
    if raw_df.empty:
        return pd.DataFrame()
    
    df = raw_df.copy()
    geo_col = [c for c in df.columns if 'geo' in c.lower()]
    if geo_col:
        df.rename(columns={geo_col[0]: 'geo'}, inplace=True)

    for key in ['unit', 'na_item', 'coicop', 'age', 'sex', 'sector', 'indi', 'wstatus', 'int_rt']:
        if key in info and key in df.columns:
            df = df[df[key] == info[key]]

    if 'freq' in df.columns:
        df = df[df['freq'] == 'A']
    if 'counterpart_area' in df.columns:
        df = df[df['counterpart_area'] == 'W2']
    if 'sector2' in df.columns:
        df = df[df['sector2'] == 'S1']

    year_cols = [c for c in df.columns if str(c).isdigit() and int(c) >= 1990]
    
    if 'geo' in df.columns and year_cols:
        melted = pd.melt(df, id_vars=['geo'], value_vars=year_cols, var_name='Év', value_name='Érték')
        melted['Év'] = melted['Év'].astype(int)
        melted['Érték'] = pd.to_numeric(melted['Érték'], errors='coerce')
        return melted.groupby(['geo', 'Év'], as_index=False)['Érték'].mean()
    return pd.DataFrame()

# -----------------------------------------------------------------------------
# SIDEBAR BEÁLLÍTÁSOK
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Globális Beállítások")

selected_indicators = st.sidebar.multiselect(
    "Megjelenítendő mutatók:",
    options=list(INDICATORS.keys()),
    default=list(INDICATORS.keys())
)

default_countries = ["HU", "EU27_2020", "EU13_AVG", "PL", "RO"]

selected_countries = st.sidebar.multiselect(
    "Országok / Régiók:",
    options=list(EU_COUNTRIES.keys()),
    default=default_countries,
    format_func=lambda c: f"{EU_COUNTRIES.get(c, c)} ({c})"
)

year_range = st.sidebar.slider("Időszak:", 1990, 2026, (2010, 2025))

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Nézet beállítások")

use_indexing = st.sidebar.toggle("Bázisidőszakhoz viszonyított index (T=100)", value=False)
base_year = year_range[0]
if use_indexing:
    base_year = st.sidebar.number_input("Bázisév (100%):", min_value=year_range[0], max_value=year_range[1], value=year_range[0])

# -----------------------------------------------------------------------------
# FELDOLGOZÁS ÉS MEGJELENÍTÉS
# -----------------------------------------------------------------------------
if not selected_indicators:
    st.info("Kérlek, válassz ki legalább egy mutatót a bal oldali sávban!")

for label in selected_indicators:
    info = INDICATORS[label]
    
    st.markdown("---")
    st.subheader(f"📊 {label}")
    st.caption(info["desc"])

    with st.spinner(f"Adatok betöltése ({label})..."):
        raw_df = load_eurostat_dataset(info["code"])
        all_countries_df = prepare_clean_df(raw_df, info)

    if not all_countries_df.empty:
        # --- HELYEZÉSEK SZÁMÍTÁSA MAGYARORSZÁGNAK ---
        ranks_dict = {}
        years_in_range = list(range(year_range[0], year_range[1] + 1))
        
        raw_ranks_eu13 = {}
        raw_ranks_eu27 = {}

        for yr in years_in_range:
            yr_data = all_countries_df[all_countries_df['Év'] == yr].dropna(subset=['Érték'])
            
            # EU13 Helyezés
            eu13_yr = yr_data[yr_data['geo'].isin(EU13_CODES)].copy()
            total_eu13 = len(eu13_yr)
            rank_eu13_str = "-"
            if total_eu13 > 0 and 'HU' in eu13_yr['geo'].values:
                eu13_yr['rank'] = eu13_yr['Érték'].rank(ascending=not info['higher_is_better'], method='min')
                hu_rank = int(eu13_yr[eu13_yr['geo'] == 'HU']['rank'].values[0])
                raw_ranks_eu13[yr] = hu_rank
                rank_eu13_str = f"<b><span style='font-size:15px;'>{hu_rank}</span></b><span style='font-size:10px;'>/{total_eu13}</span>"

            # EU27 Helyezés
            eu27_yr = yr_data[yr_data['geo'].isin(EU27_CODES)].copy()
            total_eu27 = len(eu27_yr)
            rank_eu27_str = "-"
            if total_eu27 > 0 and 'HU' in eu27_yr['geo'].values:
                eu27_yr['rank'] = eu27_yr['Érték'].rank(ascending=not info['higher_is_better'], method='min')
                hu_rank27 = int(eu27_yr[eu27_yr['geo'] == 'HU']['rank'].values[0])
                raw_ranks_eu27[yr] = hu_rank27
                rank_eu27_str = f"<b><span style='font-size:15px;'>{hu_rank27}</span></b><span style='font-size:10px;'>/{total_eu27}</span>"

            ranks_dict[yr] = {
                "eu13": rank_eu13_str,
                "eu27": rank_eu27_str
            }

        def calc_diff_html(raw_dict):
            valid_years = [y for y in years_in_range if y in raw_dict]
            if len(valid_years) >= 2:
                start_rank = raw_dict[valid_years[0]]
                end_rank = raw_dict[valid_years[-1]]
                diff = start_rank - end_rank
                if diff > 0:
                    return f"<span style='color:#16a34a; font-weight:bold;'>▲ +{diff}</span>"
                elif diff < 0:
                    return f"<span style='color:#dc2626; font-weight:bold;'>▼ {diff}</span>"
                else:
                    return f"<span style='color:#64748b; font-weight:bold;'>➔ 0</span>"
            return "-"

        diff_eu13_html = calc_diff_html(raw_ranks_eu13)
        diff_eu27_html = calc_diff_html(raw_ranks_eu27)

        # EU13 Átlag
        eu13_df = all_countries_df[all_countries_df['geo'].isin(EU13_CODES)].groupby('Év', as_index=False)['Érték'].mean()
        eu13_df['geo'] = 'EU13_AVG'
        
        melted_with_avg = pd.concat([all_countries_df, eu13_df], ignore_index=True)

        filtered_df = melted_with_avg[
            (melted_with_avg['geo'].isin(selected_countries)) &
            (melted_with_avg['Év'] >= year_range[0]) &
            (melted_with_avg['Év'] <= year_range[1])
        ].dropna(subset=['Érték']).copy()

        filtered_df['Ország'] = filtered_df['geo'].map(lambda x: EU_COUNTRIES.get(x, x))

        if not filtered_df.empty:
            # BÁZISINDEX KISZÁMÍTÁSA
            if use_indexing:
                base_values = filtered_df[filtered_df['Év'] == base_year].set_index('Ország')['Érték'].to_dict()
                filtered_df['Megjelenített_Érték'] = filtered_df.apply(
                    lambda r: (r['Érték'] / base_values[r['Ország']]) * 100 if r['Ország'] in base_values and base_values[r['Ország']] != 0 else None, axis=1
                )
                y_axis_title = f"Index ({base_year} = 100%)"
            else:
                filtered_df['Megjelenített_Érték'] = filtered_df['Érték']
                y_axis_title = "Érték"

            filtered_df['Címke'] = filtered_df['Megjelenített_Érték'].map(lambda x: f"{x:.1f}" if pd.notnull(x) else "")

            present_countries = filtered_df['Ország'].unique().tolist()
            ordered_countries = [c for c in SORT_ORDER if c in present_countries]
            ordered_countries += sorted([c for c in present_countries if c not in SORT_ORDER])

            # --- HIGHLIGHT & HOVER VONALDIAGRAM ---
            fig = px.line(
                filtered_df,
                x='Év',
                y='Megjelenített_Érték',
                color='Ország',
                text='Címke',
                category_orders={'Ország': ordered_countries},
                markers=True,
                template="plotly_white",
                labels={'Megjelenített_Érték': y_axis_title}
            )

            for trace in fig.data:
                if trace.name == "Magyarország":
                    trace.line.color = '#D62728'
                    trace.line.width = 4.5
                    trace.opacity = 1.0
                elif trace.name == "EU27 Átlag":
                    trace.line.color = '#1F77B4'
                    trace.line.width = 2.5
                    trace.opacity = 0.85
                elif trace.name == "EU13 Átlag":
                    trace.line.color = '#00CC96'
                    trace.line.width = 2.5
                    trace.opacity = 0.85
                else:
                    trace.line.width = 1.8
                    trace.opacity = 0.65

                trace.textposition = "top center"
                trace.textfont = dict(color=trace.line.color, size=11)
                trace.mode = 'lines+markers'

            grid_fig = go.Figure()
            for tr in fig.data:
                grid_fig.add_trace(tr)

            grid_fig.update_layout(
                height=460,
                hovermode="x unified",
                xaxis=dict(dtick=1, range=[year_range[0] - 0.5, year_range[1] + 0.5]),
                yaxis_title=y_axis_title,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(b=10, t=50, l=10, r=10),
                updatemenus=[
                    dict(
                        type="buttons",
                        direction="right",
                        active=0,
                        x=0.0,
                        y=1.15,
                        xanchor="left",
                        yanchor="top",
                        buttons=[
                            dict(label="Címkék: KI", method="restyle", args=[{"mode": "lines+markers"}]),
                            dict(label="Címkék: BE", method="restyle", args=[{"mode": "lines+markers+text"}])
                        ]
                    )
                ]
            )

            st.plotly_chart(grid_fig, use_container_width=True)

            # --- HELYEZÉSI TÁBLÁZAT ---
            row_eu13_vals = [ranks_dict[y]["eu13"] for y in years_in_range] + [diff_eu13_html]
            row_eu27_vals = [ranks_dict[y]["eu27"] for y in years_in_range] + [diff_eu27_html]

            col_names = years_in_range + ["Változás"]

            rank_df = pd.DataFrame(
                [row_eu13_vals, row_eu27_vals],
                index=["Régiós helyezés (EU13)", "EU helyezés (EU27)"],
                columns=col_names
            )

            html_table = rank_df.to_html(escape=False, classes="rank-table")
            
            st.markdown("""
            <style>
            .rank-table {
                width: 100%;
                border-collapse: collapse;
                font-family: sans-serif;
                margin-top: -15px;
                margin-bottom: 12px;
                text-align: center;
            }
            .rank-table th, .rank-table td {
                border: 1px solid #e2e8f0;
                padding: 5px 2px;
                text-align: center;
            }
            .rank-table th {
                background-color: #f8fafc;
                font-weight: 600;
                font-size: 12px;
                color: #475569;
            }
            .rank-table td:first-child, .rank-table th:first-child {
                text-align: left;
                font-weight: bold;
                background-color: #f1f5f9;
                white-space: nowrap;
                padding-left: 8px;
                padding-right: 8px;
                color: #1e293b;
            }
            .rank-table td:last-child, .rank-table th:last-child {
                background-color: #f8fafc;
                min-width: 75px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(html_table, unsafe_allow_html=True)

            # --- ELEMZŐ MODUL: MAGYARORSZÁG LEMARADÁSA / ELŐNYE A RÉGIÓHOZ KÉPEST ---
            with st.expander(f"🎯 Magyarország lemaradása / előnye a régióhoz képest – {label}"):
                available_refs = [c for c in selected_countries if c != "HU"]
                
                if available_refs:
                    default_idx = available_refs.index("EU13_AVG") if "EU13_AVG" in available_refs else 0
                    
                    ref_country = st.selectbox(
                        "Referencia ország / régió kiválasztása:",
                        options=available_refs,
                        index=default_idx,
                        format_func=lambda x: EU_COUNTRIES.get(x, x),
                        key=f"gap_ref_{info['code']}"
                    )

                    if ref_country:
                        hu_vals = filtered_df[filtered_df['geo'] == 'HU'].set_index('Év')['Érték']
                        ref_vals = filtered_df[filtered_df['geo'] == ref_country].set_index('Év')['Érték']
                        
                        gap_df = pd.DataFrame({'HU': hu_vals, 'REF': ref_vals}).dropna()
                        gap_df['Eltérés'] = gap_df['HU'] - gap_df['REF']

                        gap_fig = go.Figure()
                        gap_fig.add_trace(go.Bar(
                            x=gap_df.index,
                            y=gap_df['Eltérés'],
                            marker_color=['#16a34a' if val >= 0 else '#dc2626' for val in gap_df['Eltérés']],
                            name="Eltérés"
                        ))
                        
                        gap_fig.update_layout(
                            title=f"Magyarország vs. {EU_COUNTRIES.get(ref_country, ref_country)} közötti különbség",
                            xaxis=dict(dtick=1),
                            yaxis_title="Különbség (pont / %)",
                            height=280,
                            template="plotly_white",
                            margin=dict(t=40, b=20)
                        )
                        st.plotly_chart(gap_fig, use_container_width=True)

            # --- AKCIÓGOMBOK EGY SORBAN ---
            c1, c2, c3, c4, c5 = st.columns([1.8, 1.8, 2.5, 2.0, 2.0])
            
            with c1:
                if st.button(f"🔗 Beágyazási kód", key=f"embed_{info['code']}"):
                    show_embed_modal(label, info['code'])
            
            with c2:
                st.download_button(
                    label="📥 CSV letöltése",
                    data=filtered_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"{info['code']}_azaki_eu.csv",
                    mime="text/csv",
                    key=f"dl_{info['code']}"
                )

            with c3:
                st.markdown("<div style='padding-top: 6px; font-size: 12px; color: #64748b;'>Adatforrás: <b>Eurostat</b></div>", unsafe_allow_html=True)

            with c4:
                st.markdown("<div style='padding-top: 6px; font-size: 13px; color: #64748b; text-align: right;'><b>AZAKI.EU</b></div>", unsafe_allow_html=True)

            with c5:
                with st.popover("📄 Adattábla"):
                    pivoted = filtered_df.pivot(index='Év', columns='Ország', values='Érték').sort_index(ascending=False)
                    pivoted_cols = [c for c in ordered_countries if c in pivoted.columns]
                    st.dataframe(pivoted[pivoted_cols], use_container_width=True)

        else:
            st.warning("A kiválasztott szűrők alapján nincs elérhető adat ehhez a mutatóhoz.")
    else:
        st.error(f"Nem sikerült letölteni az adatokat az Eurostatról ({info['code']}).")

# -----------------------------------------------------------------------------
# MODUL 2: KÉT MUTATÓ EGYÜTTES ÁBRÁZOLÁSA (DUAL-AXIS DIAGRAM / KORRELÁCIÓ)
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("🔀 Két Mutató Együttes Ábrázolása (Dual-Axis Korreláció)")
st.caption("Akkor hasznos, ha két makrogazdasági mutató kapcsolatát vizsgálod Magyarországon (pl. Infláció vs. GDP növekedés).")

col_m1, col_m2 = st.columns(2)
with col_m1:
    ind1 = st.selectbox("1. Mutató (Bal Y tengely):", options=list(INDICATORS.keys()), index=0)
with col_m2:
    ind2 = st.selectbox("2. Mutató (Jobb Y tengely):", options=list(INDICATORS.keys()), index=2)

if ind1 and ind2:
    raw1 = load_eurostat_dataset(INDICATORS[ind1]["code"])
    raw2 = load_eurostat_dataset(INDICATORS[ind2]["code"])

    df1 = prepare_clean_df(raw1, INDICATORS[ind1])
    df2 = prepare_clean_df(raw2, INDICATORS[ind2])

    if not df1.empty and not df2.empty:
        hu1 = df1[(df1['geo'] == 'HU') & (df1['Év'] >= year_range[0]) & (df1['Év'] <= year_range[1])].set_index('Év')['Érték']
        hu2 = df2[(df2['geo'] == 'HU') & (df2['Év'] >= year_range[0]) & (df2['Év'] <= year_range[1])].set_index('Év')['Érték']

        dual_df = pd.DataFrame({ind1: hu1, ind2: hu2}).dropna()

        dual_fig = make_subplots(specs=[[{"secondary_y": True}]])

        dual_fig.add_trace(
            go.Scatter(x=dual_df.index, y=dual_df[ind1], name=ind1, mode='lines+markers', line=dict(color='#D62728', width=3)),
            secondary_y=False,
        )

        dual_fig.add_trace(
            go.Scatter(x=dual_df.index, y=dual_df[ind2], name=ind2, mode='lines+markers', line=dict(color='#1F77B4', width=3, dash='dash')),
            secondary_y=True,
        )

        dual_fig.update_layout(
            title_text=f"Magyarország: {ind1} <i>vs.</i> {ind2}",
            template="plotly_white",
            height=450,
            hovermode="x unified",
            xaxis=dict(dtick=1),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        dual_fig.update_yaxes(title_text=ind1, secondary_y=False)
        dual_fig.update_yaxes(title_text=ind2, secondary_y=True)

        st.plotly_chart(dual_fig, use_container_width=True)
