import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pygsheets
import os
from babel.numbers import format_currency

credenciais = pygsheets.authorize(service_account_file=os.getcwd()+'/cred.json')
planacomp = 'https://docs.google.com/spreadsheets/d/1ryCqPUMlhyJWI3DTr1xd7Hn5qVPm5Pg-Wm8kWUrA-Kw/'
status = credenciais.open_by_url(planacomp)

def formato_moeda(value):
    return f"{format_currency(value, 'BRL', locale='pt_BR')}"

# Função para transformar os valores das colunas
def clean_column(col):
    col = col.str.replace(' ', '')
    col = col.str.replace('[^0-9,]', '', regex=True)
    col = col.str.replace(',', '.')
    col = pd.to_numeric(col)
    return col

# Função para procurar um valor no DataFrame
def lookup_value(dataframe, lookup_column, lookup_value, return_column):
    try:
        result = dataframe[dataframe[lookup_column] == lookup_value][return_column].values[0]
        return result
    except IndexError:
        return "VALOR NÃO ENCONTRADO. Certifique se o primeiro dígito é uma letra maiúscula ou se os seis números estão corretos"
    
st.set_page_config(page_title='ACOMPANHAMENTO',layout='wide')

tema = st.sidebar.selectbox('Selecione o painel:',['DEMANDAS','TRANSPORTE','CUSTOS'])

aba1 = status.worksheet_by_title('DASHBOARD')
plmp = aba1.get_all_values()
demandas = pd.DataFrame(plmp)
demandas.columns = demandas.iloc[0]
demandas = demandas[1:]
demandas = demandas[demandas['PRIORIDADE']!='']
columns_to_clean = ['DIAS'] # Lista das colunas a transformar
for col in columns_to_clean:
    demandas[col] = clean_column(demandas[col])

aba2 = status.worksheet_by_title('RESUMODESLOC')
pltr = aba2.get_all_values()
transporte = pd.DataFrame(pltr)
transporte.columns = transporte.iloc[0]
transporte = transporte[1:]
transporte = transporte[transporte['DESTINO']!='']
columns_to_clean = ['FINAL'] # Lista das colunas a transformar
for col in columns_to_clean:
    transporte[col] = clean_column(transporte[col])

aba3 = status.worksheet_by_title('PAGAMENTOS')
plpg = aba3.get_all_values()
pagamentos = pd.DataFrame(plpg)
pagamentos.columns = pagamentos.iloc[0]
pagamentos = pagamentos[1:]
pagamentos = pagamentos.loc[pagamentos['ANO']!='']
columns_to_clean = ['VALOR','VALOR FATURADO'] # Lista das colunas a transformar
for col in columns_to_clean:
    pagamentos[col] = clean_column(pagamentos[col])

aba4 = status.worksheet_by_title('EMPENHOS')
plep = aba4.get_all_values()
empenhos = pd.DataFrame(plep)
empenhos.columns = empenhos.iloc[0]
empenhos = empenhos[1:]
empenhos = empenhos[empenhos['EMPENHO']!='']
columns_to_clean = ['RP','MANUTENÇÃO','ADAPTAÇÃO','SALDO RP','SALDO MP','SALDO ADP'] # Lista das colunas a transformar
for col in columns_to_clean:
    empenhos[col] = clean_column(empenhos[col])

aba5 = status.worksheet_by_title('CUSTOS')
plct = aba5.get_all_values()
custos = pd.DataFrame(plct)
custos.columns = custos.iloc[0]
custos = custos[1:]
custos = custos[custos['OS']!='']
columns_to_clean = ['CUSTO','M.O.','TOTAL'] # Lista das colunas a transformar
for col in columns_to_clean:
    custos[col] = clean_column(custos[col])

