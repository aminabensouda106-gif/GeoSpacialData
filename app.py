"""
Analyse de pluviométrie (GPM IMERG, résolution 30 min) sur une zone dessinée à la main.

Lancement : streamlit run app.py
"""

import datetime as dt

import ee
import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# CONFIG — à adapter une seule fois
# ---------------------------------------------------------------------------
EE_PROJECT_ID = "ton-projet-google-cloud"   # <-- remplace par l'ID de ton projet GEE
IMERG_COLLECTION = "NASA/GPM_L3/IMERG_V07"  # imagerie satellite, pas de pluviomètres au sol
PRECIP_BAND = "precipitation"               # mm/h, moyenne sur la demi-heure
IMERG_SCALE_M = 11132                       # résolution native ~0.1° (~11 km)
DEFAULT_CENTER = [31.7, -7.0]               # Maroc, à ajuster si besoin
DEFAULT_ZOOM = 6
MAX_RANGE_DAYS = 60                         # garde-fou pour éviter un calcul trop long côté EE


# ---------------------------------------------------------------------------
# Connexion à Earth Engine (une seule fois par session)
# ---------------------------------------------------------------------------
@st.cache_resource
def init_ee():
    try:
        ee.Initialize(project=EE_PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=EE_PROJECT_ID)
    return True


# ---------------------------------------------------------------------------
# Requête Earth Engine : série temporelle de pluie moyenne sur le polygone
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_rainfall_timeseries(polygon_coords, start_date: str, end_date_exclusive: str):
    geometry = ee.Geometry.Polygon(polygon_coords)

    collection = (
        ee.ImageCollection(IMERG_COLLECTION)
        .filterDate(start_date, end_date_exclusive)
        .filterBounds(geometry)
        .select(PRECIP_BAND)
    )

    def reduce_image(img):
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=IMERG_SCALE_M,
            bestEffort=True,
            maxPixels=1e9,
        )
        return ee.Feature(
            None,
            {
                "time": img.date().format("YYYY-MM-dd HH:mm"),
                "precip_mm_h": stats.get(PRECIP_BAND),
            },
        )

    features = collection.map(reduce_image).getInfo()["features"]

    rows = [f["properties"] for f in features if f["properties"]["precip_mm_h"] is not None]
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    df["precip_mm_30min"] = df["precip_mm_h"] * 0.5  # taux horaire -> lame d'eau du pas de 30 min
    df["cumul_mm"] = df["precip_mm_30min"].cumsum()
    return df


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Analyse pluviométrie (IMERG 30 min)", layout="wide")
st.title("Analyse de pluviométrie sur zone dessinée — données 30 min (GPM IMERG)")

init_ee()

st.markdown(
    "1. **Dessine un polygone** sur la carte (outil polygone/rectangle à gauche de la carte).\n"
    "2. **Choisis les dates** de début et de fin.\n"
    "3. Clique sur **Lancer l'analyse**."
)

col_map, col_form = st.columns([2, 1])

with col_map:
    m = folium.Map(location=DEFAULT_CENTER, zoom_start=DEFAULT_ZOOM)
    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "polygon": True,
            "rectangle": True,
        },
        edit_options={"edit": True},
    ).add_to(m)
    map_state = st_folium(m, height=550, width=None, key="draw_map")

with col_form:
    end_date = st.date_input("Date de fin", value=dt.date.today())
    start_date = st.date_input("Date de début", value=end_date - dt.timedelta(days=7))
    run = st.button("Lancer l'analyse", type="primary")

# ---------------------------------------------------------------------------
# Extraction du polygone dessiné
# ---------------------------------------------------------------------------
polygon_coords = None
drawing = map_state.get("last_active_drawing") if map_state else None
if drawing and drawing.get("geometry", {}).get("type") in ("Polygon",):
    polygon_coords = drawing["geometry"]["coordinates"]

# ---------------------------------------------------------------------------
# Lancement de l'analyse
# ---------------------------------------------------------------------------
if run:
    if polygon_coords is None:
        st.warning("Aucun polygone détecté : dessine d'abord une zone sur la carte.")
    elif start_date >= end_date:
        st.warning("La date de début doit être antérieure à la date de fin.")
    elif (end_date - start_date).days > MAX_RANGE_DAYS:
        st.warning(f"Réduis la période à moins de {MAX_RANGE_DAYS} jours (calcul trop long sinon).")
    else:
        end_exclusive = end_date + dt.timedelta(days=1)  # borne EE exclusive -> inclut le jour de fin
        with st.spinner("Interrogation de Earth Engine (GPM IMERG)..."):
            df = get_rainfall_timeseries(
                polygon_coords,
                start_date.isoformat(),
                end_exclusive.isoformat(),
            )

        if df.empty:
            st.error("Aucune donnée récupérée. Vérifie la zone et la période (IMERG a quelques heures de latence).")
        else:
            total_mm = df["precip_mm_30min"].sum()
            max_intensity = df["precip_mm_h"].max()

            c1, c2, c3 = st.columns(3)
            c1.metric("Pluie cumulée", f"{total_mm:.1f} mm")
            c2.metric("Intensité max", f"{max_intensity:.1f} mm/h")
            c3.metric("Nombre de pas de 30 min", f"{len(df)}")

            fig1 = go.Figure()
            fig1.add_trace(go.Bar(x=df["time"], y=df["precip_mm_30min"], name="Pluie par pas de 30 min (mm)"))
            fig1.update_layout(title="Pluviométrie par pas de temps (30 min)", xaxis_title="Temps", yaxis_title="mm")
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df["time"], y=df["cumul_mm"], mode="lines", name="Cumul (mm)"))
            fig2.update_layout(title="Pluviométrie cumulée", xaxis_title="Temps", yaxis_title="mm cumulés")
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df, use_container_width=True)
            st.download_button(
                "Télécharger les données (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                file_name="pluviometrie_30min.csv",
                mime="text/csv",
            )
