import json
import os

from superset.app import create_app

app = create_app()


def metric(expression, label):
    return {'expressionType': 'SQL', 'sqlExpression': expression,
            'label': label, 'hasCustomLabel': True, 'optionName': label}


with app.app_context():
    from superset import db, security_manager
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.core import Database
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    username = os.environ.get('ADMIN_USERNAME', 'student')
    owner = security_manager.find_user(username=username)
    if owner is None:
        owner = security_manager.add_user(
            username=username, first_name='Student', last_name='Analyst',
            email='student@example.com', role=security_manager.find_role('Admin'),
            password=os.environ['ADMIN_PASSWORD'])
        if owner is None:
            raise RuntimeError('Could not create the local admin account')

    database = db.session.query(Database).filter_by(database_name='Hillstrom analysis').one_or_none()
    if database is None:
        database = Database(database_name='Hillstrom analysis')
        database.set_sqlalchemy_uri('sqlite:////app/project/results/analytics.sqlite')
        db.session.add(database)
        db.session.commit()

    dataset = db.session.query(SqlaTable).filter_by(database_id=database.id, table_name='customers').one_or_none()
    if dataset is None:
        dataset = SqlaTable(table_name='customers', database=database, owners=[owner])
        db.session.add(dataset)
        db.session.commit()
    dataset.fetch_metadata()
    db.session.commit()

    definitions = [
        ('Purchase conversion', 'AVG(conversion * 1.0)', 'Conversion', '.2%'),
        ('Revenue per assigned customer', 'AVG(spend)', 'Revenue per customer', '$,.2f'),
        ('Website visit rate', 'AVG(visit * 1.0)', 'Visit rate', '.1%'),
    ]
    charts = []
    for title, expression, label, number_format in definitions:
        chart = db.session.query(Slice).filter_by(slice_name=title, datasource_id=dataset.id).one_or_none()
        if chart is None:
            chart = Slice(slice_name=title, datasource_id=dataset.id, datasource_type='table', owners=[owner])
            db.session.add(chart)
        params = {
            'datasource': f'{dataset.id}__table', 'viz_type': 'echarts_timeseries_bar',
            'x_axis': 'segment', 'metrics': [metric(expression, label)],
            'groupby': [], 'adhoc_filters': [], 'row_limit': 1000,
            'time_range': 'No filter', 'color_scheme': 'supersetColors',
            'show_legend': False, 'show_value': True,
            'y_axis_format': number_format, 'x_axis_sort_asc': True,
            'rich_tooltip': True, 'tooltipTimeFormat': 'smart_date',
        }
        chart.viz_type = 'echarts_timeseries_bar'
        chart.params = json.dumps(params)
        charts.append(chart)

    table = db.session.query(Slice).filter_by(slice_name='Group metrics', datasource_id=dataset.id).one_or_none()
    if table is None:
        table = Slice(slice_name='Group metrics', datasource_id=dataset.id, datasource_type='table', owners=[owner])
        db.session.add(table)
    table.viz_type = 'table'
    table.params = json.dumps({
        'datasource': f'{dataset.id}__table', 'viz_type': 'table', 'query_mode': 'aggregate',
        'groupby': ['segment'], 'metrics': [metric('COUNT(*)', 'Customers'),
        metric('SUM(conversion)', 'Buyers'), metric('SUM(visit)', 'Visitors'),
        metric('SUM(spend)', 'Revenue'), metric('AVG(conversion * 1.0)', 'Conversion'),
        metric('AVG(spend)', 'Revenue per customer')], 'adhoc_filters': [],
        'row_limit': 1000, 'time_range': 'No filter', 'table_timestamp_format': 'smart_date',
        'include_search': False, 'page_length': 10,
        'column_config': {'Conversion': {'d3NumberFormat': '.3%'},
                          'Revenue': {'d3NumberFormat': '$,.2f'},
                          'Revenue per customer': {'d3NumberFormat': '$,.3f'}},
    })
    charts.append(table)
    db.session.commit()

    slug = 'hillstrom-email-experiment'
    dashboard = db.session.query(Dashboard).filter_by(slug=slug).one_or_none()
    if dashboard is None:
        dashboard = Dashboard(slug=slug, owners=[owner])
        db.session.add(dashboard)
    dashboard.dashboard_title = 'Email campaigns: visits, purchases and revenue'
    dashboard.published = True
    dashboard.slices = charts
    layout = {
        'DASHBOARD_VERSION_KEY': 'v2',
        'ROOT_ID': {'id': 'ROOT_ID', 'type': 'ROOT', 'children': ['GRID_ID']},
        'GRID_ID': {'id': 'GRID_ID', 'type': 'GRID', 'children': ['ROW-TOP', 'ROW-BOTTOM'], 'parents': ['ROOT_ID']},
        'HEADER_ID': {'id': 'HEADER_ID', 'type': 'HEADER', 'meta': {'text': dashboard.dashboard_title}},
    }
    for row_id, row_charts in [('ROW-TOP', charts[:2]), ('ROW-BOTTOM', charts[2:])]:
        row = {'id': row_id, 'type': 'ROW', 'children': [],
               'parents': ['ROOT_ID', 'GRID_ID'], 'meta': {'background': 'BACKGROUND_TRANSPARENT'}}
        layout[row_id] = row
        for chart in row_charts:
            key = f'CHART-{chart.id}'
            row['children'].append(key)
            layout[key] = {'id': key, 'type': 'CHART', 'children': [],
                'parents': ['ROOT_ID', 'GRID_ID', row_id],
                'meta': {'chartId': chart.id, 'uuid': str(chart.uuid),
                         'width': 6, 'height': 50, 'sliceName': chart.slice_name}}
    dashboard.position_json = json.dumps(layout)
    dashboard.json_metadata = json.dumps({
        'refresh_frequency': 0, 'color_scheme': 'supersetColors',
        'native_filter_configuration': [{
            'id': 'NATIVE_FILTER-channel', 'name': 'Purchase channel',
            'filterType': 'filter_select', 'targets': [{'datasetId': dataset.id, 'column': {'name': 'channel'}}],
            'defaultDataMask': {'extraFormData': {}, 'filterState': {}},
            'cascadeParentIds': [], 'scope': {'rootPath': ['ROOT_ID'], 'excluded': []},
            'controlValues': {'enableEmptyFilter': False, 'multiSelect': True, 'searchAllOptions': False,
                              'inverseSelection': False, 'defaultToFirstItem': False},
            'type': 'NATIVE_FILTER',
        }],
    })
    db.session.commit()
    print(f'Dashboard ready: /superset/dashboard/{slug}/')
