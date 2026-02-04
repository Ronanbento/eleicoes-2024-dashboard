import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
import glob
import os

# Config
st.set_page_config(page_title="Eleições 2024 - Dashboard", layout="wide", page_icon="🗳️")

# Party Colors
PARTY_COLORS = {
    'AVANTE': '#2eacb2', 'CIDADANIA': '#ec008c', 'DC': '#c89721', 'DEM': '#8CC63E',
    'MDB': '#009959', 'NOVO': '#ec671c', 'PCB': '#a8231c', 'PCDOB': '#800314',
    'PCO': '#9F030A', 'PDS': '#0067A5', 'PDT': '#FE8E6D', 'PEN': '#4AA561',
    'PFL': '#8CC63E', 'PHS': '#8A191E', 'PL': '#30306C', 'PMB': '#FF69B4',
    'PMN': '#CF7676', 'PODE': '#00d663', 'PP': '#54b8ea', 'PPL': '#9ACD32',
    'PPS': '#ec008c', 'PRB': '#005CA9', 'REPUBLICANOS': '#005CA9',
    'PROS': '#f48c24', 'PRTB': '#2cb53f', 'PSB': '#FFCC00', 'PSC': '#006f41',
    'PSD': '#ffa400', 'PSDB': '#0080FF', 'PSL': '#054577', 'PSOL': '#68018D',
    'PSTU': '#c92127', 'PT': '#C0122D', 'PTB': '#005533', 'PTC': '#01369E',
    'PTN': '#00d663', 'PV': '#01652F', 'REDE': '#3ca08c', 'SD': '#f37021',
    'SOLIDARIEDADE': '#f37021', 'UNIÃO': '#00A0DF', 'UNIAO': '#00A0DF',
    'UP': '#000000'
}

# GCS Configuration
USE_GCS = os.environ.get("USE_GCS", "false").lower() == "true"
GCS_BUCKET = "eleicoes-2024-dados"
GCS_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/data"

# Helper Functions
def normalize_name(name):
    if not isinstance(name, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', name)
                   if unicodedata.category(c) != 'Mn').upper()

@st.cache_data
def load_all_states_data(cargo_filter):
    """Load all state files from GCS or local"""
    
    if USE_GCS:
        # Production: Load from GCS
        st.info("🌐 Carregando dados do Google Cloud Storage...")
        
        # List of all states
        states = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                  'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
                  'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
        
        dfs = []
        for uf in states:
            url = f"{GCS_BASE_URL}/votacao_candidato_munzona_2024_{uf}.csv"
            try:
                df_temp = pd.read_csv(url, delimiter=';', encoding='latin1', low_memory=False)
                cargo_col = 'DS_CARGO' if 'DS_CARGO' in df_temp.columns else 'NM_TIPO_ELEICAO'
                df_temp = df_temp[df_temp[cargo_col] == cargo_filter]
                dfs.append(df_temp)
            except Exception as e:
                st.warning(f"Erro ao carregar {uf}: {e}")
        
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    else:
        # Development: Load from local
        data_folder = r"C:\Users\ronan.araujo\Downloads\votacao_candidato_munzona_2024"
        csv_files = glob.glob(os.path.join(data_folder, "votacao_candidato_munzona_2024_*.csv"))
        csv_files = [f for f in csv_files if "BRASIL" not in f]
        
        dfs = []
        for file in csv_files:
            try:
                df_temp = pd.read_csv(file, delimiter=';', encoding='latin1', low_memory=False)
                cargo_col = 'DS_CARGO' if 'DS_CARGO' in df_temp.columns else 'NM_TIPO_ELEICAO'
                df_temp = df_temp[df_temp[cargo_col] == cargo_filter]
                dfs.append(df_temp)
            except Exception as e:
                st.warning(f"Erro ao carregar {os.path.basename(file)}: {e}")
        
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data
def identify_winners(df):
    """Identify winner per municipality - PROPERLY AGGREGATED"""
    # First aggregate all votes per candidate per municipality
    agg_df = df.groupby(['SG_UF', 'NM_MUNICIPIO', 'NM_URNA_CANDIDATO', 'SG_PARTIDO']).agg({
        'QT_VOTOS_NOMINAIS_VALIDOS': 'sum'
    }).reset_index()
    
    # Now find the winner (max votes) per municipality
    winners = agg_df.loc[agg_df.groupby(['SG_UF', 'NM_MUNICIPIO'])['QT_VOTOS_NOMINAIS_VALIDOS'].idxmax()]
    return winners[['SG_UF', 'NM_MUNICIPIO', 'NM_URNA_CANDIDATO', 'SG_PARTIDO', 'QT_VOTOS_NOMINAIS_VALIDOS']]

@st.cache_data
def get_state_geojson(uf_code):
    """Fetch GeoJSON for a given UF"""
    url = f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf_code}/?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
    response = requests.get(url)
    return response.json()

@st.cache_data
def get_municipality_names(uf_code):
    """Fetch Municipality ID to Name mapping"""
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_code}/municipios"
    mun_list = requests.get(url).json()
    return {str(m['id']): m['nome'] for m in mun_list}

