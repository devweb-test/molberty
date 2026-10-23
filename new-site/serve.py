#!/usr/bin/env python3
"""Dependency-free local preview. Run: python3 serve.py [--port 4173]"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit
from email.utils import parsedate_to_datetime
from datetime import timezone
from io import BytesIO
import argparse
import gzip


class PreviewHandler(SimpleHTTPRequestHandler):
 """Serve the same static files, with negotiated gzip and normal revalidation."""
 compressible={'.html','.css','.js','.json','.svg','.xml','.txt','.ttf'}

 def end_headers(self):
  # Files have stable names while the prototype is edited: revalidate, do not
  # leave a long-lived cached app.js or price table after an update.
  self.send_header('Cache-Control','no-cache')
  self.send_header('Vary','Accept-Encoding')
  super().end_headers()

 def accepts_gzip(self):
  encodings={}
  for item in self.headers.get('Accept-Encoding','').split(','):
   parts=item.strip().lower().split(';');name=parts[0];quality=1.0
   for parameter in parts[1:]:
    if parameter.strip().startswith('q='):
     try:quality=float(parameter.strip()[2:])
     except ValueError:quality=0.0
   encodings[name]=quality
  return encodings.get('gzip',encodings.get('*',0))>0

 def send_head(self):
  path=Path(self.translate_path(self.path))
  if path.is_dir():
   if not urlsplit(self.path).path.endswith('/'):return super().send_head()
   path=next((path/name for name in ('index.html','index.htm') if (path/name).is_file()),path)
  if not self.accepts_gzip() or path.suffix.lower() not in self.compressible or not path.is_file() or self.headers.get('Range'):
   return super().send_head()
  try:
   stat=path.stat()
   if self.headers.get('If-Modified-Since') and not self.headers.get('If-None-Match'):
    try:
     modified=parsedate_to_datetime(self.headers['If-Modified-Since'])
     if modified.tzinfo is None:modified=modified.replace(tzinfo=timezone.utc)
     if int(stat.st_mtime)<=modified.timestamp():
      self.send_response(304);self.end_headers();return None
    except (ValueError,TypeError,OverflowError):pass
   data=path.read_bytes()
  except OSError:return super().send_head()
  compressed=gzip.compress(data,compresslevel=6,mtime=0)
  if len(compressed)>=len(data):return super().send_head()
  self.send_response(200)
  self.send_header('Content-type',self.guess_type(str(path)))
  self.send_header('Content-Encoding','gzip')
  self.send_header('Content-Length',str(len(compressed)))
  self.send_header('Last-Modified',self.date_time_string(stat.st_mtime))
  self.end_headers()
  return BytesIO(compressed)

parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4173);args=parser.parse_args()
root=Path(__file__).resolve().parent
try:
 server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(PreviewHandler,directory=str(root)))
except OSError as exc:
 parser.exit(1,f'Не удалось открыть порт {args.port}: {exc}\nПопробуйте: python3 serve.py --port 4174\n')
print(f'Мольберты.ру: http://127.0.0.1:{args.port}/',flush=True)
try: server.serve_forever()
except KeyboardInterrupt: server.server_close()
