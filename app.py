# The version supporting the heroku app.
# Dash components
import dash
import dash_core_components as dcc 
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State

# Pandas for creating dataframe for maps
import pandas as pd

# Caching
from flask_caching import Cache

# Police api
from police_api import PoliceAPI

# external stylesheet stored in assets folder
external_stylesheets = ['https://fonts.googleapis.com/css?family=Nunito'] 


# Dash app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server # Needed for heroku deployment
cache = Cache(server, config={"CACHE_TYPE":"simple"})
app.title = 'Street Level Crime'

# Constants which will not change including the Mapbox token for accessing the Mapbox API
COLUMN_HEADING = ['Crime Month', 'Crime Category', 'Location Name', 'Latitude', 'Longitude']
SUMMARY_HEADING = ['Crime Category', 'Total']
MAPBOX = 'pk.eyJ1IjoidnNndXJ1bmciLCJhIjoiY2lyNnVibDZrMDAwNmlrbm4wNDhmeW5neiJ9.D8CS9O3fheYIAotVYMyxcQ'
CRIME_CATEGORY_COLOUR ={
                        'Anti-social behaviour':'Orange',
                        'Burglary':'Red',
                        'Violence and sexual offences':'Magenta',
                        'Drugs':'Blue',
                        'Bicycle theft':'Green',
                        'Criminal damage and arson':'light yellow',
                        'Other theft':'light green',
                        'Possession of weapons':'cyan',
                        'Public order':'white',
                        'Shoplifting':'grey',
                        'Theft from the person':'light orange',
                        'Vehicle crime':'brown',
                        'Other crime':'light blue',
                        'Robbery':'Yellow'}


police = PoliceAPI()
# Get the date range of data
dt_range = police.get_dates()

def format_date_range(date_range):
    month_dict = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    new_date_range = []
    for d in date_range:
        a = d.split('-')
        dt = month_dict[int(a[1])]+' '+a[0]
        new_date_range.append((dt))
    return new_date_range

new_dt_range = format_date_range((dt_range))
date_range = dict(zip(new_dt_range, dt_range))
date_dropdown = [{'label':str(k), 'value':str(v)} for k, v in date_range.items()]

# Get the police force
police_forces = police.get_forces()
police_force_list =[{'label':p.name, 'value':p.name} for p in police_forces]

def get_police_force_id(police_name):
    """A function to return the police id in str data format."""
    police_id = [p.id for p in police_forces if p.name == police_name]
    if police_id != []:
        return police_id[0]
    else:
        return None

# Get neighbourhood boundary for finding crime
@cache.memoize(10)
def get_neighbourhood_id(police_name, neighbourhood_name):
    force_id = get_police_force_id(police_name)
    neighbourhoods_police = police.get_force(force_id).neighbourhoods
    neighbourhood = [n.id for n in neighbourhoods_police if n.name==neighbourhood_name]
    if neighbourhood != []:
        return neighbourhood[0]

@cache.memoize(10)
def get_neighbourhood_boundary(police_name, neighbourhood_name):
    if (police_name is not None) and (neighbourhood_name is not None):
        police_id = get_police_force_id(police_name)
        neighbourhood_id = get_neighbourhood_id(police_name, neighbourhood_name)
        neighbourhood = police.get_neighbourhood(police_id, neighbourhood_id)
        return neighbourhood.boundary
    else:
        return None


@cache.memoize(10)
def get_neighbourhood_centre(police_name, neighbourhood_name):
    if (police_name is not None) and (neighbourhood_name is not None):
        police_id = get_police_force_id(police_name)
        neighbourhood_id = get_neighbourhood_id(police_name, neighbourhood_name)
        neighbourhood = police.get_neighbourhood(police_id, neighbourhood_id)
        coords = {'lon':neighbourhood.centre['longitude'], 'lat':neighbourhood.centre['latitude']}
        return coords
    else:
        return {'lon':-2, 'lat':54.5} # approx centre of GB.

@cache.memoize(10)
def create_data_dict(column_heading_list, crime_object_list):
    crime_data = []
    for c in crime_object_list:
        data = [c.month, c.category.name, c.location.name, c.location.latitude, c.location.longitude]
        interim_dict = dict(zip(column_heading_list, data))
        crime_data.append(interim_dict)
    if crime_data != []:
        return crime_data
    else:
        return None

