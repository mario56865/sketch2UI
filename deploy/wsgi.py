# Borrowed from https://www.pyimagesearch.com/2018/02/05/deep-learning-production-keras-redis-flask-apache/

import os
from run_pytorch_server import app as application

if __name__ == '__main__':
    os.system('kill $(lsof -t -i:8000')
    application.run() 