if tema == 'DEMANDAS':
    anos = demandas['ANO'].unique()
    maxano = max(anos)
    ano = st.sidebar.radio('Ano:',options=anos, index=list(anos).index(maxano),horizontal=True,label_visibility='collapsed')
    demandas = demandas.loc[demandas['ANO']==ano]

    st.subheader('Painel de demandas',divider='rainbow')
        
    cc1,cc2,cc3 = st.columns([0.15,0.15,0.7])

    situacao = cc1.radio('Status',['PENDENTES','ENCERRADAS'],label_visibility='collapsed')
    if situacao == 'PENDENTES':
        demandas = demandas.loc[demandas['STATUS']!='ENCERRADO']
    if situacao == 'ENCERRADAS':
        demandas = demandas.loc[demandas['STATUS']=='ENCERRADO']   

    dia = cc3.slider('Dias:',0,demandas['DIAS'].max())

    painel = demandas.loc[demandas['DIAS']>=dia].sort_values(by=['PRIORIDADE', 'DIAS'], ascending=[True, False])
    painel = painel[['PRIORIDADE','OS','CAMPUS','SETOR','SERVIÇO','STATUS','DIAS','MÊS','DETALHAMENTO','CONTROLE']]
    with cc2.container():
        st.metric('DEMANDAS:',painel['PRIORIDADE'].count())
    
    '-----'
    # Contar as ocorrências de cada item na coluna 'CAMPUS'
    campus_counts = painel['CAMPUS'].value_counts().sort_index()

    # Criar colunas para cada item único na coluna 'CAMPUS'
    columns = st.columns(len(campus_counts))
    # Exibir métricas horizontalmente
    for i, (campus, count) in enumerate(campus_counts.items()):
        with columns[i]:
            st.metric(label=f"Total de {campus}", value=count)

    c1,c2 = st.columns(2)
    with c1:
        painel
    with c2:
        busca = st.text_input('Digite o número da OS para consultar o DETALHAMENTO:')
    with c2:
        if busca:
            resultado = lookup_value(painel, 'OS', busca, 'DETALHAMENTO')  # Alterar 'idade' para a coluna desejada
            st.write(resultado)

    gd = painel.groupby(['CAMPUS','SERVIÇO']).count().reset_index()
    
    # Transformar os dados para o formato desejado
    df_pivot = gd.pivot_table(index='CAMPUS', columns='SERVIÇO', values='OS', aggfunc='sum', fill_value=0).reset_index()
    # Calcular a porcentagem para cada serviço em cada campus
    df_pivot_pct = df_pivot.set_index('CAMPUS').apply(lambda x: x / x.sum(), axis=1).reset_index()
    # Criar o gráfico de barras empilhadas tipo 100%
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, servico in enumerate(df_pivot_pct.columns[1:]):
        fig.add_trace(go.Bar(
            y=df_pivot_pct['CAMPUS'],x=df_pivot_pct[servico],name=servico,orientation='h',marker_color=colors[i],
            text=df_pivot[servico],textposition='inside',insidetextanchor='middle'))        
    fig.update_layout(
        title=f'DEMANDAS POR CAMPUS ({situacao})',barmode='stack')
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='white')
    fig

    dm = painel.groupby(['MÊS','CONTROLE']).count().reset_index().sort_values('CONTROLE')
    fig = px.line(dm,x=['MÊS'],y='OS',text='OS',title=f'HISTÓRICO MENSAL ({situacao})',width=1000,height=500)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black',tickfont_size=15)
    fig.update_layout(legend=dict(title=None, orientation='h',x=0.3),showlegend=False)
    fig.update_traces(textfont_size=15,textfont_color='black',textposition='top left')
    fig
    
    dt = painel.groupby(['SERVIÇO']).count().reset_index().sort_values('OS',ascending=False)
    fig = px.bar(dt,x='SERVIÇO',y='OS',color='SERVIÇO',title=f'CONTAGEM DE SERVIÇO ({situacao})',text='OS',width=900,height=400)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None),showlegend=False)
    fig.update_traces(textfont_size=15,textangle=0, textposition="outside", cliponaxis=False)
    fig
    
    espera = painel[['SERVIÇO','DIAS']]
    dt = espera.groupby(['SERVIÇO']).mean().round(2).reset_index().sort_values('DIAS',ascending=False)
    fig = px.bar(dt,x='SERVIÇO',y='DIAS',color='SERVIÇO',title=f'TEMPO MÉDIO DE ESPERA (EM DIAS)',text='DIAS',width=900,height=400)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None),showlegend=False)
    fig.update_traces(textfont_size=15,textangle=0, textposition="outside", cliponaxis=False)
    fig
    
    st.markdown(''':black[****Obs.:*** Observar a motivação da espera, ex.: pendência de projeto ou de material, demandante ausente, complexidade da demanda etc.]''')
    
    dt = painel.groupby(['SETOR']).count().reset_index().sort_values('OS',ascending=False)
    fig = px.bar(dt,x='SETOR',y='OS',color='SETOR',title=f'PRINCIPAIS DEMANDANTES ({situacao})',text='OS',width=900,height=400)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None),showlegend=False)
    fig.update_traces(textfont_size=15,textangle=0, textposition="outside", cliponaxis=False)
    fig

    st.markdown(''':black[****Obs.:*** O setor DINFRA, enquanto demandante, representa intervenções em área comum dos *campi*, 
                ex.: estacionamento, reservatórios de água, circulação etc.]''')
    
    with st.expander('Base de dados:'):
        painel
        
