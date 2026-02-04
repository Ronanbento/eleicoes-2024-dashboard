# 🗳️ Dashboard Eleições Municipais 2024

Dashboard interativo para análise dos resultados das Eleições Municipais 2024 no Brasil.

## Funcionalidades

- ✅ Navegação hierárquica: Brasil → Estado → Município
- 🎨 Cores oficiais dos partidos políticos
- 🗺️ Mapas geográficos interativos por estado
- 📊 Gráficos e visualizações detalhadas
- 🔄 Filtro de turnos (1º, 2º ou Vencedores Finais)
- 🏆 Identificação automática de vencedores

## Dados

Fonte: [TSE - Repositório de Dados Eleitorais](https://dadosabertos.tse.jus.br/)

## Como Usar

1. Selecione o **Cargo** (Prefeito ou Vereador)
2. Escolha o **Turno** (Vencedores Finais recomendado)
3. Navegue pelos níveis:
   - **Brasil**: Visão geral de todos os municípios
   - **Estado**: Mapas e rankings estaduais
   - **Município**: Detalhamento com todos os candidatos

## Tecnologias

- Python 3.11
- Streamlit
- Pandas, Plotly, Folium
- API IBGE (GeoJSON)

## Deploy

Hospedado via Streamlit Community Cloud com dados no Google Cloud Storage.