# Main App
st.title("🗳️ Dashboard Eleições Municipais 2024")
st.info("ℹ️ **Dados**: Eleições Municipais 2024. Navegação hierárquica: Brasil → Estado → Município")

# Step 1: Cargo Selection
st.sidebar.header("1️⃣ Selecione o Cargo")
cargo_type = st.sidebar.radio("Cargo", ["Prefeito", "Vereador"])

# Step 1.5: Round Selection
st.sidebar.header("🔄 Selecione o Turno")
if cargo_type == "Prefeito":
    turno_option = st.sidebar.radio("Turno", ["Apenas Vencedores Finais", "1º Turno", "2º Turno", "Todos os Turnos"])
    st.sidebar.info("💡 **Vencedores Finais**: Mostra automaticamente o resultado do 2º turno onde houve, ou 1º turno nos demais casos")
else:
    turno_option = "1º Turno"  # Vereador só tem 1 turno
    st.sidebar.info("ℹ️ Vereador tem apenas um turno")

with st.spinner(f"Carregando dados de {cargo_type}..."):
    df_all = load_all_states_data(cargo_type)

if df_all.empty:
    st.error("Nenhum dado encontrado para o cargo selecionado.")
    st.stop()

# Filter by round
if turno_option == "1º Turno":
    df_all = df_all[df_all['NR_TURNO'] == 1]
elif turno_option == "2º Turno":
    df_all = df_all[df_all['NR_TURNO'] == 2]
elif turno_option == "Apenas Vencedores Finais":
    # Get final round per municipality (max turno)
    max_turno_per_mun = df_all.groupby(['SG_UF', 'NM_MUNICIPIO'])['NR_TURNO'].max().reset_index()
    max_turno_per_mun.columns = ['SG_UF', 'NM_MUNICIPIO', 'MAX_TURNO']
    df_all = df_all.merge(max_turno_per_mun, on=['SG_UF', 'NM_MUNICIPIO'])
    df_all = df_all[df_all['NR_TURNO'] == df_all['MAX_TURNO']]
    df_all = df_all.drop(columns=['MAX_TURNO'])
# "Todos os Turnos" = no filter

# Identify winners
winners_df = identify_winners(df_all)

# Step 2: Navigation Level
st.sidebar.header("2️⃣ Navegação")
nav_level = st.sidebar.radio("Nível de Visualização", ["Brasil (Todos)", "Estado Específico", "Município Específico"])

