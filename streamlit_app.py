import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import eurostat
import uuid

st.set_page_config(
    page_title="AZAKI - Mérlegen az elmúlt 16 év",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# GLOBAL CSS - MINDEN SZÖVEG, CAPTION ÉS ELEM FEKETÉRE ÁLLÍTÁSA
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Minden Streamlit szöveges elem és caption feketére kényszerítése */
    html, body, p, div, span, label, h1, h2, h3, h4, h5, h6, 
    .stCaption, [data-testid="stCaptionContainer"], small, .stMarkdown p {
        color: #000000 !important;
    }
    
    /* Táblázat stílusok */
    .rank-table {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
        margin-top: -15px;
        margin-bottom: 12px;
        text-align: center;
    }
    .rank-table th, .rank-table td {
        border: 1px solid #cbd5e1;
        padding: 5px 2px;
        text-align: center;
        color: #000000;
    }
    .rank-table th {
        background-color: #f1f5f9;
        font-weight: 600;
        font-size: 12px;
    }
    .rank-table td:first-child, .rank-table th:first-child {
        text-align: left;
        font-weight: bold;
        background-color: #e2e8f0;
        white-space: nowrap;
        padding-left: 8px;
        padding-right: 8px;
    }
    .rank-table td:last-child, .rank-table th:last-child {
        background-color: #f8fafc;
        min-width: 75px;
    }
    .rank-table td:last-child span {
        font-weight: bold;
    }
    .rank-table td:last-child {
        font-size: 15px;
    }
    .rank-table span {
        display: inline-block;
    }
    .source-text {
        color: #000000 !important;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Mérlegen az elmúlt 16 év: Magyarország és a régió EU-s felzárkózása")

st.markdown("""
<div style="color: #000000 !important; font-size: 14px; line-height: 1.5; margin-bottom: 20px;">
    Az Orbán Viktor nevével fémjelzett elmúlt 16 éves korszakot egyesek az ország történetének egyik legsikeresebb időszakaként festik le, míg mások inkább történelmi léptékű kihagyott lehetőségként látják, és az EU-pénzek által nyújtott hátszél ellenére folyamatosan romló közszolgáltatásról és nem működő országról beszélnek, ahol a régió többi országa messze elhúzott mellettünk. Arra nem tennék kísérletet, hogy a különböző politikai oldalak között ítéletet hirdessek, de arra igen, hogy ábrák sokaságával illusztráljam az ország teljesítményét, az EU átlaga és a 2004 után csatlakozott 13 ország átlagához képest, így a kedves olvasó mindezek ismeretében jobban, adat alapon hozhat ítéletet.
    <br><br>
    <span style="color: #000000 !important; font-weight: bold; font-size: 13px;">Adatforrás: Eurostat | Elemzés és vizualizáció: azaki.eu</span>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# PLOTLY MOBILBARÁT BEÁLLÍTÁSOK
# -----------------------------------------------------------------------------
MOBILE_PLOT_CONFIG = {
    'scrollZoom': False,
    'displayModeBar': False,
    'showAxisDragHandles': False
}

# -----------------------------------------------------------------------------
# MUTATÓK ÉS METAADATOK (21 MUTATÓ)
# -----------------------------------------------------------------------------
INDICATORS = {
    "GDP egy főre (PPP)": {
        "code": "nama_10_pc",
        "unit": "PC_EU27_2020_HAB_MPPS_CP",
        "na_item": "B1GQ",
        "desc": "Vásárlóerő-paritáson mért egy főre jutó GDP (EU27_2020 átlag = 100%)",
        "higher_is_better": True
    },
    "2 keresős 2 gyermekes család nettó éves keresete euróban": {
        "code": "earn_nt_net",
        "currency": "EUR",
        "estruct": "NET",
        "ecase": "CPL_CH2_AW100_100",
        "desc": "Éves nettó kereset EUR-ban a családi adókedvezmények után (kétkeresős, 2 gyermekes háztartás, ahol mindkét szülő az átlagbér 100%-át keresi)",
        "higher_is_better": True
    },
    "Munkanélküliségi ráta": {
        "code": "une_rt_a",
        "unit": "PC_ACT",
        "age": "Y15-74",
        "sex": "T",
        "desc": "Munkanélküliségi ráta a 15-74 éves népesség körében (%)",
        "higher_is_better": False
    },
    "Foglalkoztatási ráta": {
        "code": "lfsi_emp_a",
        "unit": "PC_POP",
        "age": "Y20-64",
        "sex": "T",
        "wstatus": "EMP_LFS",
        "indi": "EMPM",
        "desc": "Foglalkoztatási ráta a 20-64 éves népesség körében (%)",
        "higher_is_better": True
    },
    "Termékenységi ráta": {
        "code": "demo_find",
        "indic_de": "TOTFERRT",
        "desc": "Teljes termékenységi arányszám (gyermek/nő)",
        "higher_is_better": True
    },
    "Népesség": {
        "code": "demo_gind",
        "indi": "AVG",
        "desc": "Átlagos éves népességszám (fő)",
        "higher_is_better": True
    },
    "Várható élettartam": {
        "code": "demo_mlexpec",
        "sex": "T",
        "age": "Y_LT1",
        "desc": "Születéskor várható élettartam (évek száma)",
        "higher_is_better": True
    },
    "Egészségben eltöltött várható élettartam": {
        "code": "hlth_hlye",
        "sex": "T",
        "unit": "YR",
        "hlth_hle": "HLY_LE_Y0_PC",
        "desc": "Egészségben eltöltött várható élettartam születéskor (évek száma)",
        "higher_is_better": True
    },
    "Egészségügyi kiadások a GDP %-ában": {
        "code": "hlth_sha11_hc",
        "unit": "PC_GDP",
        "icha11_hc": "TOT_HC",
        "desc": "Folyó egészségügyi kiadások a GDP százalékában (%)",
        "higher_is_better": True
    },
    "Megelőzhető és kezelhető halálozások aránya": {
        "code": "hlth_cd_apr",
        "unit": "RT",
        "sex": "T",
        "icd10": "TOTAL",
        "desc": "Elkerülhető és kezelhető halálozások száma 100 000 lakosra vetítve",
        "higher_is_better": False
    },
    "Oktatási kiadások a GDP %-ában": {
        "code": "gov_10a_exp",
        "unit": "PC_GDP",
        "cofog99": "GF09",
        "sector": "S13",
        "desc": "Kormányzati oktatási kiadások a GDP százalékában (%)",
        "higher_is_better": True
    },
    "Felsőfokú végzettségűek aránya": {
        "code": "edat_lfse_03",
        "unit": "PC",
        "age": "Y25-34",
        "sex": "T",
        "isced11": "ED5-8",
        "desc": "Felsőfokú végzettséggel rendelkező 25-34 évesek aránya (%)",
        "higher_is_better": True
    },
    "Infláció (CPI)": {
        "code": "prc_hicp_aind",
        "unit": "RCH_A_AVG",
        "coicop": "CP00",
        "desc": "Harmonizált fogyasztói árindex éves átlagos változása (%)",
        "higher_is_better": False
    },
    "Költségvetési hiány a GDP %-ában": {
        "code": "gov_10dd_edpt1",
        "unit": "PC_GDP",
        "sector": "S13",
        "na_item": "B9",
        "desc": "Kormányzati egyenleg (hiány/többlet) a GDP százalékában (%)",
        "higher_is_better": True
    },
    "Államadósság a GDP %-ában": {
        "code": "gov_10dd_edpt1",
        "unit": "PC_GDP",
        "sector": "S13",
        "na_item": "GD",
        "desc": "Bruttó államadósság a GDP százalékában (%)",
        "higher_is_better": False
    },
    "10 éves államkötvényhozamok": {
        "code": "irt_lt_mcby_a",
        "unit": "PC",
        "int_rt": "MCBY",
        "desc": "10 éves államkötvények másodlagos piaci hozama (%)",
        "higher_is_better": False
    },
    "Beruházási ráta": {
        "code": "nama_10_gdp",
        "unit": "PC_GDP",
        "na_item": "P51G",
        "desc": "Bruttó állóeszköz-felhalmozás a GDP százalékában (%)",
        "higher_is_better": True
    },
    "Termelékenység (GDP/munkaóra)": {
        "code": "nama_10_lp_ulc",
        "unit": "I10",
        "na_item": "RLPR_HW",
        "desc": "Munkatermelékenység egy munkaórára vetítve (Index, 2010 = 100%)",
        "higher_is_better": True
    },
    "Lakásárindex": {
        "code": "prc_hpi_a",
        "unit": "I15_A_AVG",
        "purchase": "TOTAL",
        "desc": "Lakásárindex éves átlaga (2015 = 100%)",
        "higher_is_better": True
    },
    "Kiadott építési engedélyek száma": {
        "code": "sts_cobp_a",
        "unit": "THS",
        "cpa2_1": "CPA_F41001",
        "s_adj": "NSA",
        "indic_bt": "BPRM_DW",
        "desc": "Kiadott építési engedélyek éves száma (ezer db)",
        "higher_is_better": True
    },
    "Reál GDP növekedés": {
        "code": "nama_10_gdp",
        "unit": "CLV_PCH_PRE",
        "na_item": "B1GQ",
        "desc": "Előző évhez képesti reál GDP változás %-ban",
        "higher_is_better": True
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
    embed_code = f'<iframe src="https://azaki.eu?indicator={code_key}" width="100%" height="820" frameborder="0" scrolling="no"></iframe>\n<p style="font-size: 12px; color: #000000;">Forrás: <a href="https://azaki.eu" target="_blank" style="color:#000000;">azaki.eu</a> / Eurostat</p>'
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

    # Special handling for household income indicator
    if info["code"] == "earn_nt_net":
        try:
            filters = {
                'estruct': 'NET',
                'ecase': 'CPL_CH2_AW100_100',
                'currency': 'EUR'
            }
            
            for key, value in filters.items():
                if key in df.columns:
                    if value in df[key].unique():
                        df = df[df[key] == value]
                    else:
                        st.warning(f"Value '{value}' not found in column '{key}'. Available values: {df[key].unique().tolist()}")
            
            if 'freq' in df.columns:
                df = df[df['freq'] == 'A']
            
            year_cols = [c for c in df.columns if str(c).isdigit() and int(c) >= 1990]
            if 'geo' in df.columns and year_cols:
                melted = pd.melt(df, id_vars=['geo'], value_vars=year_cols, var_name='Év', value_name='Érték')
                melted['Év'] = melted['Év'].astype(int)
                melted['Érték'] = pd.to_numeric(melted['Érték'], errors='coerce')
                return melted.groupby(['geo', 'Év'], as_index=False)['Érték'].mean()
        except Exception as e:
            st.error(f"Error processing household income data: {e}")
            return pd.DataFrame()

    # Special handling for fertility rate (demo_find)
    if info["code"] == "demo_find":
        try:
            if 'indic_de' in df.columns and 'indic_de' in info:
                if info['indic_de'] in df['indic_de'].unique():
                    df = df[df['indic_de'] == info['indic_de']]
                else:
                    st.warning(f"Value '{info['indic_de']}' not found in column 'indic_de'. Available: {df['indic_de'].unique().tolist()}")
            
            if 'sex' in df.columns:
                df = df[df['sex'] == 'T']
            
            if 'freq' in df.columns:
                df = df[df['freq'] == 'A']
            
            year_cols = [c for c in df.columns if str(c).isdigit() and int(c) >= 1990]
            if 'geo' in df.columns and year_cols:
                melted = pd.melt(df, id_vars=['geo'], value_vars=year_cols, var_name='Év', value_name='Érték')
                melted['Év'] = melted['Év'].astype(int)
                melted['Érték'] = pd.to_numeric(melted['Érték'], errors='coerce')
                return melted.groupby(['geo', 'Év'], as_index=False)['Érték'].mean()
        except Exception as e:
            st.error(f"Error processing fertility data: {e}")
            return pd.DataFrame()

    # Special handling for healthy life years (hlth_hlye)
    if info["code"] == "hlth_hlye":
        try:
            # Filter by sex = T (Total)
            if 'sex' in df.columns and 'sex' in info:
                if info['sex'] in df['sex'].unique():
                    df = df[df['sex'] == info['sex']]
                else:
                    st.warning(f"Value '{info['sex']}' not found in column 'sex'. Available: {df['sex'].unique().tolist()}")
            
            # Filter by hlth_hle = HLY_LE_Y0_PC
            if 'hlth_hle' in df.columns and 'hlth_hle' in info:
                if info['hlth_hle'] in df['hlth_hle'].unique():
                    df = df[df['hlth_hle'] == info['hlth_hle']]
                else:
                    st.warning(f"Value '{info['hlth_hle']}' not found in column 'hlth_hle'. Available: {df['hlth_hle'].unique().tolist()}")
            
            # Filter by unit = YR
            if 'unit' in df.columns and 'unit' in info:
                if info['unit'] in df['unit'].unique():
                    df = df[df['unit'] == info['unit']]
                else:
                    st.warning(f"Value '{info['unit']}' not found in column 'unit'. Available: {df['unit'].unique().tolist()}")
            
            if 'freq' in df.columns:
                df = df[df['freq'] == 'A']
            
            year_cols = [c for c in df.columns if str(c).isdigit() and int(c) >= 1990]
            if 'geo' in df.columns and year_cols:
                melted = pd.melt(df, id_vars=['geo'], value_vars=year_cols, var_name='Év', value_name='Érték')
                melted['Év'] = melted['Év'].astype(int)
                melted['Érték'] = pd.to_numeric(melted['Érték'], errors='coerce')
                return melted.groupby(['geo', 'Év'], as_index=False)['Érték'].mean()
        except Exception as e:
            st.error(f"Error processing healthy life years data: {e}")
            return pd.DataFrame()

    # General filtering for other indicators
    filter_keys = ['unit', 'na_item', 'coicop', 'age', 'sex', 'sector', 'indi', 'wstatus', 'int_rt', 'icha11_hc', 'icd10', 'cofog99', 'isced11', 'purchase', 'indic_sb', 'indic_de', 'hlth_hle']
    for key in filter_keys:
        if key in info and key in df.columns:
            if info[key] in df[key].unique():
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

default_countries = ["HU", "EU27_2020", "EU13_AVG", "PL", "RO"]

selected_countries = st.sidebar.multiselect(
    "Országok / Régiók:",
    options=list(EU_COUNTRIES.keys()),
    default=default_countries,
    format_func=lambda c: f"{EU_COUNTRIES.get(c, c)} ({c})"
)

year_range = st.sidebar.slider("Időszak:", 1990, 2026, (2010, 2026))

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Nézet beállítások")

use_indexing = st.sidebar.toggle("Bázisidőszakhoz viszonyított index (T=100)", value=False)
base_year = year_range[0]
if use_indexing:
    base_year = st.sidebar.number_input("Bázisév (100%):", min_value=year_range[0], max_value=year_range[1], value=year_range[0])

# -----------------------------------------------------------------------------
# FELDOLGOZÁS ÉS MEGJELENÍTÉS (MINDEN MUTATÓ AUTOMATIKUSEN)
# -----------------------------------------------------------------------------
indicator_counter = 0

for label, info in INDICATORS.items():
    indicator_counter += 1
    unique_key_suffix = f"{indicator_counter}_{uuid.uuid4().hex[:6]}"
    
    st.markdown("---")
    st.subheader(f"📊 {label}")
    st.markdown(f"<div style='color: #000000; font-size: 14px; margin-bottom: 10px;'>{info['desc']}</div>", unsafe_allow_html=True)

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
                rank_eu13_str = f"<b><span style='font-size:15px; color:#d97706;'>{hu_rank}</span></b><span style='font-size:10px; color:#000000;'>/{total_eu13}</span>"

            # EU27 Helyezés
            eu27_yr = yr_data[yr_data['geo'].isin(EU27_CODES)].copy()
            total_eu27 = len(eu27_yr)
            rank_eu27_str = "-"
            if total_eu27 > 0 and 'HU' in eu27_yr['geo'].values:
                eu27_yr['rank'] = eu27_yr['Érték'].rank(ascending=not info['higher_is_better'], method='min')
                hu_rank27 = int(eu27_yr[eu27_yr['geo'] == 'HU']['rank'].values[0])
                raw_ranks_eu27[yr] = hu_rank27
                rank_eu27_str = f"<b><span style='font-size:15px; color:#2563eb;'>{hu_rank27}</span></b><span style='font-size:10px; color:#000000;'>/{total_eu27}</span>"

            ranks_dict[yr] = {
                "eu13": rank_eu13_str,
                "eu27": rank_eu27_str
            }

        # --- HELYEZÉS VÁLTOZÁSÁNAK SZÍNEZETT KISZÁMÍTÁSA ---
        def calc_diff_html(raw_dict):
            valid_years = [y for y in years_in_range if y in raw_dict]
            if len(valid_years) >= 2:
                start_rank = raw_dict[valid_years[0]]
                end_rank = raw_dict[valid_years[-1]]
                
                rank_change = start_rank - end_rank

                if rank_change > 0:
                    return f"<span style='color: #16a34a !important; font-weight: bold;'>▲ +{rank_change}</span>"
                elif rank_change < 0:
                    return f"<span style='color: #dc2626 !important; font-weight: bold;'>▼ {rank_change}</span>"
                else:
                    return f"<span style='color: #000000 !important; font-weight: bold;'>➔ 0</span>"
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
                font=dict(color="#000000"),
                title=dict(font=dict(color="#000000")),
                xaxis=dict(
                    dtick=1, 
                    range=[year_range[0] - 0.5, year_range[1] + 0.5], 
                    fixedrange=True,
                    title=dict(font=dict(color="#000000")),
                    tickfont=dict(color="#000000")
                ),
                yaxis=dict(
                    fixedrange=True,
                    title=dict(font=dict(color="#000000")),
                    tickfont=dict(color="#000000")
                ),
                yaxis_title=y_axis_title,
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="right", 
                    x=1,
                    font=dict(color="#000000")
                ),
                margin=dict(b=10, t=50, l=10, r=10),
                updatemenus=[
                    dict(
                        buttons=list([
                            dict(
                                label="Címkék: KI",
                                method="restyle",
                                args=[{"mode": "lines+markers"}],
                            ),
                            dict(
                                label="Címkék: BE",
                                method="restyle",
                                args=[{"mode": "lines+markers+text"}],
                            )
                        ]),
                        direction="right",
                        showactive=True,
                        x=0.0,
                        xanchor="left",
                        y=1.15,
                        yanchor="top",
                        font=dict(color="#000000"),
                        bgcolor="#f0f0f0",
                        bordercolor="#cccccc",
                        borderwidth=1
                    )
                ]
            )

            st.plotly_chart(grid_fig, use_container_width=True, config=MOBILE_PLOT_CONFIG)

            # --- HELYEZÉSI TÁBLÁZAT ---
            row_eu13_vals = [ranks_dict[y]["eu13"] for y in years_in_range] + [diff_eu13_html]
            row_eu27_vals = [ranks_dict[y]["eu27"] for y in years_in_range] + [diff_eu27_html]

            col_names = years_in_range + ["Változás"]

            html_table = '<table class="rank-table">'
            html_table += '<thead><tr><th></th>'
            for col in col_names:
                html_table += f'<th>{col}</th>'
            html_table += '</tr></thead><tbody>'

            html_table += '<tr><td>Régiós helyezés (EU13)</td>'
            for val in row_eu13_vals:
                html_table += f'<td>{val}</td>'
            html_table += '</tr>'

            html_table += '<tr><td>EU helyezés (EU27)</td>'
            for val in row_eu27_vals:
                html_table += f'<td>{val}</td>'
            html_table += '</tr>'

            html_table += '</tbody></table>'

            st.markdown(html_table, unsafe_allow_html=True)

            # --- ELEMZŐ MODUL ---
            with st.expander(f"🎯 Magyarország lemaradása / előnye a régióhoz képest – {label}"):
                available_refs = [c for c in selected_countries if c != "HU"]
                
                if available_refs:
                    default_idx = available_refs.index("EU13_AVG") if "EU13_AVG" in available_refs else 0
                    
                    ref_country = st.selectbox(
                        "Referencia ország / régió kiválasztása:",
                        options=available_refs,
                        index=default_idx,
                        format_func=lambda x: EU_COUNTRIES.get(x, x),
                        key=f"gap_ref_{info['code']}_{unique_key_suffix}"
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
                            font=dict(color="#000000"),
                            xaxis=dict(dtick=1, fixedrange=True, tickfont=dict(color="#000000"), title=dict(font=dict(color="#000000"))),
                            yaxis=dict(fixedrange=True, tickfont=dict(color="#000000"), title=dict(font=dict(color="#000000"))),
                            yaxis_title="Különbség (pont / %)",
                            height=280,
                            template="plotly_white",
                            margin=dict(t=40, b=20)
                        )
                        st.plotly_chart(gap_fig, use_container_width=True, config=MOBILE_PLOT_CONFIG)

            # --- AKCIÓGOMBOK ---
            c1, c2, c3, c4, c5 = st.columns([1.8, 1.8, 2.5, 2.0, 2.0])
            
            with c1:
                if st.button(f"🔗 Beágyazási kód", key=f"embed_{info['code']}_{unique_key_suffix}"):
                    show_embed_modal(label, info['code'])
            
            with c2:
                st.download_button(
                    label="📥 CSV letöltése",
                    data=filtered_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"{info['code']}_azaki_eu.csv",
                    mime="text/csv",
                    key=f"dl_{info['code']}_{unique_key_suffix}"
                )

            with c3:
                st.markdown("<div style='padding-top: 6px; font-size: 12px; color: #000000 !important; font-weight: bold;'>Adatforrás: <b>Eurostat</b></div>", unsafe_allow_html=True)

            with c4:
                st.markdown("<div style='padding-top: 6px; font-size: 13px; color: #000000 !important; text-align: right; font-weight: bold;'><b>AZAKI.EU</b></div>", unsafe_allow_html=True)

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
st.markdown("<div style='color: #000000 !important; font-size: 14px; margin-bottom: 15px;'>Akkor hasznos, ha két makrogazdasági mutató kapcsolatát vizsgálod Magyarországon (pl. Infláció vs. GDP növekedés).</div>", unsafe_allow_html=True)

col_m1, col_m2 = st.columns(2)
with col_m1:
    ind1 = st.selectbox(
        "1. Mutató (Bal Y tengely):", 
        options=list(INDICATORS.keys()), 
        index=0,
        key="dual_ind1"
    )
with col_m2:
    ind2 = st.selectbox(
        "2. Mutató (Jobb Y tengely):", 
        options=list(INDICATORS.keys()), 
        index=12,
        key="dual_ind2"
    )

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
            font=dict(color="#000000"),
            xaxis=dict(dtick=1, fixedrange=True, tickfont=dict(color="#000000"), title=dict(font=dict(color="#000000"))),
            yaxis=dict(fixedrange=True, tickfont=dict(color="#000000"), title=dict(font=dict(color="#000000"))),
            yaxis2=dict(fixedrange=True, tickfont=dict(color="#000000"), title=dict(font=dict(color="#000000"))),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#000000"))
        )

        dual_fig.update_yaxes(title_text=ind1, secondary_y=False)
        dual_fig.update_yaxes(title_text=ind2, secondary_y=True)

        st.plotly_chart(dual_fig, use_container_width=True, config=MOBILE_PLOT_CONFIG)
