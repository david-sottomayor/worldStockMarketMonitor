import datetime as dt
import numpy as np
import pandas as pd
import investpy
import flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#Retrieve a list of countries with stocks listed on Investing.com
countries = investpy.get_stock_countries()
countries.sort()

#Defines a function to return a list of the available stocks in a given country
def getStocks(country):
    # function to get a dictionary of all tickers/stocks available
    # in a specific country
    try:
        dfStocks = investpy.get_stocks(country=country.lower())
    except:
        dfStocks = pd.DataFrame(data=dict(name=['No results'], symbol=['No results']) )
    # extract names/labels and symbols
    dfStocks.sort_values('name',inplace=True)
    dfStocks.loc[:, 'name'] = dfStocks.loc[:, 'name'].apply(lambda x: x.strip('u200b') )
    labels= [', '.join(i) for i in dfStocks.loc[:, ['name','symbol']].values]
    values = dfStocks.loc[:, ['symbol']].values.T[0]
    dictStocks = [{'label':i, 'value':j} for i,j in zip(labels, values)]
    return dictStocks

#Define a function to retrieve historic data of chosen stock and by default from a scentury to date
#Inputs: Symbol, Country, Period Span wit 'Y' or 'M' sufix
def getStocksData(stock, country, span='100Y'):
    if 'Y' in span:
        span = float(span.strip('Y'))
        fromDate = dt.date.today() - dt.timedelta(days=span*365.25)
    elif 'M' in span:
        fromDate = dt.date.today() - dt.timedelta(days=span*31)
    fromDate = fromDate.strftime('%d/%m/%Y')
    toDate = dt.date.today().strftime('%d/%m/%Y')
    try:
        dfStocks = investpy.get_stock_historical_data(stock=stock, country=country, from_date=fromDate,
                                                      to_date=toDate, as_json=False, order='ascending')
        dfStocks.reset_index(inplace=True)
        dfStocks.columns = [i.lower() for i in dfStocks.columns]
    except:
        raise Exception(f"Couldn\'t get data for {stock} in {country}")
        dfStocks = pd.DataFrame([])
    return dfStocks

#Define a function to retrieve a company profile
def getProfile(stock,country):
    try:
        profile=investpy.stocks.get_stock_company_profile(stock, country, language='english')
    except:
        raise Exception(f"Couldn\'t get profile for {stock} in {country}")
        profile = ''
    return profile['desc']

#Define a function to retrive a company summary
def getSummary(stock,country):
    try:
        summary=investpy.stocks.get_stock_financial_summary(stock, country, summary_type='income_statement', period='annual')
    except:
        raise Exception(f"Couldn\'t get summary for {stock} in {country}")
        summary = pd.Dataframe([])
    return summary

#Define a function to retrive stock's dividends
def getDividends(stock,country):
    try:
        dividends=investpy.stocks.get_stock_dividends(stock, country)
    except:
        raise Exception(f"Couldn\'t get dividends for {stock} in {country}")
        dividends = pd.Dataframe([])
    return dividends

#Define a function to get the top five stocks from the selected country
def getTop10(country):
    try:
        top10=investpy.stocks.get_stocks_overview(country, as_json=False, n_results=1000)
        top10=top10.sort_values('turnover', ascending=False).head(10)
        top10.drop(['country','symbol','currency'],axis=1, inplace=True)
        top10.rename(columns={"change_percentage":"change %"}, inplace=True)
    except:
        raise Exception(f"Couldn\'t get top10 for {country}")
        top10 = pd.Dataframe([])
    return top10