@cache.memoize(10)
def calculate_crime_summary(SUMMARY_HEADING, df):
    """
    Function to calculate total of each type of crime
    Returns dictionary of crimetype and total as key value pair.
    """
    data = []
    crime_dictionary = df['Crime Category'].value_counts().to_dict()
    for k, v in crime_dictionary.items():
        interim_dict ={f'{SUMMARY_HEADING[0]}':k, f'{SUMMARY_HEADING[1]}':v}
        data.append(interim_dict)
    if data != []:
        return data
    else:
        return None

@cache.memoize(10)
def generate_map(n_clicks=None, police_force_dropdown=None, neighbourhood_dropdown=None, crime_date_dropdown=None):
    if n_clicks is None and police_force_dropdown is None and neighbourhood_dropdown is None and crime_date_dropdown is None:
        startup_map = dict(
                        data =[{
                            'type':'scattermapbox',
                            'lat':54.5,
                            'lon':-2,
                            'mode':'markers'
                            }],
                        layout=dict(
                                autosize=True,
                                height=500,
                                font=dict(color="#fffcfc"),
                                titlefont=dict(color="#fffcfc", size='14'),
                                margin=dict(
                                        l=25,
                                        r=25,
                                        b=25,
                                        t=35),
                                hovermode="closest",
                                plot_bgcolor='#191A1A',
                                paper_bgcolor='#020202',
                                title='Waiting for all user parameters',
                                legend=dict(
                                    font=dict(color="#fffcfc",size=10),
                                    orientation='h'),
                                mapbox=dict(
                                        accesstoken=MAPBOX,
                                        style="dark",
                                        center=dict(
                                                lat=54.5,
                                                lon=-2),
                                        zoom=4,
                            )
                    )
            )
        return startup_map
    else:
        if police_force_dropdown is not None and neighbourhood_dropdown is not None and crime_date_dropdown is not None:
            neighbourhood_boundary = get_neighbourhood_boundary(police_force_dropdown, neighbourhood_dropdown)
            crimes = police.get_crimes_area(neighbourhood_boundary, date=crime_date_dropdown)
            table = create_data_dict(COLUMN_HEADING, crimes)
            neighbourhood_centre = get_neighbourhood_centre(police_force_dropdown, neighbourhood_dropdown)
            if table is not None:
                df = pd.DataFrame(table).dropna()
                figure = dict(
                    data =[
                        # Anonymised crime location layer
                        {
                            'type':'scattermapbox',
                            'lat':df['Latitude'],
                            'lon':df['Longitude'],
                            'mode':'markers',
                            'marker':{
                                'color':[CRIME_CATEGORY_COLOUR[d] for d in df['Crime Category']]
                            },
                            'text':[[f"Crime Category:{c}<br>Location:{l}"]for c, l in zip(df['Crime Category'], df['Location Name'])],
                            'name':'Anonymised Crime Location'
                        },
                        ## The neighbourhood boundary layer
                        {
                            'type':'scattermapbox',
                            'lat':[coord[0] for coord in neighbourhood_boundary],
                            'lon':[coord[1] for coord in neighbourhood_boundary],
                            'mode':'lines',
                            'name':f'{neighbourhood_dropdown} neighbourhood boundary',
                            'hoverinfo':'text'
                        }],
                    layout=dict(
                            # autosize=True,
                            # height=500,
                            font=dict(color="#fffcfc"),
                            titlefont=dict(color="#fffcfc", size='14'),
                            margin=dict(
                                    l=35,
                                    r=35,
                                    b=35,
                                    t=45),
                            hovermode="closest",
                            plot_bgcolor='#191A1A',
                            paper_bgcolor='#020202',
                            showlegend=True, # need to improve here
                            legend=dict(
                                    font=dict(color="#fffcfc",size=10),
                                    orientation='h'),
                            title='Anonymised Crime Location',
                            mapbox=dict(
                                    accesstoken=MAPBOX,
                                    style="dark",
                                    center=dict(
                                            lon=neighbourhood_centre['lon'],
                                            lat=neighbourhood_centre['lat']
                                    ),
                                    zoom=12
                            )
                        )
                )
                return figure
            else:  # return this data when no crime data found.
                no_data = dict(
                    data =[
                        {'type':'scattermapbox',
                        'lat':neighbourhood_centre['lon'],
                        'lon':neighbourhood_centre['lat'],
                        'mode':'markers'
                        }],
                    layout=dict(
                        autosize=True,
                        height=500,
                        font=dict(color="#191A1A"),
                        titlefont=dict(color="#191A1A", size='14'),
                        margin=dict(
                                l=35,
                                r=35,
                                b=35,
                                t=45),
                        hovermode="closest",
                        plot_bgcolor='#fffcfc',
                        paper_bgcolor='#fffcfc',
                        title=f'No crime in {crime_date_dropdown}.',
                        legend=dict(
                                    font=dict(color="#fffcfc",size=10),
                                    orientation='h'),
                        mapbox=dict(
                                accesstoken=MAPBOX,
                                style="light",
                                center=dict(
                                        lon=neighbourhood_centre['lon'],
                                        lat=neighbourhood_centre['lat']
                                        ),
                                zoom=12,
                                )
                        )
                )
                return no_data