if tema == 'TRANSPORTE':
    st.subheader('Painel de transporte')
    anos = transporte['ANO'].unique()
    maxano = max(anos)
    ano = st.sidebar.radio('Ano:',options=anos, index=list(anos).index(maxano),horizontal=True,label_visibility='collapsed')
    transporte = transporte.loc[transporte['ANO']==ano]
    '-----'
    c1,c2,c3,c4,c5,c6 = st.columns([0.15,0.15,0.15,0.2,0.2,0.15])
    viagens = transporte.loc[(transporte['COMPARTILHADA']=='NÃO') & (transporte['UNIDADE']=='CHP')]
    ticket = transporte.loc[transporte['UNIDADE']=='CHP']
    ticket = ticket['DESTINO'].count()
    cvia = transporte['FINAL'].sum()
    cvformat = format_currency(cvia, 'BRL', locale='pt_BR')
    cmm = (transporte['FINAL'].sum()/transporte['MÊS'].nunique()).round(2)
    cmformat = format_currency(cmm, 'BRL', locale='pt_BR')
    deslocusto = transporte['FINAL'].mean()
    dlformat = format_currency(deslocusto, 'BRL', locale='pt_BR')
   
    c1.metric(f'Contagem de viagens:',viagens['DESTINO'].count())
    c2.metric(f'Contagem de Demandas:',ticket)
    c3.metric(f'Demandas / viagem (Anual):',(ticket/viagens['DESTINO'].count()).round(2))
    c4.metric(f'Custo total:',cvformat)
    c5.metric(f'Custo mensal médio:',cmformat)
    c6.metric(f'Custo médio por demanda:',dlformat)
    '-----'
    data_hoje = pd.Timestamp.today().date().strftime('%d/%m/%Y')
    st.markdown('**VIAGENS DE HOJE**')
    vhoje = transporte.loc[transporte['DATA']==data_hoje]
    vhoje = vhoje[['DESTINO','DATA','TICKET','ASSUNTO','LOCAL','UNIDADE','IDA (HORA)','VOLTA (HORA)','COMPARTILHADA']]
    cl1,cl2 = st.columns(2)
    grhoje = vhoje.groupby(['DESTINO']).count().reset_index()
    fig = px.bar(grhoje,x='DESTINO',y='TICKET',text='TICKET')
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None))
    fig.update_traces(textfont_size=15,textangle=0, textposition="outside", cliponaxis=False)
    with cl1:
        fig  
    dem = vhoje[['COMPARTILHADA','TICKET']]
    gc = dem.groupby(['COMPARTILHADA']).count().reset_index()
    fig = px.pie(gc,names='COMPARTILHADA',values='TICKET',hole=0.5)
    fig.update_traces(text=gc['TICKET'],textfont_size=15,
                      textinfo='percent+text+label',showlegend=False)
    fig.update_layout(title={'text':'VIAGEM COMPARTILHADA','x': 0.5,'xanchor':'center'})
    with cl2:
        fig
    with st.expander('Base de dados:',expanded=True):
        vhoje
    
    vtrans = transporte[['MÊS','TICKET','CONTROLE']]
    via = vtrans.groupby(['MÊS','CONTROLE']).count().reset_index().sort_values('CONTROLE')
    fig = px.line(via,x=['MÊS'],y='TICKET',text='TICKET',title='VIAGENS POR MÊS',width=900,height=500)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black',tickfont_size=15)
    fig.update_layout(legend=dict(title=None, orientation='h',x=0.3),showlegend=False)
    fig.update_traces(textfont_size=15,textfont_color='black',textposition='top left')
    fig
    
    vtrans = transporte[['TICKET','DESTINO']]
    via = vtrans.groupby(['DESTINO']).count().reset_index().sort_values('DESTINO')
    fig = px.bar(via,x='DESTINO',y='TICKET',title='VIAGENS POR CAMPUS',text='TICKET',width=900,height=400)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None))
    fig.update_traces(textfont_size=15,textangle=0, textposition="outside", cliponaxis=False)
    fig
    
    mediavi = viagens[['MÊS','DESTINO','CONTROLE']]
    mediavi = mediavi.groupby(['MÊS','CONTROLE']).count().reset_index().sort_values('CONTROLE')
    medtik = transporte[['MÊS','TICKET','CONTROLE']]
    medtik = medtik.groupby(['MÊS','CONTROLE']).count().reset_index().sort_values('CONTROLE')
    mediavi['ATEND./VIAG.'] = (medtik['TICKET']/mediavi['DESTINO']).round(2)
    fig = px.line(mediavi,x=['MÊS'],y='ATEND./VIAG.',text='ATEND./VIAG.',title='MÉDIA DE ATENDIMENTO / VIAGEM',width=900,height=500)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black',tickfont_size=15)
    fig.update_layout(legend=dict(title=None, orientation='h',x=0.3),showlegend=False)
    fig.update_traces(textfont_size=15,textfont_color='black',textposition='top left')
    fig
    
    ctrans = transporte[['MÊS','FINAL','CONTROLE']]
    dsl = ctrans.groupby(['MÊS','CONTROLE']).sum().reset_index().sort_values('CONTROLE')
    dsl['FORMATADO'] = dsl['FINAL'].apply(formato_moeda)
    fig = px.line(dsl,x=['MÊS'],y='FINAL',text='FORMATADO',title='HISTÓRICO DE CUSTO',width=900,height=500)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black',tickfont_size=15)
    fig.update_layout(legend=dict(title=None, orientation='h',x=0.3),showlegend=False)
    fig.update_traces(textfont_size=15,textfont_color='black',textposition='top left')
    fig 
    
    with st.expander('Base de dados:'):
        transporte
        
