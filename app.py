import datetime
from functools import reduce
from pkg_resources import normalize_path
import streamlit as st
import pydeck as pdk 
import pandas as pd
import altair as alt
import os
import matplotlib.pyplot as plt
import numpy as np

 


#Poblaciones en 2021 (actualizado el 15-Marzo)
habitantes = {
             'Andorra': 0.077, 
             'Argentina': 45.20,
             'Australia': 25.50,
             'Austria': 9.06,
             'Bangladesh': 164.69,
             'Belgium': 11.59,
             'Brazil': 212.56,
             'Canada': 37.74,
             'China': 1439.33,
             'Colombia': 50.88,
             'Denmark': 5.79,
             'Egypt': 102.33,
             'Ethiopia': 114.96,
             'France': 65.27,
             'Germany': 83.78,
             'Greece': 10.42,
             'India': 1380.00,
             'Indonesia': 273.52,
             'Italy': 60.46,
             'Japan': 126.47,
             'Netherlands': 17.13,
             'Norway': 5.41,
             'Poland': 37.84,
             'Romania': 19.23,
             'Russia': 145.93,
             'Spain': 46.75,
             'Sweden': 10.09, 
             'Switzerland': 8.65,
             'United Kingdom': 67.89}
 


@st.cache(ttl=60*60*1)
def read_data():
    BASEURL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series"    
    url_confirmed = f"{BASEURL}/time_series_covid19_confirmed_global.csv"
    url_deaths = f"{BASEURL}/time_series_covid19_deaths_global.csv"
    url_recovered = f"{BASEURL}/time_series_covid19_recovered_global.csv"

    confirmed = pd.read_csv(url_confirmed, index_col=0)
    deaths = pd.read_csv(url_deaths, index_col=0)
    recovered = pd.read_csv(url_recovered, index_col=0)

    # sum over potentially duplicate rows (France and their territories)
    confirmed = confirmed.groupby("Country/Region").sum().reset_index()
    deaths = deaths.groupby("Country/Region").sum().reset_index()
    recovered = recovered.groupby("Country/Region").sum().reset_index()


    return (confirmed, deaths, recovered)

def transform(df, collabel='confirmed', norm=False):
    dfm = pd.melt(df)
    dfm["date"] = pd.to_datetime(dfm.variable, infer_datetime_format=True)
    dfm = dfm.set_index("date")
    dfm = dfm[["value"]]
    dfm.columns = [collabel]
    if norm:
        dfm[[collabel]] = dfm[[collabel]] / (habitantes[norm]* 1_000_000) * 100_000
    return dfm

def transform2(df, collabel='confirmed'):
    dfm = pd.melt(df, id_vars=["Country/Region"])
    dfm["date"] = pd.to_datetime(dfm.variable, infer_datetime_format=True)
    dfm = dfm.set_index("date")
    dfm = dfm[["Country/Region","value"]]
    dfm.columns = ["country", collabel]
    return dfm

