import flask, sqlite3, json, sys
from datetime import datetime

app = flask.Flask(__name__)
app.config["DEBUG"] = True

@app.get("/verify")
def verify():
    return flask.jsonify({'valid':True})

@app.get("/map")
def map():
    f = open('config.json', 'r')
    data = json.load(f)

    mapa = [int(x) for x in data['map']]

    return flask.jsonify({'map': mapa})

@app.get("/currentband")
def currentband():
    f = open('band.json', 'r')
    data = json.load(f)
    f.close()
    
    return flask.jsonify({'mac': data['mac']})

@app.get("/locations")
def locations():
    # Creamos la conexion con la BD
    db_connection = sqlite3.connect('file:db/space.db?mode=ro', uri=True)
    locations_db = db_connection.cursor()

    args = flask.request.args
    date = args.get('from')
    mac = args.get('mac')

    try: # Con la conversión compruebo el formato (si fuese erróneo, no devuelve ninguna)
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')

        locations_db.execute(f'SELECT date, x, y FROM locations WHERE date > \'{date}\' AND mac_address = \'{mac}\'')
        rows = locations_db.fetchall()

        keys = ['date', 'x', 'y']
        data = {'locations': [dict(zip(keys, row)) for row in rows]}

        db_connection.close()
        return flask.jsonify(data)

    except ValueError:
        db_connection.close()
        return flask.jsonify({'error':'El formato no es correcto.'})


@app.get("/currentlocation")
def currentlocation():
    # Creamos la conexion con la BD
    db_connection = sqlite3.connect('file:db/space.db?mode=ro', uri=True)
    locations_db = db_connection.cursor()

    args = flask.request.args
    mac = args.get('mac')

    locations_db.execute(f'SELECT date, x, y FROM locations WHERE mac_address = \'{mac}\' ORDER BY date DESC LIMIT 1')
    row = locations_db.fetchone()
    print(row)
    db_connection.close()

    keys = ['date', 'x', 'y']
    data = {'locations': [dict(zip(keys, row))]}

    return flask.jsonify(data)


@app.get("/events")
def events():
    # Creamos la conexion con la BD
    db_connection = sqlite3.connect('file:db/space.db?mode=ro', uri=True)
    events_db = db_connection.cursor()

    args = flask.request.args
    date = args.get('from')
    mac = args.get('mac')

    try: # Con la conversión compruebo el formato (si fuese erróneo, no devuelve ninguna)
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')

        events_db.execute(f'SELECT date, message, priority FROM events WHERE date > \'{date}\' and mac_address = \'{mac}\'')
        rows = events_db.fetchall()

        keys = ['date', 'message', 'priority']
        data = {'events': [dict(zip(keys, row)) for row in rows]}

        db_connection.close()
        return flask.jsonify(data)

    except ValueError:
        db_connection.close()
        return flask.jsonify({'error':'El formato no es correcto.'})


@app.post("/setband")
def setband():
    # Obtenemos los datos
    data = flask.request.get_json(force=True)

    f = open('band.json', 'w')
    f.write(json.dumps(data, indent=4))
    f.close()

    return flask.jsonify({'response':'Seleccionada una nueva pulsera.'})
    


if __name__ == '__main__':
    app.run('192.168.4.1', debug=True, port=8100, ssl_context=('certs/server.crt', 'certs/server.key'))