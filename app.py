import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Observatorio de Franquicias – Córdoba", layout="wide")

USUARIOS_VALIDOS = {
    "rodolfopardo": "1234",
    "jp": "1234",
    "brian": "1234"
}

def login():
    st.image("search.mas-logo-blanco.png", width=200)
    st.title("🔐 Observatorio de Franquicias – Córdoba")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        if user in USUARIOS_VALIDOS and password == USUARIOS_VALIDOS[user]:
            st.session_state['logged_in'] = True
            st.session_state['user'] = user
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

if 'logged_in' not in st.session_state:
    login()
    st.stop()

# --- CARGA Y LIMPIEZA DE DATOS ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("search.mas-logo-blanco.png", width=120)
with col_title:
    st.title("📊 Observatorio de Franquicias – Córdoba")

st.sidebar.markdown(f"👤 Sesión iniciada como: `{st.session_state.get('user', '')}`")


@st.cache_data
def cargar_datos():
    df = pd.read_csv("https://drive.google.com/uc?id=162YQgYfv4cbL3yudA-hNysDp3V4MqUgI")
    df['title'] = df['title'].astype(str)
    

    df['addressPreview'] = df['addressPreview'].astype(str)
    df = df[df['addressPreview'].str.contains(r'c[oó]rdoba', case=False, na=False)]

    total_original = len(df)

    
    total_cordoba = len(df)
    eliminados = total_original - total_cordoba

    # Normalización de títulos
    df['title_normalizado'] = df['title'].str.lower().str.replace(r'[^a-z0-9 ]', '', regex=True)

    # Detección de franquiciados
    marca_counts = df['title_normalizado'].value_counts()
    df['es_franquiciado'] = df['title_normalizado'].isin(marca_counts[marca_counts > 1].index)

    return df, eliminados

df, registros_fuera_cordoba = cargar_datos()

if registros_fuera_cordoba > 0:
    st.warning(f"⚠️ Se eliminaron {registros_fuera_cordoba} registros que no pertenecen a Córdoba.")

# --- PANEL GENERAL ---
st.markdown("### Panel General")

total_filas = len(df)
total_columnas = df.shape[1]
total_marcas = df['title'].nunique()
marcas_franquiciadas = df[df['es_franquiciado']]['title'].nunique()
marcas_no_franquiciadas = total_marcas - marcas_franquiciadas

porc_franq = (marcas_franquiciadas / total_marcas) * 100 if total_marcas > 0 else 0
porc_no_franq = 100 - porc_franq

col1, col2, col3, col4 = st.columns(4)
col1.metric("Datos analizados", total_filas)
col2.metric("Variables analizadas", total_columnas)
col3.metric("Marcas con franquicia", f"{marcas_franquiciadas} ({porc_franq:.1f}%)")
col4.metric("Marcas sin franquicia", f"{marcas_no_franquiciadas} ({porc_no_franq:.1f}%)")

st.markdown("### Distribución de Marcas")
pie_df = pd.DataFrame({
    'Tipo': ['Marcas con franquicias', 'Marcas sin franquicias'],
    'Cantidad': [marcas_franquiciadas, marcas_no_franquiciadas]
})
fig_pie = px.pie(pie_df, names='Tipo', values='Cantidad', title='Distribución de marcas únicas')
fig_pie.update_layout(
    height=500,  # Podés ajustar a 600 o más si querés
    title_font_size=20,
    legend_font_size=14
)
st.plotly_chart(fig_pie, use_container_width=True)

# --- FILTROS ---
st.markdown("### Filtros")

tipo_cluster = st.radio("¿Qué tipo de negocios te gustaría analizar?", ['Franquiciados', 'No franquiciados'])
es_franquiciado = True if tipo_cluster == 'Franquiciados' else False

df_filtrado_tipo = df[df['es_franquiciado'] == es_franquiciado]

marcas_disponibles = (
    df_filtrado_tipo['title']
    .value_counts()
    .sort_values(ascending=False)
    .index
    .tolist()
)


marcas_seleccionadas = st.multiselect("Seleccioná una o más marcas", opciones := marcas_disponibles, default=[])
if marcas_seleccionadas:
    df_filtrado = df_filtrado_tipo[df_filtrado_tipo['title'].isin(marcas_seleccionadas)]
else:
    df_filtrado = df_filtrado_tipo.copy()

# --- FILTRO POR KEYWORD ---
keywords_disponibles = (
    df_filtrado['keyword']
    .dropna()
    .astype(str)
    .str.strip()
    .str.lower()
    .value_counts()
    .sort_values(ascending=False)
    .index
    .tolist()
)

keywords_seleccionadas = st.multiselect("Filtrar por una o más keywords", keywords_disponibles, default=[])
if keywords_seleccionadas:
    df_filtrado = df_filtrado[df_filtrado['keyword'].str.lower().str.strip().isin(keywords_seleccionadas)]


