'''
This file is the WSGI entrypoint for remote / production use.

If you are using Gunicorn, for example:
gunicorn ycdl_flask_entrypoint:site --bind "0.0.0.0:PORT" --access-logfile "-"
'''
import werkzeug.middleware.proxy_fix

import backend

backend.site.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(backend.site.wsgi_app)

site = backend.site