def main():
    st.set_page_config(page_title="Breve dash autoactualizable para el Covid-19", page_icon=None, layout='centered', initial_sidebar_state='auto')
    st.title("Dash autoactualizable para el Covid-19 🔬")
    st.markdown("""\
        
    """)


    countries = ["Andorra", "Argentina", "Australia","Austria","Bangladesh","Belgium","Brazil","Canada","China","Colombia", \
             "Denmark","Egypt","Ethiopia","France","Germany","Greece","India","Indonesia","Italy","Japan","Netherlands", \
             "Norway","Poland","Romania","Russia","Spain","Sweden","Switzerland","United Kingdom",]

    analysis = st.sidebar.selectbox("Desplegable", ["Por fecha","Por país","Resumen global"])

    if analysis == "Resumen global":

        st.header("Mortalidad y casos de Covid-19 en diversos países")
        st.markdown("""\
            Casos de Covid-19 en los países seleccionados"""
            f""" (Lista completa: {', '.join(countries)}). 
            """

            """
            💡 Puedes añadir/quitar países y escoger escala logarítmica.
            """)

        confirmed, deaths, recovered = read_data()

        multiselection = st.multiselect("Añade/quita países:", countries, default=countries)
        logscale = st.checkbox("Escala logarítmica", False)

        confirmed = confirmed[confirmed["Country/Region"].isin(multiselection)]
        confirmed = confirmed.drop(["Lat", "Long"],axis=1)
        confirmed = transform2(confirmed, collabel="confirmed")

        deaths = deaths[deaths["Country/Region"].isin(multiselection)]
        deaths = deaths.drop(["Lat", "Long"],axis=1)
        deaths = transform2(deaths, collabel="deaths")

        frate = confirmed[["country"]]
        frate["frate"] = (deaths.deaths / confirmed.confirmed)*100

        # saveguard for empty selection 
        if len(multiselection) == 0:
            return 

        SCALE = alt.Scale(type='linear')
        if logscale:
            confirmed["confirmed"] += 0.00001

            confirmed = confirmed[confirmed.index > '2020-02-16']
            frate = frate[frate.index > '2020-02-16']
            
            SCALE = alt.Scale(type='log', domain=[10, int(max(confirmed.confirmed))], clamp=True)


        c2 = alt.Chart(confirmed.reset_index()).properties(height=150).mark_line().encode(
            x=alt.X("date:T", title="Fecha"),
            y=alt.Y("confirmed:Q", title="Número de casos", scale=SCALE),
            color=alt.Color('country:N', title="País",scale=alt.Scale(scheme='tableau20'))
        ).interactive()

        # case fatality rate...
        c3 = alt.Chart(frate.reset_index()).properties(height=100).mark_line().encode(
            x=alt.X("date:T", title="Fecha"),
            y=alt.Y("frate:Q", title="Tasa de mortalidad [%]", scale=alt.Scale(type='linear')),
            color=alt.Color('country:N', title="País")
        ).interactive()

        per100k = confirmed.loc[[confirmed.index.max()]].copy()
        per100k.loc[:,'habitantes'] = per100k.apply(lambda x: habitantes[x['country']], axis=1)
        per100k.loc[:,'per100k'] = per100k.confirmed / (per100k.habitantes * 1_000_000) * 100_000
        per100k = per100k.set_index("country")
        per100k = per100k.sort_values(ascending=False, by='per100k')
        per100k.loc[:,'per100k'] = per100k.per100k.round(2)

        c4 = alt.Chart(per100k.reset_index()).properties(width=75).mark_bar().encode(
            x=alt.X("per100k:Q", title="Casos por 100000 habitantes"),
            y=alt.Y("country:N", title="Países", sort=None),
            color=alt.Color('country:N', title="Países",scale=alt.Scale(scheme='tableau20')),
            tooltip=[alt.Tooltip('country:N', title='País'), 
                     alt.Tooltip('per100k:Q', title='Casos por 100000 habitantes'),
                     alt.Tooltip('habitantes:Q', title='Habitantes [10^6]')]
        ).interactive()

        st.altair_chart(alt.hconcat(c4, alt.vconcat(c2, c3)), use_container_width=True)

        st.markdown(f"""\
            <div style="font-size: small">
            Poblaciones actualizadas a Febrero de 2021.
            </div><br/>  

            """, unsafe_allow_html=True)


    elif analysis == "Por país":        

        confirmed, deaths, recovered = read_data()

        st.header("Estadísticas individuales")
        st.markdown("""\
            Estadísticas desglosadas por país """
            f""" (actualmente sólo {', '.join(countries)}).  
            """
            """  
            💡 Puedes seleccionar casos totales o nuevos casos diarios.
            Normalizar indica los casos por cada 100000 habitantes. 
            """)

        # selections
        col1, col2, col3, _, _ = st.beta_columns(5)

        selection = col1.selectbox("Selecciona un país:", countries)
        cummulative = col2.radio("Conteo:", ["Casos totales", "Nuevas notificaciones"])
        norm_sel = col3.radio("Normalizar:", ["No", "Sí"])
        normalizar = selection if norm_sel == "Sí" else False
        
        confirmed = confirmed[confirmed["Country/Region"] == selection].iloc[:,3:]
        confirmed = transform(confirmed, collabel="confirmed", norm=normalizar)

        deaths = deaths[deaths["Country/Region"] == selection].iloc[:,3:]
        deaths = transform(deaths, collabel="deaths", norm=normalizar)

        recovered = recovered[recovered["Country/Region"] == selection].iloc[:,3:]
        recovered = transform(recovered, collabel="recovered", norm=normalizar)

        
        df = reduce(lambda a,b: pd.merge(a,b, on='date'), [confirmed, recovered, deaths])
        df["active"] = df.confirmed - (df.deaths + df.recovered)

        variables = ["recovered", "active", "deaths"]
        colors = ["green", "blue", "red"]

        value_vars = variables
        SCALE = alt.Scale(domain=variables, range=colors)
        if cummulative == 'Nuevas notificaciones':
            value_vars = ["new"]
            df["new"] = df.confirmed - df.shift(1).confirmed
            df["new"].loc[df.new < 0]  = 0
            SCALE = alt.Scale(domain=["new"], range=["blue"]) 

        dfm = pd.melt(df.reset_index(), id_vars=["date"], value_vars=value_vars)

        # introduce order col as altair does auto-sort on stacked elements
        dfm['order'] = dfm['variable'].replace(
            {val: i for i, val in enumerate(variables[::-1])}
        )

        cases_label = "Casos" if normalizar == False else "Casos por 100000 habitantes"

        c = alt.Chart(dfm.reset_index()).mark_bar().properties(height=300).encode(
            x=alt.X("date:T", title="Fecha"),
            y=alt.Y("sum(value):Q", title=cases_label, scale=alt.Scale(type='linear')),
            color=alt.Color('variable:N', title="Categoría", scale=SCALE),#, sort=alt.EncodingSortField('value', order='ascending')),
            order='order'
        ).interactive()

        if cummulative != 'Nuevas notificaciones':
            st.altair_chart(c, use_container_width=True)
        else:
            # media semanal (falta añadir IA14d)
            rm_7day = df[['new']].rolling('7D').mean().rename(columns={'new': 'value'})
            c_7day = alt.Chart(rm_7day.reset_index()).properties(height=300).mark_line(strokeDash=[1,1], color='red').encode(
                x=alt.X("date:T", title="Fecha"),
                y=alt.Y("value:Q", title=cases_label, scale=alt.Scale(type='linear')),
            )
            st.altair_chart((c + c_7day), use_container_width=True)
            st.markdown(f"""\
                <div style="font-size: small">Nuevos casos diarios (incluyendo media semanal).</div><br/>
                """, unsafe_allow_html=True)
