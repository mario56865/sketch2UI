import json
import torch
from PIL import Image
import os
import io
import xml.etree.cElementTree as ET
from flask import render_template, request, Flask, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import requests
import numpy as np
from visual import create_plot
import zipfile
import shutil
import glob
import urllib.parse
from bs4 import BeautifulSoup as Soup

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/uploads")
EXTENSIONS = set(['jpg', 'png', 'jpeg'])
png_output_list = None
filenames_list = None


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ENV'] = 'development'

PyTorch_REST_API_URL = 'http://127.0.0.1:4000/predict'

extra_dirs = ['templates/', 'static/']
extra_files = extra_dirs[:]
for extra_dir in extra_dirs:
    for dirname, dirs, files in os.walk(extra_dir):
        for filename in files:
            filename = os.path.join(dirname, filename)
            if os.path.isfile(filename):
                extra_files.append(filename)

def create_var_folders():
    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads")) is not True:
        os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads"))
    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/json")) is not True:
        os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/json"))
    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/xml")) is not True:
        os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/xml"))
    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/uploads")) is not True:
        os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/uploads"))

def delete_folders():
    shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/json"))
    os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/json"))
    shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/xml"))
    os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/downloads/xml"))
    shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/uploads"))
    os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "var/www/uploads"))

def predict_result(image_path):
    # Initialize image path
    image = open(image_path, 'rb').read()
    assert(image is not None)
    payload = {'image': image}
    #print(payload)

    # Submit the request.
    try:
        r = requests.post(PyTorch_REST_API_URL, files=payload).json()
    except Exception as e:
        print(e)

    # Ensure the request was successful.
    if r['success']:
        # Loop over the predictions and display them.
        return r['predictions'][0]['labels'], r['predictions'][0]['boxes']
    # Otherwise, the request failed.
    else:
        print('Request failed')

def file_allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSIONS

@app.route("/")
def home_screen():
    global png_output_list
    global filenames_list

    png_output_list = list()
    filenames_list = list()

    delete_folders()
    return render_template('index.html')

@app.route("/home_page")
def redirect_back_home():
    return redirect(url_for('home_screen'))

@app.route("/oops")
def oops():
    return "OOPS! You didn't input any thing, please try again"

@app.errorhandler(403)
def page_forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

@app.route("/instruct")
def instructions():
    return render_template('instruct.html')

@app.route("/pubs")
def pubs():
    return render_template('pubs.html')

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/json")
def downloadjson():
    data = io.BytesIO()
    path_json = os.path.join(os.path.dirname(os.path.abspath(__file__)),'var/www/downloads/json')
    with zipfile.ZipFile(data, mode='w', compression=zipfile.ZIP_DEFLATED) as z:
        for f_name in glob.glob(os.path.join(path_json, '*')):
            z.write(f_name, os.path.join('json', os.path.basename(f_name)))
    data.seek(0)
    return send_file(data, mimetype='application/zip', as_attachment=True, attachment_filename='json.zip')

@app.route("/xml")
def xmls():
    data = io.BytesIO()
    path_xml = os.path.join(os.path.dirname(os.path.abspath(__file__)),'var/www/downloads/xml')
    with zipfile.ZipFile(data, mode='w', compression=zipfile.ZIP_DEFLATED) as z:
        for f_name in glob.glob(os.path.join(path_xml, '*')):
            z.write(f_name, os.path.join('xml', os.path.basename(f_name)))
    data.seek(0)
    return send_file(data, mimetype='application/zip', as_attachment=True, attachment_filename='xml.zip')

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    global png_output_list
    global filenames_list
    if request.method == 'POST':
        file_obj = request.files
        assert(file_obj is not None)
        for __, f in file_obj.items():
            if f and file_allowed(f.filename):
                filename = secure_filename(f.filename)
                filenames_list.append(filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                f.save(file_path)


        for img_input in glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*')):
            label, box = predict_result(img_input)
            label = np.array(label)
            box = np.array(box) #TODO Add more multi batch stuffies
            png_output = create_plot(label, box, os.path.join(app.config['UPLOAD_FOLDER'], img_input))
            assert(png_output is not None)
            png_output_list.append(png_output.decode('utf-8'))
            label = None
            box = None
            png_output = None
    
   #print(png_output_list)
    return render_template('result.html', img_data=png_output_list, filenames=filenames_list, list_len=len(png_output_list))




if __name__ == '__main__':
    app.secret_key = 'lolUWiscool'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.register_error_handler(403, page_forbidden)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    create_var_folders()

    app.run(debug=True, port=5000)