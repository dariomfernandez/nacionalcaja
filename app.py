import datetime
import locale
import pandas as pd  # pip install pandas openpyxl
import plotly.express as px  # pip install plotly-express
import streamlit as st  # pip install streamlit
#import mysql.connector as connection
import mariadb
#import mysql.connector

# emojis: https://www.webfx.com/tools/emoji-cheat-sheet/
st.set_page_config(page_title="Movimientos de caja", page_icon=":moneybag:", layout="wide")

locale.setlocale(locale.LC_MONETARY, 'es_AR')

gclougfuncurl = "https://southamerica-east1-nacionalgestion-366711.cloudfunctions.net/nacional"

#nacionalDatabase = "vinasdealtura"

# Obtener datos desde la db de Nacional
def get_data_from_mysql():
    result_dataFrame = None
    mydb = None
    try:
        #print("Paso 1")
        #st.write("Paso 1")
        #mydb = mariadb.connect(host=st.secrets["db_server"], database = st.secrets["db_name"], port=3306, user=st.secrets["db_username"], password=st.secrets["db_password"])
        #mydb = mysql.connector.connect(host=st.secrets["db_server"], database = st.secrets["db_name"], port=3306, user=st.secrets["db_username"], password=st.secrets["db_password"])
        #st.write("Paso 2")
        #print("Paso 2")
        query = f"SELECT movimiento, numero, IF(flujo='ENTRADA', 1, -1)*importe AS importe, flujo, modalidad, caja, DATE(t2fecha) AS t2fecha FROM {nacionalDatabase}.fnd_movimiento_flujo AS t1 INNER JOIN (SELECT movimiento AS t2movim, numero AS t2num, fecha AS t2fecha FROM {nacionalDatabase}.fnd_movimiento) AS t2 ON CONCAT(t1.movimiento, t1.numero)=CONCAT(t2.t2movim, t2.t2num) UNION SELECT 'COBRO', cobro, importe, 'ENTRADA', modalidad, caja, DATE(t2fecha) AS t2fecha FROM {nacionalDatabase}.vta_cobro_medio AS t1 INNER JOIN (SELECT numero AS t2num, fecha AS t2fecha FROM {nacionalDatabase}.vta_cobro) AS t2 ON t1.cobro=t2.t2num UNION SELECT 'PAGO' AS movimiento, pago, -importe AS importe, 'SALIDA', modalidad, caja, DATE(t2fecha) AS t2fecha FROM {nacionalDatabase}.cmp_pago_medio AS t1 INNER JOIN (SELECT numero, DATE(fecha) AS t2fecha FROM {nacionalDatabase}.cmp_pago) AS t2 ON t1.pago=t2.numero;"
        #st.write("Paso 3")
        #print("Paso 3")
        #result_dataFrame = pd.read_sql(query, mydb, parse_dates={"t2fecha": {"format": "%d/%m/%y"}})
        result_dataFrame = pd.read_json(gclougfuncurl + "?stmt=" + urllib.parse.quote(query))
        result_dataFrame['t2fecha']= pd.to_datetime(result_dataFrame['t2fecha'])
        #print("DataFrame crudo:\r\n", result_dataFrame.head())
        #print("Paso 4")
    except Exception as e:
        st.write("EXCEPCION: " + str(e))
        print("EXCEPCION: " + str(e))
    mydb.close() #close the connection
    return(result_dataFrame)

df = get_data_from_mysql()

# ---- SIDEBAR ----
st.sidebar.header("Filtros:")

fechaDesde = st.sidebar.date_input(
    "Desde:",
    value=df["t2fecha"].min(),
)

fechaHasta = st.sidebar.date_input(
    "Hasta:",
    value=df["t2fecha"].max(),
)

tipoFlujo = st.sidebar.multiselect(
    "Tipo de flujo:",
    options=df.query("flujo!=''")["flujo"].unique(),
    default=df.query("flujo!=''")["flujo"].unique()
)

tipoCaja = st.sidebar.multiselect(
    "Caja:",
    options=df.query("caja.notnull()")["caja"].unique(),
    default=df.query("caja.notnull()")["caja"].unique(),
)

tipoComprobante = st.sidebar.multiselect(
    "Comprobante:",
    options=df["movimiento"].unique(),
    default=df["movimiento"].unique(),
)

df_selection = df.query(
    "flujo==@tipoFlujo & movimiento==@tipoComprobante & caja==@tipoCaja & caja.notnull() & modalidad=='CAJA' & t2fecha>=@fechaDesde & t2fecha<=@fechaHasta"
)
df.style.format({"t2fecha": lambda t: t.strftime("%d/%m/%Y")})
df_selection.sort_values(by='t2fecha', ascending=False)
df_saldoant = df.query(
    "flujo==@tipoFlujo & movimiento==@tipoComprobante & caja==@tipoCaja & caja.notnull() & modalidad=='CAJA' & t2fecha<@fechaDesde"
)
#print("Saldo anterior:\r\n", df_saldoant)

# ---- MAINPAGE ----
st.header(":moneybag: Movimientos de caja")
#st.markdown("##")

# TOP KPI's
saldoAnterior = float(df_saldoant["importe"].sum())
importeTotal = float(df_selection["importe"].sum())
importeIngresos = float(df_selection.query("importe>0")["importe"].sum())
importeEgresos = abs(float(df_selection.query("importe<0")["importe"].sum()))
left_column, middle_column, right_column = st.columns(3)
with left_column:
    st.subheader("Neto:")
    st.subheader(locale.currency(importeTotal, grouping=True))
with middle_column:
    st.subheader("Ingresos:")
    st.subheader(locale.currency(importeIngresos, grouping=True))
with right_column:
    st.subheader("Egresos:")
    st.subheader(locale.currency(importeEgresos, grouping=True))

#st.markdown("""---""")
df_selection.sort_values(by='t2fecha', ascending=True, inplace=True)
saldoAcumulado = []
importeSaldo = saldoAnterior
for index, row in df_selection.iterrows():
    importeSaldo = importeSaldo + row['importe']
    saldoAcumulado.append(importeSaldo)
df_selection['saldo'] = saldoAcumulado
df_selection['importe'] = df_selection['importe'].map('{:,.2f}'.format)
df_selection['saldo'] = df_selection['saldo'].map('{:,.2f}'.format)
df_selection['t2fecha'] = df_selection['t2fecha'].map('{:%d/%m/%Y}'.format)
df_selection.columns = ['Movimiento', 'Número', 'Importe', 'Flujo', 'Modalidad', 'Caja', 'Fecha', 'Saldo']
# Ocultar columna índice
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """
st.markdown(hide_table_row_index, unsafe_allow_html=True)
st.info("Saldo anterior: " + locale.currency(saldoAnterior, grouping=True))
st.table(df_selection[['Fecha', 'Movimiento', 'Número', 'Caja', 'Importe', 'Saldo']])

# ---- HIDE STREAMLIT STYLE ----
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
