import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------
# Chargement DATA PRINCIPALE
# --------------------------------------------

@st.cache_data
def load_main_data():
    df_raw = pd.read_csv("data_ratp.csv", header=None, dtype=str)

    header_line = df_raw.iloc[0, 0].split(";")
    df = df_raw.iloc[1:].copy()
    df = df[0].str.split(";", expand=True)
    df.columns = header_line

    df.columns = (
        df.columns.str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace("é", "e")
        .str.replace("è", "e")
        .str.replace("ê", "e")
        .str.replace("à", "a")
    )

    df["trafic"] = pd.to_numeric(df["trafic"], errors="coerce")
    df["rang"] = pd.to_numeric(df["rang"], errors="coerce")

    cols_corr = [c for c in df.columns if "correspondance" in c]
    df[cols_corr] = df[cols_corr].fillna("Aucune").replace("", "Aucune").astype(str)

    df["arrondissement_pour_paris"] = (
        df["arrondissement_pour_paris"]
        .replace("", None)
        .astype(float)
    )

    df["nb_corr"] = df[cols_corr].apply(lambda r: sum(v != "Aucune" for v in r), axis=1)

    return df


# --------------------------------------------
# Chargement DES COORDONNÉES (pré-géocodées)
# --------------------------------------------

@st.cache_data
def load_geocoded():
    df_geo = pd.read_csv("stations_geocode.csv")
    return df_geo


df = load_main_data()
df_geo = load_geocoded()

# --------------------------------------------
# SIDEBAR (Navigation + filtre réseau global)
# --------------------------------------------

st.sidebar.title("📌 Menu & Filtres")
st.sidebar.markdown("**Dataset : Trafic annuel RATP — 2020**")

page = st.sidebar.radio(
    "Navigation",
    ["📊 Chiffres clés", "🏙️ Détail par arrondissement", "🗺️ Carte interactive"]
)

reseaux = sorted(df["reseau"].dropna().unique())
reseau_sel = st.sidebar.selectbox("Sélectionner un réseau", reseaux)

df_global = df[df["reseau"] == reseau_sel]

# --------------------------------------------
# PAGE 1 — CHIFFRES CLÉS
# --------------------------------------------

if page == "📊 Chiffres clés":

    st.title("🚇 Dashboard RATP — Trafic annuel 2020")
    st.subheader(f"📊 Chiffres clés — Réseau : {reseau_sel}")

    trafic_total = df_global["trafic"].sum()
    nb_stations = df_global["station"].nunique()
    station_max = df_global.loc[df_global["trafic"].idxmax(), "station"]
    trafic_moyen = int(df_global["trafic"].mean())

    # KPIs stylées
    k1, k2, k3, k4 = st.columns([1.3, 1, 1.5, 1])

# 👉 KPIs custom avec taille réduite
    def kpi_small(label, value):
        st.markdown(
            f"""
            <div style="text-align:center;">
                <div style="font-size:16px; color:#003A70; font-weight:600;">{label}</div>
                <div style="font-size:24px; color:#000000; font-weight:700; margin-top:4px;">
                    {value}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    k1, k2, k3, k4 = st.columns([1.3, 1, 1.5, 1])

    with k1:
        kpi_small("Trafic total", f"{trafic_total:,.0f}".replace(",", " "))

    with k2:
        kpi_small("Nombre de stations", nb_stations)

    with k3:
        kpi_small("Station la plus fréquentée", station_max.title())

    with k4:
        kpi_small("Trafic moyen / station", f"{trafic_moyen:,.0f}".replace(",", " "))


    st.markdown("---")

    # Pie chart
    st.write("### 🍩 Répartition du trafic — Métro vs RER")
    df_pie = df.groupby("reseau")["trafic"].sum().reset_index()

    fig_pie = px.pie(
        df_pie,
        names="reseau",
        values="trafic",
        color="reseau",
        color_discrete_map={"Metro": "#009B77", "Métro": "#009B77", "RER": "#003A70"},
        title="Répartition du trafic — 2020"
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Top 10 des correspondances
    st.write("### 🔝 Top 10 des stations avec le plus de correspondances")

    df_top_corr = df.sort_values("nb_corr", ascending=False).head(10)

    fig_corr = px.bar(
        df_top_corr,
        x="station",
        y="nb_corr",
        color="nb_corr",
        title="Top 10 — Nombre de correspondances"
    )

    st.plotly_chart(fig_corr, use_container_width=True)


# --------------------------------------------
# PAGE 2 — ARRONDISSEMENTS
# --------------------------------------------

elif page == "🏙️ Détail par arrondissement":

    st.title("🏙️ Détail par arrondissement — 2020")

    colA, colB = st.columns(2)

    # ⚡ Récupération des arrondissements sans virgule
    arr_valids = sorted(
        [int(a) for a in df["arrondissement_pour_paris"].dropna().unique()]
    )

    # ⚡ Construction propre de la liste d'affichage
    arr_display = ["Tous"] + [str(a) for a in arr_valids] + ["Non renseigné"]

    # ⚡ Selectbox
    with colA:
        arr_sel = st.selectbox("Arrondissement", arr_display)


    with colB:
        reseau_sel_2 = st.selectbox("Réseau", reseaux, index=reseaux.index(reseau_sel))

    df_arr = df.copy()

    if arr_sel not in ["Tous", "Non renseigné"]:
        df_arr = df_arr[df_arr["arrondissement_pour_paris"] == int(arr_sel)]
    elif arr_sel == "Non renseigné":
        df_arr = df_arr[df_arr["arrondissement_pour_paris"].isna()]

    df_arr = df_arr[df_arr["reseau"] == reseau_sel_2]

    st.write(f"### Nombre de stations trouvées : **{len(df_arr)}**")
    st.dataframe(df_arr)


# --------------------------------------------
# PAGE 3 — CARTE INTERACTIVE (toutes stations)
# --------------------------------------------

elif page == "🗺️ Carte interactive":

    st.title("🗺️ Carte interactive — Toutes stations RATP (2020)")

    df_map = df_geo.dropna(subset=["lat", "lon"])

    color_map = {
        "Metro": "#008000",
        "Métro": "#008000",
        "RER": "#0000CC"
    }

    # ❗ PAS de parameter size dans px.scatter_mapbox
    fig_map = px.scatter_mapbox(
        df_map,
        lat="lat",
        lon="lon",
        hover_name="station",
        hover_data=["reseau", "trafic", "nb_corr"],
        color="reseau",
        zoom=11,
        height=650,
        color_discrete_map=color_map
    )

    # 👉 Taille réellement forcée ici
    fig_map.update_traces(marker=dict(size=8))   # ← Ajuste ici (3 / 4 / 5)

    fig_map.update_layout(mapbox_style="open-street-map")
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    st.plotly_chart(fig_map, use_container_width=True)



