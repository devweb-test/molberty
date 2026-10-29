"""Run against serve.py: PREVIEW_URL=http://127.0.0.1:4175 python3 scripts/test-server.py."""
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import os, gzip, json

root=Path(__file__).resolve().parent.parent
base=os.environ.get('PREVIEW_URL','http://127.0.0.1:4173').rstrip('/')

def fetch(path,headers=None,method='GET',opener=None):
 request=Request(base+path,headers=headers or {},method=method)
 try:
  response=(opener.open(request) if opener else urlopen(request))
 except HTTPError as error:response=error
 with response:return response.status,dict(response.headers),response.read()

for route,file in [('/catalog/','catalog/index.html'),('/prices/','prices/index.html'),('/contacts/','contacts/index.html'),('/assets/data.js','assets/data.js'),('/assets/app.js','assets/app.js'),('/assets/style.css','assets/style.css'),('/assets/prata.ttf','assets/prata.ttf')]:
 original=(root/file).read_bytes()
 status,headers,data=fetch(route,{'Accept-Encoding':'gzip'})
 assert status==200 and headers.get('Content-Encoding')=='gzip',route
 assert gzip.decompress(data)==original,route+' gzip content'
 assert len(data)==int(headers['Content-Length']) and len(data)<len(original),route
 assert headers['Vary']=='Accept-Encoding' and headers['Cache-Control']=='no-cache'
 head,head_headers,head_data=fetch(route,{'Accept-Encoding':'gzip'},'HEAD')
 assert head==200 and head_data==b'' and int(head_headers['Content-Length'])==len(data),route+' HEAD'
 status,_,body=fetch(route,{'Accept-Encoding':'gzip','If-Modified-Since':headers['Last-Modified']})
 assert status==304 and body==b'',route+' 304'
 for encoding in ['identity','gzip;q=0, identity;q=1']:
  status,plain_headers,plain=fetch(route,{'Accept-Encoding':encoding})
  assert status==200 and 'Content-Encoding' not in plain_headers and plain==original,route+' identity'
 status,_,body=fetch(route,{'Accept-Encoding':'gzip','If-Modified-Since':'Thu, 01 Jan 1970 00:00:00 GMT'})
 assert status==200 and gzip.decompress(body)==original,route+' stale validation'

photo=json.loads((root/'data/catalog.json').read_text())['products'][0]['image']
status,headers,data=fetch('/assets/'+photo,{'Accept-Encoding':'gzip'})
assert status==200 and 'Content-Encoding' not in headers and data==(root/'assets'/photo).read_bytes()
error_page=(root/'404.html').read_bytes()
for missing in ['/missing-performance-test/','/catalog/no-such-category/item/','/no-such-file.html']:
 for encoding in ['identity','gzip','gzip;q=0, identity;q=1']:
  status,headers,body=fetch(missing,{'Accept-Encoding':encoding})
  assert status==404 and 'Location' not in headers,missing
  assert headers['Content-Type']=='text/html; charset=utf-8'
  assert headers['X-Robots-Tag']=='noindex, nofollow'
  assert (gzip.decompress(body) if headers.get('Content-Encoding')=='gzip' else body)==error_page
  status,head_headers,head_body=fetch(missing,{'Accept-Encoding':encoding},'HEAD')
  assert status==404 and not head_body and head_headers['Content-Length']==headers['Content-Length']

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
status,headers,_=fetch('/catalog',opener=build_opener(NoRedirect))
assert status==301 and headers['Location']=='/catalog/'
print('Gzip negotiation, exact content, HEAD, 304, stale validation, images, 404 and slash redirect: PASS')
