from flask import Flask, render_template, url_for, redirect, jsonify, request, session
from flask_session import Session #old style was -> from flask.ext.session import Session
from pymongo import MongoClient
import bson
from datetime import date, datetime
import string
import random
import smtplib
import configparser

app = Flask(__name__)
sess = Session()
config = configparser.ConfigParser()
config.read('config.ini')


def send_review_email(id, status, token):
    server = smtplib.SMTP('localhost', 25)
    server.helo()
    msg = f'<p>' \
          f'' \
          f'<a href="/status/{id}/{status}/{token}">Approve</a>' \
          f'</p>'
    server.sendmail('nospam@nospam.org', 'k.nitin.r@gmail.com', msg)
    server.quit()
    pass


def get_db_connection():
    client = MongoClient(
        host=config['db'].get('host', '127.0.0.1'),
        port=int(config['db'].get('port', 27017)),
        username=config['db'].get('user') if 'None' != config['db']['authType'] else None,
        password=config['db'].get('password') if 'None' != config['db']['authType'] else None,
        authSource=config['db'].get('authSource', 'admin') if 'None' != config['db']['authType'] else 'admin',
        # authMechanism=config['db'].get('authMechanism', 'SCRAM-SHA-256') if 'None' != config['db']['authType'] else 'SCRAM-SHA-256',
    )
    return client[config['db'].get('dbname', 'test')]


@app.route('/data')
def data():
    db = get_db_connection()
    jobsarr = db['jobposting'].find()
    return jsonify(jobsarr)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        db = get_db_connection()
        usercnt = db['users'].count()
        user = db['users'].find_one({'_id': request.form['username']})
        if (user is not None and user['password'] == request.form['password']) \
                or (usercnt == 0 and request.form['username'] == 'root' and request.form['password'] == 'katkam'):
            session['username'] = request.form['username']
            return redirect('/')
        else:
            return redirect('/login?error=Invalid+user')
    else:
        return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session['username'] = None
    return redirect('/')


# @app.route('/status/<id>/<status>/<token>')
# def email_status(id, status, token):
#     db = get_db_connection()
#     db['jobposting'].update_one({'_id': bson.ObjectId(id), 'token': token}, {'$set': {'status': status}})
#     return redirect('/')


@app.route('/webstatus/<id>/<status>', methods=['POST'])
def web_status(id, status):
    if not is_logged_in():
        return redirect('/login')
    db = get_db_connection()
    db['jobposting'].update_one({'_id': bson.ObjectId(id)}, {'$set': {'status': status}})
    return redirect('/')


@app.route('/')
def home():
    db = get_db_connection()
    if is_logged_in():
      jobsarr = db['jobposting'].find().sort('_id', -1).limit(50)
    else:
      jobsarr = db['jobposting'].find({'status': 'Approved'}).sort('_id', -1).limit(50)
    return render_template('index.html', jobs=jobsarr)


def is_logged_in():
    return not (not 'username' in session or session['username'] == '' or session['username'] == None)


@app.route('/post', methods=['POST', 'GET'])
def post():
    db = get_db_connection()
    if request.method == 'POST':
        data = request.form.to_dict()

        id_str = request.args['id'] if 'id' in request.args else ''
        if id_str != '':
            if not is_logged_in():
                return redirect('/login')
            data['_id'] = bson.ObjectId(data['_id'])

        #Cannot use date.today() because:
        #bson.errors.InvalidDocument: cannot encode object: datetime.date(2020, 2, 26), of type: <class 'datetime.date'>
        data['postedon'] = datetime.today()

        data['tags'] = data['tags'].strip()
        if data['tags'] != '':
          data['tags'] = data['tags'].split(',')
          i_range = list(range(len(data['tags'])))
          i_range.reverse()
          for i in i_range:
              data['tags'][i] = data['tags'][i].strip()
              if data['tags'][i] == '':
                del data['tags'][i]

        data['token'] = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
        data['status'] = 'Awaiting Approval'

        if id_str != '':
            id_bson = data['_id']
            del data['_id']
            db['jobposting'].update_one({'_id': id_bson}, {'$set': data})
        else:
            db['jobposting'].insert_one(data)
        return redirect('/')
    else:
        id_str = request.args['id'] if 'id' in request.args else ''
        job = None
        if id_str != '':
            job = db['jobposting'].find_one({'_id': bson.ObjectId(id_str)})
        return render_template('post.html', job = job)


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem' #redis, memcached, filesystem or mongodb
    sess.init_app(app)
    app.run(
        host=config['http'].get('bindip', '0.0.0.0'),
        port=config['http'].get('port', '5000'),
        debug=config['app'].get('debug', True)
    )


#    return redirect(url_for('static', filename='post.html'), code=302)
# jobsarr = [
#     {'title': 'Sr. Forklift Inspector', 'date': '20-FEB-2020', 'postedby': 'Nitin'},
#     {'title': 'Pepper Sauce Maker', 'date': '18-FEB-2020', 'postedby': 'Neil'},
# ]
