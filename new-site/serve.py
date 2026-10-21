#!/usr/bin/env python3
"""Dependency-free local preview. Run: python3 serve.py [--port 4173]"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4173);args=parser.parse_args()
root=Path(__file__).resolve().parent
try:
 server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(root)))
except OSError as exc:
 parser.exit(1,f'Не удалось открыть порт {args.port}: {exc}\nПопробуйте: python3 serve.py --port 4174\n')
print(f'Мольберты.ру: http://127.0.0.1:{args.port}/',flush=True)
try: server.serve_forever()
except KeyboardInterrupt: server.server_close()