# --- SECCIÓN TOP 10 ---
st.markdown("### Top 10 negocios destacados")

if es_franquiciado:
    top_direcciones = (
        df_filtrado.groupby('title')
        .size()
        .reset_index(name='cantidad_direcciones')
        .sort_values(by='cantidad_direcciones', ascending=False)
        .head(10)
    )
    st.markdown("#### 🏪 Franquicias con más apariciones")
    top_direcciones.rename(columns={'title': 'Marca', 'cantidad_direcciones': 'Cantidad de apariciones'}, inplace=True)
    st.dataframe(top_direcciones, use_container_width=True)

else:
    if 'reviews' in df_filtrado.columns and 'stars' in df_filtrado.columns:
        df_temp = df_filtrado.copy()
        df_temp['reviews'] = pd.to_numeric(df_temp['reviews'], errors='coerce')
        df_temp['stars'] = pd.to_numeric(df_temp['stars'], errors='coerce')
        df_validos = df_temp.dropna(subset=['reviews', 'stars'])

        if not df_validos.empty:
            top_reviews = (
                df_validos.groupby('title')
                .agg({
                    'reviews': 'sum',
                    'stars': 'mean'
                })
                .reset_index()
                .sort_values(by=['reviews', 'stars'], ascending=[False, False])
                .head(10)
            )
            st.markdown("#### 🌟 Negocios no franquiciados con más reviews")
            top_reviews.rename(columns={'title': 'Marca'}, inplace=True)
            st.dataframe(top_reviews[['Marca', 'reviews', 'stars']], use_container_width=True)

        else:
            st.info("No hay datos válidos de 'reviews' y 'stars' para generar el ranking.")
    else:
        st.info("No existen columnas 'reviews' o 'stars' en el CSV.")

import plotly.graph_objects as go
from collections import Counter

st.markdown("### 🌞 Visualización jerárquica de keywords")

if 'keyword' in df_filtrado.columns and not df_filtrado.empty:
    if marcas_seleccionadas:  # Si hay marcas seleccionadas, mostrar keywords
        keywords = df_filtrado['keyword'].dropna().astype(str).str.strip().str.lower()
        top_keywords = Counter(keywords).most_common(10)

        if top_keywords:
            labels = [kw for kw, _ in top_keywords]
            values = [v for _, v in top_keywords]
            parents = [''] * len(labels)

            fig = go.Figure(go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                textinfo="label+value+percent entry",
                insidetextorientation='radial',
                hovertemplate='<b>%{label}</b><br>Frecuencia: %{value}<br>%{percentEntry:.1%}',
            ))
            fig.update_layout(
                title="Top 10 keywords más frecuentes",
                margin=dict(t=50, l=0, r=0, b=0),
                height=550,
                uniformtext=dict(minsize=12, mode='show')
            )
            st.plotly_chart(fig, use_container_width=True)

    elif keywords_seleccionadas:  # Si hay keywords pero no marcas, mostrar marcas como sunburst
        marcas = df_filtrado['title'].dropna().astype(str).str.strip().str.lower()
        top_marcas = Counter(marcas).most_common(10)

        if top_marcas:
            labels = [m for m, _ in top_marcas]
            values = [v for _, v in top_marcas]
            parents = [''] * len(labels)

            fig = go.Figure(go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                textinfo="label+value+percent entry",
                insidetextorientation='radial',
                hovertemplate='<b>%{label}</b><br>Frecuencia: %{value}<br>%{percentEntry:.1%}',
            ))
            fig.update_layout(
                title="Top 10 marcas asociadas a las keywords seleccionadas",
                margin=dict(t=50, l=0, r=0, b=0),
                height=550,
                uniformtext=dict(minsize=12, mode='show')
            )
            st.plotly_chart(fig, use_container_width=True)


# --- TABLA FINAL CON FILTROS APLICADOS ---
st.markdown("### 📋 Tabla final con todos los datos")

columnas_a_excluir = [
    'client', 'accountName', 'locationId', 'locationName',
    'locationCity', 'locationState', 'type', 'createdAt'
]
columnas_presentes = [col for col in columnas_a_excluir if col in df_filtrado.columns]

df_final = df_filtrado.drop_duplicates(subset=['addressPreview']).drop(columns=columnas_presentes, errors='ignore')


st.dataframe(df_final, use_container_width=True)

# Descargar CSV limpio
csv = df_final.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar tabla filtrada", csv, "franquicias_filtradas.csv", "text/csv")

# --- LOGOUT ---
st.markdown("---")
if st.button("🔓 Cerrar sesión"):
    st.session_state.clear()
    st.rerun()