# Level 1: Brasil View
if nav_level == "Brasil (Todos)":
    st.subheader(f"🌎 Visão Brasil - Vencedores de {cargo_type}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Municípios", len(winners_df))
    with col2:
        st.metric("Total de Votos Válidos", f"{winners_df['QT_VOTOS_NOMINAIS_VALIDOS'].sum():,}".replace(',', '.'))
    
    # Top Winners Table
    st.subheader("🏆 Top 20 Vencedores (por votos)")
    top_winners = winners_df.sort_values('QT_VOTOS_NOMINAIS_VALIDOS', ascending=False).head(20)
    top_winners_display = top_winners.copy()
    top_winners_display['Partido'] = top_winners_display['SG_PARTIDO'].apply(
        lambda x: f"<span style='color: {PARTY_COLORS.get(x, '#666')}'><b>{x}</b></span>"
    )
    st.write(top_winners_display[['SG_UF', 'NM_MUNICIPIO', 'NM_URNA_CANDIDATO', 'Partido', 'QT_VOTOS_NOMINAIS_VALIDOS']].to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Party Distribution
    st.subheader("📊 Distribuição por Partido")
    party_dist = winners_df['SG_PARTIDO'].value_counts().head(15)
    fig_party = go.Figure(data=[go.Bar(
        x=party_dist.index,
        y=party_dist.values,
        marker_color=[PARTY_COLORS.get(p, '#cccccc') for p in party_dist.index]
    )])
    fig_party.update_layout(title="Municípios Vencidos por Partido", xaxis_title="Partido", yaxis_title="Municípios")
    st.plotly_chart(fig_party, use_container_width=True)

# Level 2: State View
elif nav_level == "Estado Específico":
    st.sidebar.subheader("🔍 Selecione o Estado")
    selected_uf = st.sidebar.selectbox("UF", sorted(winners_df['SG_UF'].unique()))
    
    state_winners = winners_df[winners_df['SG_UF'] == selected_uf]
    
    st.subheader(f"🗺️ {selected_uf} - Vencedores de {cargo_type}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Municípios", len(state_winners))
    with col2:
        st.metric("Total de Votos", f"{state_winners['QT_VOTOS_NOMINAIS_VALIDOS'].sum():,}".replace(',', '.'))
    with col3:
        party_lead = state_winners['SG_PARTIDO'].value_counts().idxmax()
        st.metric("Partido Líder", party_lead)
    
    # Bubble Chart
    st.subheader("💡 Mapa de Bolhas - Vencedores por Município")
    fig_bubble = px.scatter(state_winners, 
                            x='NM_MUNICIPIO', 
                            y='QT_VOTOS_NOMINAIS_VALIDOS',
                            size='QT_VOTOS_NOMINAIS_VALIDOS',
                            color='SG_PARTIDO',
                            color_discrete_map=PARTY_COLORS,
                            hover_data=['NM_URNA_CANDIDATO'],
                            title=f"Vencedores em {selected_uf}")
    fig_bubble.update_layout(xaxis_title="Município", yaxis_title="Votos", xaxis={'tickangle': -45})
    st.plotly_chart(fig_bubble, use_container_width=True)
    
    # Geographic Map
    st.subheader("🗺️ Mapa Geográfico - Vencedores por Partido")
    with st.spinner("Carregando mapa..."):
        try:
            geojson = get_state_geojson(selected_uf)
            id_to_name = get_municipality_names(selected_uf)
            
            # Prepare data mapping
            votes_map = {}
            party_map = {}
            for _, row in state_winners.iterrows():
                mun_norm = normalize_name(row['NM_MUNICIPIO'])
                votes_map[mun_norm] = row['QT_VOTOS_NOMINAIS_VALIDOS']
                party_map[mun_norm] = row['SG_PARTIDO']
            
            # Inject data into GeoJSON
            for feature in geojson['features']:
                cod = str(feature['properties'].get('codarea', ''))
                mun_name = id_to_name.get(cod, 'Unknown')
                mun_norm = normalize_name(mun_name)
                
                feature['properties']['name'] = mun_name
                feature['properties']['name_join_key'] = mun_norm
                feature['properties']['votes'] = votes_map.get(mun_norm, 0)
                feature['properties']['party'] = party_map.get(mun_norm, 'N/A')
                feature['properties']['color'] = PARTY_COLORS.get(party_map.get(mun_norm, ''), '#cccccc')
            
            # Create map
            m = folium.Map(location=[-15, -47], zoom_start=6)
            
            # Add colored polygons
            for feature in geojson['features']:
                folium.GeoJson(
                    feature,
                    style_function=lambda x: {
                        'fillColor': x['properties']['color'],
                        'color': '#000000',
                        'weight': 0.5,
                        'fillOpacity': 0.6
                    },
                    tooltip=folium.Tooltip(
                        f"<b>{feature['properties']['name']}</b><br>"
                        f"Partido: {feature['properties']['party']}<br>"
                        f"Votos: {feature['properties']['votes']:,}".replace(',', '.')
                    )
                ).add_to(m)
            
            st_folium(m, width=800, height=600)
        except Exception as e:
            st.error(f"Erro ao carregar mapa: {e}")
    
    # Winners Table
    st.subheader("📋 Lista de Vencedores")
    st.dataframe(state_winners[['NM_MUNICIPIO', 'NM_URNA_CANDIDATO', 'SG_PARTIDO', 'QT_VOTOS_NOMINAIS_VALIDOS']].sort_values('QT_VOTOS_NOMINAIS_VALIDOS', ascending=False), use_container_width=True, hide_index=True)

# Level 3: Municipality View
elif nav_level == "Município Específico":
    st.sidebar.subheader("🔍 Selecione Estado e Município")
    selected_uf = st.sidebar.selectbox("UF", sorted(df_all['SG_UF'].unique()))
    
    municipalities = df_all[df_all['SG_UF'] == selected_uf]['NM_MUNICIPIO'].dropna().unique()
    selected_mun = st.sidebar.selectbox("Município", sorted(municipalities))
    
    mun_data = df_all[(df_all['SG_UF'] == selected_uf) & (df_all['NM_MUNICIPIO'] == selected_mun)]
    mun_data = mun_data.groupby(['NM_URNA_CANDIDATO', 'SG_PARTIDO']).agg({
        'QT_VOTOS_NOMINAIS_VALIDOS': 'sum'
    }).reset_index().sort_values('QT_VOTOS_NOMINAIS_VALIDOS', ascending=False)
    
    st.subheader(f"🏙️ {selected_mun} ({selected_uf}) - {cargo_type}")
    
    if not mun_data.empty:
        winner = mun_data.iloc[0]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏆 Vencedor", winner['NM_URNA_CANDIDATO'])
        with col2:
            st.metric("Partido", winner['SG_PARTIDO'])
        with col3:
            st.metric("Votos", f"{winner['QT_VOTOS_NOMINAIS_VALIDOS']:,}".replace(',', '.'))
        
        # All Candidates
        st.subheader("📊 Todos os Candidatos")
        fig_cand = go.Figure(data=[go.Bar(
            x=mun_data['NM_URNA_CANDIDATO'],
            y=mun_data['QT_VOTOS_NOMINAIS_VALIDOS'],
            marker_color=[PARTY_COLORS.get(p, '#cccccc') for p in mun_data['SG_PARTIDO']],
            text=mun_data['SG_PARTIDO'],
            textposition='auto'
        )])
        fig_cand.update_layout(title=f"Votação em {selected_mun}", xaxis_title="Candidato", yaxis_title="Votos", xaxis={'tickangle': -45})
        st.plotly_chart(fig_cand, use_container_width=True)
        
        st.dataframe(mun_data, use_container_width=True, hide_index=True)