#Design App Layout
app = dash.Dash(__name__, external_stylesheets =[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.Div([html.H1('World Stock Market Monitor',style={"text-align":"center"}),
             html.Hr(),
             html.Br()
    ]),
    html.Div([    
        html.Div([
            html.Label('Choose a country to analyze stocks from:',style=dict(margin="10px")),
            dcc.Dropdown(options=[{'label': k.capitalize(), 'value': k} for k in countries],placeholder="Select country",
                         id='dropdownCountries', style=dict(width="60%",verticalAlign="middle"))],
        style=dict(display='flex',width="50%")),
        html.Div([
                html.Label('Choose stocks to plot:',style=dict(margin="10px")),
                dcc.Dropdown(options=getStocks('portugal'),placeholder="Select stocks",id='dropdownStocks', multi=True,
                         style=dict(width="80%",verticalAlign="middle"))],style=dict(display='flex',width="60%")),
        html.Div([
                html.Div([
                    html.Label('Select Initial Date:', style=dict(margin="10px")),
                    dcc.DatePickerSingle(date=dt.datetime.today() - dt.timedelta(days=36525),
                    display_format='Y-MM-DD',
                    id='initialdate', style=dict(width="50%",verticalAlign="middle"))], style=dict(display='flex',width="40%")),         
                html.Div([
                    html.Label('Select Final Date:',style=dict(margin="10px")),
                    dcc.DatePickerSingle(date=dt.datetime.today(),
                    display_format='Y-MM-DD',
                    id='finaldate',style=dict(width="50%",verticalAlign="middle"))], style=dict(display='flex',width="40%")),
            ],style=dict(display='flex',width="60%")),   
    ],style={"display":"flex","margin-bottom":"5px"}),
    html.Div([
        html.Label('Choose only one company to generate report:',style={"margin-right":"5px"}),
        dcc.Dropdown(id='dropdownReport',placeholder="Select company", multi=False, style={"width":"60%"}),
        html.P(id='tempLabel',children='No Company selected')],#,style={"visibility":"hidden"})],
    style=dict(display='flex')),
    html.Br(),
    dcc.Tabs(id='tabs', value='tabStocks', persistence=False, children=[ 
        dcc.Tab(label='Stocks', value='tabStocks', children=
            html.Div([    
                html.Div([
                    html.H4('Top 10 performing stocks in the selected country', style={"width": "40%"}),
                    html.H4('Plot of selected stock(s)', style={"width": "60%"})],
                style=dict(display='flex')),    
                html.Div([
                    html.Div([
                        html.Div(id='top10Desc', 
                                children='This are the 10 stocks currently offering a higher turnover for the selected country\n\n\n',),
                        html.Div(id='table', style={"width": "30%","margin-top":"50px"}),
                    ], style={"width": "40%"}),
                    html.Div(id='margin', style={"width": "10%"}),
                    html.Div(id="g1Container", style={"height": "70%", "width": "100%"},children=dcc.Graph(id='graphic')),
                ],className='box',style=dict(display='flex'))    
            ])    
        ),
        dcc.Tab(label='Report', value='tabReport',children=[
            html.H4(f'Company Report',style={"text-align":"center"}),
            html.H4('Profile'),
            html.Div(id='profile'),
            html.H4('Summary'),
            html.Div(id='summary'),
            html.Div([
                html.Div([
                    html.H4('Dividends'),
                    html.Div(id='dividends')
                ],style={"width":"38%"}),
                html.Div(style={"width":"2%"}),
                html.Div(dcc.Graph(id='divGraph'),style={"width":"60%"})       
            ],style=dict(display="flex",width="100%")),
            html.H4('Stock Prices'),
            html.Div(dcc.Graph(id='candle'))]
        )]),
    html.Footer(id='footer',children=[
        html.Table(style={"width":"100%"}, children=[
            html.Tr(style={"width":"100%"}, children=[
                html.Td(style={"width":"20%", "float":"left"}, children=[
                     html.Img(src='https://www.novaims.unl.pt/images/logo.png')
                ]),
                html.Td(style={"width":"60%", "text-align":"center"}, children=[
                    html.H5('©2021, David Sotto-Mayor Machado, Débora A. Santos, Ana Marta Silva, and Pedro Henriques Medeiros'),
                    html.P("for the Master's Program in Data Science and Advanced Analytics at NOVA IMS - Information Management School")
                ]),
                html.Td(style={"width":"20%", "align":"right", "text-align":"right"}, children=[
                    html.Img(src='https://i-invdn-com.akamaized.net/logos/investing-com-logo.png',style={"background-color":"#000000"}),
                    html.P('Data obtained instantaneously from Investing.com',style={"text-align":"right"})
                ])
            ])
        ])
    ],style=dict(display='flex',width='100%'))
],style=dict(margin='1em')) 

#Callbacks
#Set stocks from selected country
@app.callback(
    [Output('dropdownStocks', 'options'),
     Output('dropdownStocks', 'value')],
    [Input('dropdownCountries', 'value')])
def setStocks(selectedCountry):
    return [getStocks(selectedCountry),'']

#Get stocks for dropdownReport
@app.callback(
    [Output('dropdownReport', 'options')],
    [Input('dropdownStocks', 'value')],
    [State('dropdownStocks', 'options')]
    )
def setStocks(selectedStocks: list, selectedLabels: list)->list:
    if not selectedStocks:
        return []
    else:
        chosenLabels = []
        for val in selectedStocks:
            chosenLabelList = [x['label'] for x in selectedLabels if x['value'] == val]
            chosenLabel = chosenLabelList[0]
            chosenLabels.append({'label':chosenLabel,'value':val})
    return [chosenLabels]

#Update data of top10 stocks
@app.callback(Output('table','children'),
            [Input('dropdownCountries', 'value')])
def updateTable(selectedCountry):
    df=getTop10(selectedCountry)
    data = df.to_dict('rows')
    columns =  [{"name": i, "id": i,} for i in (df.columns)]
    return dash_table.DataTable(data=data, columns=columns)

#Plot graphic
@app.callback(
    Output('graphic', 'figure'),
    [Input('dropdownCountries', 'value'),
     Input('dropdownStocks', 'value'),
     Input('initialdate', 'date'),
     Input('finaldate', 'date')
    ])