#ToDo List:
#añadir plots de matplotlib, bokeh, desglosar por comunidades (faltaría el csv anidado)

#    arr = np.random.normal(1, 1, size=100)
#    fig, ax = plt.subplots()
#    ax.hist(arr, bins=20)
#    
#    st.pyplot(fig)
#    st.info("""\

    elif analysis == "Por fecha":        
              
              
              
## MAP

# Variable for date picker, default to Jan 1st 2020
        date = datetime.date(2020,1,1)
# Set viewport for the deckgl map
        view = pdk.ViewState(latitude=0, longitude=0, zoom=0.2,)
# Create the scatter plot layer
        covidLayer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                pickable=False,
                opacity=0.3,
                stroked=True,
                filled=True,
                radius_scale=10,
                radius_min_pixels=5,
                radius_max_pixels=60,
                line_width_min_pixels=1,
                get_position=["Longitude", "Latitude"],
                get_radius=metric_to_show_in_covid_Layer,
                get_fill_color=[252, 136, 3],
                get_line_color=[255,0,0],
                tooltip="test test",
            )

# Create the deck.gl map
        r = pdk.Deck(
            layers=[covidLayer],
            initial_view_state=view,
            map_style="mapbox://styles/mapbox/light-v10",
)
# Create a subheading to display current date
        subheading = st.subheader("")
# Render the deck.gl map in the Streamlit app as a Pydeck chart 
        map = st.pydeck_chart(r)
# Update the maps and the subheading each day for 90 days
        for i in range(0, 120, 1):
    # Increment day by 1
            date += datetime.timedelta(days=1)
    # Update data in map layers
            covidLayer.data = df[df['date'] == date.isoformat()]
    # Update the deck.gl map
            r.update()
    # Render the map
            map.pydeck_chart(r)
    # Update the heading with current date
            subheading.subheader("%s on : %s" % (metric_to_show_in_covid_Layer, date.strftime("%B %d, %Y")))
    
# wait 0.1 second before go onto next day
            time.sleep(0.05)              
              
              
              
              
              
              
              
              
              
              
        st.info("""    
        Fuente de datos: [Johns Hopkins Univerity (GitHub)](https://github.com/CSSEGISandData/COVID-19). 
    """)


    # ----------------------








if __name__ == "__main__":
    main()
