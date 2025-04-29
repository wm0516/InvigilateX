import sys
path = '/home/wmm/InvigilateX'
if path not in sys.path:
    sys.path.append(path)

from main import app as application