@cache.memoize(10)
def generate_crime_table(n_clicks=None, police_force_dropdown=None, neighbourhood_dropdown=None, crime_date_dropdown=None):
    if police_force_dropdown is not None and neighbourhood_dropdown is not None and crime_date_dropdown is not None:
        neighbourhood_boundary = get_neighbourhood_boundary(police_force_dropdown, neighbourhood_dropdown)
        crimes = police.get_crimes_area(neighbourhood_boundary, date=crime_date_dropdown)
        table = create_data_dict(COLUMN_HEADING, crimes)
        if table is not None:
            df = pd.DataFrame(table).dropna()
            crime_counts = calculate_crime_summary(SUMMARY_HEADING, df)
            table_div = [
                    html.Div([
                        html.Div(html.H4('Crime Data'), className='eight columns', style={'textAlign':'center','fontFamily':'nunito'}),
                        html.Div(html.H4('Summary'), className='four columns', style={'textAlign':'center','fontFamily':'nunito'})], className='row'),
                        html.Div([
                            html.Div(
                                dash_table.DataTable(
                                    id='crime_table',
                                    columns = [{'name':i, 'id':i} for i in COLUMN_HEADING],
                                    sort_action='native',
                                    filter_action='native',
                                    row_selectable='multi',
                                    fixed_rows=1,
                                    selected_rows=[],
                                    data=table,
                                    page_size=15,
                                    style_header={
                                        'backgroundColor':'#a9c1a1',
                                        'fontWeight':'bold',
                                        'textAlign':'center',
                                        'fontFamily':'nunito'
                                    },
                                    style_cell={'textAlign':'left','fontFamily':'nunito'},
                                    style_cell_conditional=[
                                        {'if':{'column_id':'Crime Month'},
                                        'width':'120px'}],
                                    style_table={
                                        'maxHeight':'500',
                                        'overflowY':'scroll',
                                        'overflowX':'scroll'}), className='eight columns'),
                            html.Div(
                                dash_table.DataTable(
                                    id='crime_summary',
                                    columns = [{'name':i, 'id':i} for i in SUMMARY_HEADING],
                                    fixed_rows=1,
                                    data = crime_counts,
                                    style_header={
                                        'backgroundColor':'#a9c1a1',
                                        'fontWeight':'bold',
                                        'textAlign':'center',
                                        'fontFamily':'nunito'
                                    },
                                    style_cell={'textAlign':'left','fontFamily':'nunito'},
                                    style_table={
                                        'maxHeight':'500',
                                        'overflowY':'scroll',
                                        'overflowX':'scroll'
                                    }     
                                    ), className='four columns')], className='row')
                    ]
            return table_div
        else:
            msg = [html.H5(f'No crimes for the {crime_date_dropdown}.')]
            return msg
    else:
        return None

#################################################################################

