import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import datetime as dt
import pandas as pd
import numpy as np
import investpy

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

#Define a function to retrive a company last results
def getSummary(stock,country):
    try:
        summary=investpy.stocks.get_stock_financial_summary(stock, country, summary_type='income_statement', period='annual').head(1)
    except:
        raise Exception(f"Couldn\'t get summary for {stock} in {country}")
        summary = pd.Dataframe([])
    return summary

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

#Design Layout
app = dash.Dash(__name__, external_stylesheets =[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = html.Div([
    html.Div([html.H1('World Stock Market Monitor',style={"text-align":"center"})]),
    html.Div([    
        html.Div([
            html.Label('Choose a country to analyze stocks from:',style=dict(margin="10px")),
            dcc.Dropdown(options=[{'label': k.capitalize(), 'value': k} for k in countries],placeholder="Select country",
                         id='dropdownCountries', style=dict(width="50%",verticalAlign="middle"))],
        style=dict(display='flex',width="40%")),
        html.Div([
            html.Label('Choose stocks to plot:',style=dict(margin="10px")),
            dcc.Dropdown(options=getStocks('portugal'),placeholder="Select stocks",id='dropdownStocks', multi=True,
                         style=dict(width="80%",verticalAlign="middle"))],
        style=dict(display='flex',width="60%"))],
    style=dict(display='flex')),
    html.Div([
        html.Hr(),
        html.Br(),]),
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
        dcc.Graph(id='graphic', style={"height": "50%", "width": "100%"}),],
        style=dict(display='flex')),
    html.Div([    
        html.H4('Profile(s)'),
        dcc.Markdown(id='profiles'),])
],style=dict(margin='1em')) 

#Callback
#Set stocks from selected country
@app.callback(
    [Output('dropdownStocks', 'options'),
     Output('dropdownStocks', 'value')],
    [Input('dropdownCountries', 'value')])
def setStocks(selectedCountry):
    return [getStocks(selectedCountry),'']

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
    ])
def update_graph(selectedCountry, selectedStocks):
    if not selectedStocks:
        return {}
    else:
        df = getStocksData(selectedStocks[0], selectedCountry)
        df.drop(['open','high','low','volume','currency'],axis='columns', inplace=True)
        df.rename(columns={'close':selectedStocks[0]}, inplace=True)
        df=df.set_index('date')
        for stock in range(1,len(selectedStocks)):
            temp=getStocksData(selectedStocks[stock], selectedCountry)
            temp.drop(['open','high','low','volume','currency'],axis='columns', inplace=True)
            temp.rename(columns={'close':selectedStocks[stock]}, inplace=True)
            temp=temp.set_index('date')
            df=pd.merge(df,temp,on='date',how='left')
        res=[]
        for col in df.columns:
            res.append(go.Scatter(x=df.index,y=df[col],name=col))         
        fig = go.Figure(data=res) 
    return fig

#Write Profiles and Summaries
@app.callback(
    Output('profiles', 'children'),
    [Input('dropdownCountries', 'value'),
     Input('dropdownStocks', 'value'),
    ])
def displayProfileSummary(selectedCountry, selectedStocks):    
    if selectedStocks:
        text=''
        for stock in selectedStocks:
            try:
                summary=getSummary(stock,selectedCountry)
            except:
                summary=pd.Dataframe([])
            text+=f'{getProfile(stock,selectedCountry)} \n'
            if not summary.empty:
                text+=f'Results from {summary.index.strftime("%Y/%m/%d").values}: '
                for column in summary.columns:
                    text+=f'{column}: {summary[column].values}  ' 
            text+=f'\n\n'
        return text
    else:
        return 'No profiles encountered.'

#Run App
if __name__ == '__main__': app.run_server(debug=False)