def updateGraph(selectedCountry, selectedStocks,initialdate, finaldate):  
    if not selectedStocks:
        return {}
    else:
        df = getStocksData(selectedStocks[0], selectedCountry)
        df.drop(['open','high','low','volume','currency'],axis='columns', inplace=True)
        df.rename(columns={'close':selectedStocks[0]}, inplace=True)
        for stock in range(1,len(selectedStocks)):
            temp=getStocksData(selectedStocks[stock], selectedCountry)
            temp.drop(['open','high','low','volume','currency'],axis='columns', inplace=True)
            temp.rename(columns={'close':selectedStocks[stock]}, inplace=True)
            df=pd.merge(df,temp,on='date',how='left')
        df_filtered_date = df[(df['date'] >= initialdate) & (df['date'] <= finaldate )]
        df_filtered_date=df_filtered_date.set_index('date')
        res=[]
        for col in df_filtered_date.columns:
            res.append(go.Scatter(x=df_filtered_date.index,y=df_filtered_date[col],name=col))
        layout = dict(xaxis=dict(title='Dates'),
                  yaxis=dict(title='Closing Prices'),
                  font = dict(size = 16))
        fig = go.Figure(data=res, layout = layout) 
    return fig

#Display Profile
@app.callback( 
    Output('profile', 'children'),
    [Input('dropdownCountries', 'value'),
     Input('dropdownReport', 'value'),
    ])
def showProfile(selectedCountry, selectedStock):
    try:
        profile=getProfile(selectedStock,selectedCountry)
    except:
        profile='No profile encountered'
    return profile

#Display Summary
@app.callback( 
    Output('summary', 'children'),
    [Input('dropdownCountries', 'value'),
     Input('dropdownReport', 'value'),
    ])
def showSummary(selectedCountry, selectedStock):
    try:
        dfS=getSummary(selectedStock, selectedCountry).head(1)
    except:
        dfS=pd.Dataframe([])
    dataS = dfS.to_dict('rows')
    columnsS =  [{"name": i, "id": i,} for i in (dfS.columns)]
    tableS = dash_table.DataTable(data=dataS, columns=columnsS)
    return tableS

#Display Dividends
@app.callback( 
    [Output('dividends', 'children'),
     Output('divGraph', 'figure')],
    [Input('dropdownCountries', 'value'),
     Input('dropdownReport', 'value'),
     Input('initialdate', 'date'),
     Input('finaldate', 'date')])
def showDividends(selectedCountry, selectedStock, initialdate, finaldate):
    try:
        dfDiv=getDividends(selectedStock, selectedCountry)
    except:
        dfDiv=pd.Dataframe([])
    #deal with the table
    dfDiv['Date']=pd.DatetimeIndex(dfDiv['Date']).strftime("%Y-%m-%d")
    dfDiv['Payment Date']=pd.DatetimeIndex(dfDiv['Payment Date']).strftime("%Y-%m-%d")
    dataDiv = dfDiv.head(10).to_dict('rows')
    columnsDiv =  [{"name": i, "id": i,} for i in (dfDiv.columns)]
    tableDiv = dash_table.DataTable(data=dataDiv, columns=columnsDiv)
    #Graphic Representation
    dfDivFilter=dfDiv[(dfDiv['Payment Date'] >= initialdate) & (dfDiv['Payment Date'] <= finaldate)]
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.update_layout(title_text="Dividends and Yields", title_font_size=16)
    fig.update_xaxes(title_text="Dates", title_font_size=16, tickfont_size=16)
    fig.update_yaxes(title_text="Dividend", title_font_size=16, tickfont_size=16, secondary_y=False)
    fig.update_yaxes(title_text="Yield (%)", title_font_size=16, tickfont_size=16, secondary_y=True)
    # Add traces
    fig.add_trace(go.Scatter(x=dfDivFilter['Payment Date'], y=dfDivFilter['Dividend'], name="Dividend"),secondary_y=False)
    fig.add_trace(go.Scatter(x=dfDivFilter['Payment Date'], y=dfDivFilter['Yield'], name="Yield"),secondary_y=True)
    return tableDiv , fig


#Plot candlesticks
@app.callback(
    Output('candle', 'figure'),
    [Input('dropdownCountries', 'value'),
     Input('dropdownReport', 'value'),
     Input('initialdate', 'date'),
     Input('finaldate', 'date')
    ])
def display_candlestick(selectedCountry, selectedStocks, initialdate, finaldate):
    if not selectedStocks:
        return {}
    else:
        df = getStocksData(selectedStocks, selectedCountry)
        df.drop(['volume','currency'],axis='columns', inplace=True)
        df_filtered_date = df[(df['date'] >= initialdate) & (df['date'] <= finaldate )]
        data=[go.Candlestick(x=df_filtered_date['date'],
                open=df_filtered_date['open'],
                high=df_filtered_date['high'],
                low=df_filtered_date['low'],
                close=df_filtered_date['close'])]
        layout = dict(
                  title=dict(text= f'{selectedStocks}'),
                  xaxis=dict(title='Dates'),
                  yaxis=dict(title='Prices'),
                  font = dict(size = 16))
        fig = go.Figure(data=data, layout = layout) 
        fig.update_layout(xaxis_rangeslider_visible=False)
    return fig

#Run App
if __name__ == '__main__': app.run_server(debug=False)