app.layout = html.Div([
                html.Div(id='page-title'),
                html.Div(id='neighbourhood_name'),
                html.Div([
                        html.Div(html.H4('Select Police Area'), className='three columns', style={'width':'35%', 'display':'inline-block', 'textAlign':'center','fontFamily':'nunito'}),
                        html.Div(html.H4('Select Police Neighbourhood'), className='three columns', style={'width':'35%', 'display':'inline-block', 'textAlign':'center','fontFamily':'nunito'}),
                        html.Div(html.H4('Select Date'), className='two columns', style={'width':'10%', 'display':'inline-block', 'textAlign':'center','fontFamily':'nunito'})], className='row'),
                html.Div([
                    html.Div([dcc.Dropdown(
                        id='police_force_dropdown',
                        options=police_force_list,
                        placeholder='Select a Police Force....',
                        value=None
                    )], className='three columns', style={'width':'35%', 'display':'inline-block'}),
                    html.Div([dcc.Dropdown(
                        id='police_neighbourhood',
                        placeholder ='Select Police Neighbourhood'
                           )
                    ], className='three columns', style={'width':'35%', 'display':'inline-block'}),
                    html.Div([
                    dcc.Dropdown(
                        id='crime_date',
                        options=date_dropdown,
                        multi=False,
                        value=None,
                        clearable=False
                    )],className='two columns', style={'width':'10%', 'display':'inline-block'}),
                    html.Div([
                        html.Button(id='submit_button', children='Submit', style={'fontFamily':'nunito'})
                    ],className='one column')
                ], className='row'),
                html.Div(
                    [
                        dcc.Graph(
                            id='crime_map',
                            figure=generate_map(),
                            config={'scrollZoom':True},
                            style={'marginTop':'10', 'marginBottom':'10'})
                    ], className='row twelve columns'
                ),
                html.Div(
                    id='crime_div',
                    className='row'),
                html.Div(
                    id='social_media',
                    className='row',
                    style={'width':'100%', 'text-align':'center'})
])


# Callback to update the page title of police force
@app.callback(
    Output(component_id='page-title',component_property='children'),
    [Input(component_id='police_force_dropdown', component_property='value')]
)

def update_page_title(police_force):
    if police_force is not None:
        return html.H1(f'Crime Data for {police_force}', style={'textAlign':'center','fontFamily':'nunito'})
    else:
        return html.H1('Choose a Police Force', style={'fontFamily':'nunito'})

# Callback to update the H2.
@app.callback(
    Output(component_id='neighbourhood_name',component_property='children'),
    [Input(component_id='police_neighbourhood', component_property='value')]
)

def update_neighbourhood_name(neighbourhood_name):
    if neighbourhood_name is not None:
        return html.H2(f'Neighbourhood: {neighbourhood_name}', style={'textAlign':'center','fontFamily':'nunito'})
    else:
        return html.H2('Neighbourhood Not Selected', style={'fontFamily':'nunito'})                

# Callback to populate the neighbourhood dropdown based on police force dropdown selection
@app.callback(
    Output(component_id='police_neighbourhood',component_property='options'),
    [Input(component_id='police_force_dropdown', component_property='value')]
)

def populate_police_neighbourhood(selected_police_force):
    """
    Function to populate the neighbourhoods based on police force selected.
    """
    if selected_police_force is not None:
        police_id = get_police_force_id(selected_police_force)
        police_neighbourhoods = list({'label':n.name, 'value':n.name} for n in police.get_neighbourhoods(police_id))
        return police_neighbourhoods
    else:
        return list()

# Callback to create crime table  
@app.callback(
    Output(component_id='crime_div', component_property='children'),
    [Input(component_id='submit_button', component_property='n_clicks')],
    [State(component_id='police_force_dropdown', component_property='value'),
     State(component_id='police_neighbourhood', component_property='value'),
     State(component_id='crime_date', component_property='value')])


def update_crime_table(n_clicks, police_force_dropdown, neighbourhood_dropdown, crime_date_dropdown):
    returned_data = generate_crime_table(n_clicks, police_force_dropdown, neighbourhood_dropdown, crime_date_dropdown)
    return returned_data

# Generating map each time input changes
@app.callback(
    Output(component_id='crime_map', component_property='figure'),
    [Input(component_id='submit_button', component_property='n_clicks')],
    [State(component_id='police_force_dropdown', component_property='value'),
     State(component_id='police_neighbourhood', component_property='value'),
     State(component_id='crime_date', component_property='value')])

def update_map(n_clicks, police_force_dropdown, neighbourhood_dropdown, crime_date_dropdown):
    returned_map = generate_map(n_clicks, police_force_dropdown, neighbourhood_dropdown, crime_date_dropdown)
    return returned_map

# Update the social media and website link
@app.callback(
    Output(component_id='social_media', component_property='children'),
    [Input(component_id='police_force_dropdown', component_property='value')]
    )

def update_media_links(input_police_force):
    if input_police_force is not None:
        police_id = get_police_force_id(input_police_force)
        force = police.get_force(police_id)
        media = force.engagement_methods
        data = [
            html.Div(
                html.A(f'{m["title"].title()}', href=f'{m["url"]}', target='_blank'),
                className='row',
                style={'display':'inline-block','fontFamily':'nunito', 'text-align':'center', 'position':'relative', 'padding':'20px'})for m in media]
        return data
    else:
        return None


# Running the app
if __name__ == "__main__":
    app.run_server()
