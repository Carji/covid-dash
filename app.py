import datetime
from functools import reduce
from pkg_resources import normalize_path
import streamlit as st
import pandas as pd
import altair as alt
import os
 


#Poblaciones en 2021
habitantes = {'Germany': 83.78,
            'France': 65.27,
            'United Kingdom': 67.89,
            'Italy': 60.46,
            'Spain': 46.75,
            'Poland': 37.84,
            'Romania': 19.23,
            'Netherlands': 17.13,
            'Belgium': 11.59,
            'Greece': 10.42,
            'Sweden': 10.09, 
            'Switzerland': 8.65,
            'Austria': 9.06,
            'Norway': 5.41,
            'Denmark': 5.79,
            'Argentina': 45.20,
            'Australia': 25.50,
            'Bangladesh': 164.69,
            'Brazil': 212.56,
            'Canada': 37.74,
            'China': 1439.33,
            'Colombia': 50.88,
            'Egypt': 102.33,
            'Ethiopia': 114.96,
            'India': 1380.00,
            'Indonesia': 273.52,
            'Japan': 126.47,
            'Russia': 145.93,
            'Andorra': 0.077}



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
    st.set_page_config(page_title="Covid-19", page_icon=None, layout='centered', initial_sidebar_state='auto')
    st.title("Covid 19 Exploratory Data Analysis 🔬")
    st.markdown("""\
        
    """)


    countries = ["Germany", "Austria", "Belgium", "Denmark", "France", "Greece", "Italy", \
                 "Netherlands", "Norway", "Poland", "Romania", "Spain", "Sweden", \
                 "Switzerland", "United Kingdom","Andorra","Argentina","Australia","Bangladesh","Brazil","Canada","China", \
                 "Colombia","Egypt","Ethiopia","India","Indonesia","Japan","Russia",]

    analysis = st.sidebar.selectbox("Desplegable", ["Resumen global", "Por país"])

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
            color=alt.Color('country:N', title="País")
        )

        # case fatality rate...
        c3 = alt.Chart(frate.reset_index()).properties(height=100).mark_line().encode(
            x=alt.X("date:T", title="Fecha"),
            y=alt.Y("frate:Q", title="Tasa de mortalidad [%]", scale=alt.Scale(type='linear')),
            color=alt.Color('country:N', title="País")
        )

        per100k = confirmed.loc[[confirmed.index.max()]].copy()
        per100k.loc[:,'habitantes'] = per100k.apply(lambda x: habitantes[x['country']], axis=1)
        per100k.loc[:,'per100k'] = per100k.confirmed / (per100k.habitantes * 1_000_000) * 100_000
        per100k = per100k.set_index("country")
        per100k = per100k.sort_values(ascending=False, by='per100k')
        per100k.loc[:,'per100k'] = per100k.per100k.round(2)

        c4 = alt.Chart(per100k.reset_index()).properties(width=75).mark_bar().encode(
            x=alt.X("per100k:Q", title="Casos por 100000 habitantes"),
            y=alt.Y("country:N", title="Países", sort=None),
            color=alt.Color('country:N', title="Países"),
            tooltip=[alt.Tooltip('country:N', title='País'), 
                     alt.Tooltip('per100k:Q', title='Casos por 100000 habitantes'),
                     alt.Tooltip('habitantes:Q', title='Habitantes [10^6]')]
        )

        st.altair_chart(alt.hconcat(c4, alt.vconcat(c2, c3)), use_container_width=True)

        st.markdown(f"""\
            <div style="font-size: small">
            Poblaciones actualizadas a Febrero de 2021.
            </div><br/>  

            """, unsafe_allow_html=True)


    elif analysis == "Por país":        

        confirmed, deaths, recovered = read_data()

        st.header("Country statistics")
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
        normalize = selection if norm_sel == "Sí" else False
        
        confirmed = confirmed[confirmed["Country/Region"] == selection].iloc[:,3:]
        confirmed = transform(confirmed, collabel="confirmed", norm=normalize)

        deaths = deaths[deaths["Country/Region"] == selection].iloc[:,3:]
        deaths = transform(deaths, collabel="deaths", norm=normalize)

        recovered = recovered[recovered["Country/Region"] == selection].iloc[:,3:]
        recovered = transform(recovered, collabel="recovered", norm=normalize)

        
        df = reduce(lambda a,b: pd.merge(a,b, on='date'), [confirmed, recovered, deaths])
        df["active"] = df.confirmed - (df.deaths + df.recovered)

        variables = ["recovered", "active", "deaths"]
        colors = ["steelblue", "orange", "black"]

        value_vars = variables
        SCALE = alt.Scale(domain=variables, range=colors)
        if cummulative == 'new cases':
            value_vars = ["new"]
            df["new"] = df.confirmed - df.shift(1).confirmed
            df["new"].loc[df.new < 0]  = 0
            SCALE = alt.Scale(domain=["new"], range=["orange"]) 

        dfm = pd.melt(df.reset_index(), id_vars=["date"], value_vars=value_vars)

        # introduce order col as altair does auto-sort on stacked elements
        dfm['order'] = dfm['variable'].replace(
            {val: i for i, val in enumerate(variables[::-1])}
        )

        cases_label = "Casos" if normalize == False else "Casos por 100000 habitantes"

        c = alt.Chart(dfm.reset_index()).mark_bar().properties(height=200).encode(
            x=alt.X("date:T", title="Fecha"),
            y=alt.Y("sum(value):Q", title=cases_label, scale=alt.Scale(type='linear')),
            color=alt.Color('variable:N', title="Categoría", scale=SCALE), #, sort=alt.EncodingSortField('value', order='ascending')),
            order='order'
        )

        if cummulative != 'Nuevas notificaciones':
            st.altair_chart(c, use_container_width=True)
        else:
            # add smooth 7-day trend
            rm_7day = df[['new']].rolling('7D').mean().rename(columns={'new': 'value'})
            c_7day = alt.Chart(rm_7day.reset_index()).properties(height=200).mark_line(strokeDash=[1,1], color='red').encode(
                x=alt.X("date:T", title="Fecha"),
                y=alt.Y("value:Q", title=cases_label, scale=alt.Scale(type='linear')),
            )
            st.altair_chart((c + c_7day), use_container_width=True)
            st.markdown(f"""\
                <div style="font-size: small">Daily reported new cases (incl. 7-day average).</div><br/>
                """, unsafe_allow_html=True)


    st.info("""\
          
        Fuente de datos: [Johns Hopkins Univerity (GitHub)](https://github.com/CSSEGISandData/COVID-19). 
    """)


    # ----------------------








if __name__ == "__main__":
    main()
