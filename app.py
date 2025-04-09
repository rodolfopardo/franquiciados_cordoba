import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Observatorio de Franquicias – Córdoba", layout="wide")

# --- LOGIN SIMPLE ---
def login():
    st.image("search.mas-logo-blanco.png", width=200)  # Logo arriba
    st.title("🔐 Observatorio de Franquicias – Córdoba")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        if user == "jp" and password == "1234":
            st.session_state['logged_in'] = True
            st.experimental_rerun()
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
st.markdown("### 🧮 Panel General")

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
st.plotly_chart(fig_pie, use_container_width=True)

# --- FILTROS ---
st.markdown("###vFiltros")

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


marca_seleccionada = st.selectbox("Seleccioná una marca", ["Todas"] + marcas_disponibles)
if marca_seleccionada != "Todas":
    df_filtrado = df_filtrado_tipo[df_filtrado_tipo['title'] == marca_seleccionada]
else:
    df_filtrado = df_filtrado_tipo.copy()

# --- SECCIÓN TOP 10 ---
st.markdown("### 🏆 Top 10 negocios destacados")

if es_franquiciado:
    top_direcciones = (
        df_filtrado.groupby('title')
        .size()
        .reset_index(name='cantidad_direcciones')
        .sort_values(by='cantidad_direcciones', ascending=False)
        .head(10)
    )
    st.markdown("#### 🏪 Franquicias con más direcciones")
    st.dataframe(top_direcciones[['title', 'cantidad_direcciones']], use_container_width=True)

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
            st.dataframe(top_reviews[['title', 'reviews', 'stars']], use_container_width=True)
        else:
            st.info("No hay datos válidos de 'reviews' y 'stars' para generar el ranking.")
    else:
        st.info("No existen columnas 'reviews' o 'stars' en el CSV.")

import plotly.graph_objects as go
from collections import Counter

st.markdown("### 🌞 Visualización jerárquica de keywords (Sunburst optimizado)")

if 'keyword' in df_filtrado.columns:
    keywords = df_filtrado['keyword'].dropna().astype(str).str.strip().str.lower()
    top_keywords = Counter(keywords).most_common(10)
    
    if top_keywords:
        labels = [kw for kw, _ in top_keywords]
        values = [v for _, v in top_keywords]
        parents = [''] * len(labels)  # Raíz vacía

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



# --- TABLA FINAL CON FILTROS APLICADOS ---
st.markdown("### 📋 Tabla final con todos los datos")
st.dataframe(df_filtrado, use_container_width=True)
csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar tabla filtrada", csv, "franquicias_filtradas.csv", "text/csv")

# --- LOGOUT ---
st.markdown("---")
if st.button("🔓 Cerrar sesión"):
    st.session_state.clear()
    st.experimental_rerun()