if tema == 'CUSTOS':
    st.subheader('Painel de custos')
    '-----'
    anos = demandas['ANO'].unique()
    maxano = max(anos)
    ano = st.sidebar.radio('Ano:',options=anos, index=list(anos).index(maxano),horizontal=True,label_visibility='collapsed')
    demandas = demandas.loc[demandas['ANO']==ano]
    pagamentos = pagamentos.loc[pagamentos['ANO']==ano]

    vtotal = pagamentos['VALOR FATURADO'].sum()
    vformat = format_currency(vtotal, 'BRL', locale='pt_BR')
    empenhado = empenhos['MANUTENÇÃO'].sum()
    eformat = format_currency(empenhado, 'BRL', locale='pt_BR')
    rp = empenhos['RP'].sum()
    rformat = format_currency(rp, 'BRL', locale='pt_BR')
    emp24 = rp + empenhado
    e24format = format_currency(emp24, 'BRL', locale='pt_BR')
    saldo = empenhos['SALDO MP'].sum()
    sformat = format_currency(saldo, 'BRL', locale='pt_BR')
    prest = pagamentos.groupby(['CONTROLE']).count().reset_index()
    prest = prest['CONTROLE'].count()
    prest = pd.to_numeric(prest)
    parcela = (saldo/(12-(prest-1))).round(2) # prest-2 é a correção para o mês de competência, pois o gráfico mostra o mês do pagamento, não o da execução 
    pformat = format_currency(parcela, 'BRL', locale='pt_BR')

    st.markdown(':blue[**APORTE MANUTENÇÃO PREDIAL**]')
    
    c1,c2,c3 = st.columns(3)
    c1.metric('Restos a pagar (manutenção):',rformat)
    c2.metric(f'Empenho {ano}:',eformat)
    c3.metric(f'Valor total para {ano}:',e24format)
   
    c1.markdown(f':red[**EXECUÇÃO MANUTENÇÃO PREDIAL**]')
   
    cc1,cc2,cc3 = st.columns(3)
    cc1.metric('Valor executado:',vformat)
    cc2.metric('Saldo para manutenção:',sformat)
    cc3.metric('Próximas parcelas recomendadas:',pformat)
    '-----'
    gpag = pagamentos[['CONTROLE','COMPETÊNCIA','VALOR FATURADO']]
    gpag = gpag.groupby(['CONTROLE','COMPETÊNCIA']).sum().reset_index().sort_values('CONTROLE')
    gpag['FORMATADO'] = gpag['VALOR FATURADO'].apply(formato_moeda)
    fig = px.line(gpag,x='COMPETÊNCIA',y='VALOR FATURADO',text='FORMATADO',title='HISTÓRICO DE PAGAMENTO (MÊS COMPETENTE)',width=1200,height=500)
    fig.update_yaxes(title=None,tickfont_color='black')
    fig.update_xaxes(title=None,tickfont_color='black',tickfont_size=15)
    fig.update_layout(legend=dict(title=None, orientation='h',x=0.3))
    fig.update_traces(textfont_size=15,textfont_color='black',textposition='top left')
    fig
    
    st.subheader('CUSTOS POR DEMANDA',divider='rainbow')
    st.markdown('***Custos por demanda =*** material + mão de obra estimada (material x 0,6) + transporte (se houver)')
    st.markdown('***Obs.:*** os custos representados nos gráficos a seguir não contabilizam os custos indiretos, lucro e tributos.')
    '-----'
    dem = custos[['CAMPUS','TOTAL']]
    gc = dem.groupby(['CAMPUS']).sum().reset_index()
    gc['FORMATADO'] = gc['TOTAL'].apply(formato_moeda)
    fig = px.pie(gc,names='CAMPUS',values='TOTAL',hole=0.5,width=500,height=400)
    fig.update_traces(text=gc['FORMATADO'],textfont_size=15,textfont_color='black',
                      textinfo='percent+text+label',textposition='outside',showlegend=False)
    fig.update_layout(title={'text':'CUSTO POR CAMPUS','x': 0.5,'xanchor':'center'})
    fig
    
    dem = custos[['SERVIÇO','TOTAL']]
    gc = dem.groupby(['SERVIÇO']).mean().reset_index().sort_values('TOTAL',ascending=False)
    gc['FORMATADO'] = gc['TOTAL'].apply(formato_moeda)
    fig = px.bar(gc,x='SERVIÇO',y='TOTAL',color='SERVIÇO',text='FORMATADO',title='CUSTO MÉDIO POR SERVIÇO',width=1200,height=500)
    fig.update_yaxes(title=None,tickfont_color='black',tickformat=',.2f',showticklabels=False)
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None),showlegend=False)
    fig.update_traces(textfont_size=15,textfont_color='black',textangle=0, textposition="outside", cliponaxis=False)
    fig
    
    gc = custos[['SETOR','TOTAL']]
    gc = custos.groupby(['SETOR']).sum().reset_index().head(15).sort_values('TOTAL',ascending=False)
    gc['FORMATADO'] = gc['TOTAL'].apply(formato_moeda)
    fig = px.bar(gc,x='SETOR',y='TOTAL',color='SETOR',text='FORMATADO',title=f'CUSTO ACUMULADO POR DEMANDANTE',width=1200,height=500)
    fig.update_yaxes(title=None,tickfont_color='black',tickformat=',.2f',showticklabels=False)
    fig.update_xaxes(title=None,tickfont_color='black')
    fig.update_layout(legend=dict(title=None),showlegend=False)
    fig.update_traces(textfont_size=15,textfont_color='black',textangle=0, textposition="outside", cliponaxis=False)
    fig
   
    st.markdown(''':black[****Obs.:*** O setor DINFRA, enquanto demandante, representa intervenções em área comum dos *campi*, 
                ex.: estacionamento, reservatórios de água, circulação etc.]''')
    with st.expander('Base de dados:'):
        pagamentos
        custos
