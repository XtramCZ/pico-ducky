# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)
# FeatherS2 board support

import socketpool
import time
import os
import storage

import wsgiserver as server
from adafruit_wsgi.wsgi_app import WSGIApp
import wifi

from duckyinpython import *

payload_html = """<!DOCTYPE html>
<html style="width: 100%; height: 100vh; background-color: #131516; color: white;">
    <head>
        <title>Pico W Ducky</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>*{{font-family:Verdana,Geneva,Tahoma,sans-serif;font-weight:400}}a{{text-transform:uppercase;text-decoration:none}}.delete,.edit,.run{{color:#fff;padding:1px 5px;font-size:1em;border-radius:5px}}.edit{{color:#0032ff}}.delete{{color:red}}.run{{color:#4BB543}}td{{padding:0 20px}}.new{{color:#fff;background:#333;padding:5px 10px;font-size:.9em;border-radius:5px}}</style>
    </head>
    <body> <h1>Pico W Ducky</h1>
        <table border="1"> <tr><th>PAYLOAD</th><th>ACTIONS</th></tr>
        {}
        </table>
        <br>
        <a href="/new" class="new">New Script</a>
    </body>
</html>
"""

edit_html = """<!DOCTYPE html>
<html style="width: 100%; height: 100vh; background-color: #131516; color: white;">
  <head>
    <title>Script Editor</title>
    <style>.home,.submit{{color:#fff;padding:5px 10px;font-size:.9em;border-radius:5px;text-transform:uppercase}}textarea:focus{{outline:0}}.submit{{background:#333}}.home{{background:#0c47c7;text-decoration:none}}</style>
  </head>
  <body>
    <form action="/write/{}" method="POST">
      <textarea rows="5" cols="60" name="scriptData">{}</textarea>
      <br/>
      <input type="submit" value="submit" class="submit"/>
    </form>
    <br>
    <a href="/ducky" class="home">Home</a>
  </body>
</html>
"""

new_html = """<!DOCTYPE html>
<html style="width: 100%; height: 100vh; background-color: #131516; color: white;">
  <head>
    <title>New Script</title>
    <style>.home,.submit{{color:#fff;padding:5px 10px;font-size:.9em;border-radius:5px;text-transform:uppercase}}p{{line-height:0}}textarea:focus{{outline:0}}.script-name{{resize:none}}.script-data{{width:500px;height:25vh}}.submit{{background:#333}}.home{{background:#0c47c7;text-decoration:none}}</style>
  </head>
  <body>
    <form action="/new" method="POST">
      <p>Script Name</p>
      <textarea rows="1" cols="60" name="scriptName" class="script-name"></textarea>
      <p>Script content</p>
      <textarea rows="5" cols="60" name="scriptData" class="script-data"></textarea>
      <br/>
      <input type="submit" value="submit" class="submit"/>
    </form>
    <br>
    <a href="/ducky" class="home">Home</a>
  </body>
</html>
"""

response_html = """<!DOCTYPE html>
<html style="width: 100%; height: 100vh; background-color: #131516; color: white;">
    <head> 
        <title>Pico W Ducky</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
        <style>*{{font-family:Verdana,Geneva,Tahoma,sans-serif;font-weight:400}}.home{{color:#fff;background:#0c47c7;padding:5px 10px;font-size:.9em;border-radius:5px;text-transform:uppercase;text-decoration:none}}</style>
    </head>
    <body> <h1>Pico W Ducky</h1>
        <p>{}</p>
        <a href="/ducky" class="home">Home</a>
    </body>
</html>
"""

newrow_html = "<tr><td>{}</td><td><a href='/edit/{}' class='edit'>Edit</a> <a href='/delete/{}' class='delete'>Delete</a> <a href='/run/{}' class='run'>Run</a></tr>"

def setPayload(payload_number):
    if(payload_number == 1):
        payload = "payload.dd"

    else:
        payload = "payload"+str(payload_number)+".dd"

    return(payload)


def ducky_main(request):
    print("Ducky main")
    payloads = []
    rows = ""
    files = os.listdir()
    print(files)
    for f in files:
        if ('.dd' in f) == True:
            payloads.append(f)
            print(payloads)
            newrow = newrow_html.format(f,f,f,f)
            print(newrow)
            rows = rows + newrow

    response = payload_html.format(rows)

    return(response)

_hexdig = '0123456789ABCDEFabcdef'
_hextobyte = None

def cleanup_text(string):
    """unquote('abc%20def') -> b'abc def'."""
    global _hextobyte

    if not string:
        return b''

    if isinstance(string, str):
        string = string.encode('utf-8')

    bits = string.split(b'%')
    if len(bits) == 1:
        return string

    res = [bits[0]]
    append = res.append

    if _hextobyte is None:
        _hextobyte = {(a + b).encode(): bytes([int(a + b, 16)])
                      for a in _hexdig for b in _hexdig}

    for item in bits[1:]:
        try:
            append(_hextobyte[item[:2]])
            append(item[2:])
        except KeyError:
            append(b'%')
            append(item)

    return b''.join(res).decode().replace('+',' ')

web_app = WSGIApp()

@web_app.route("/ducky")
def duck_main(request):
    response = ducky_main(request)
    return("200 OK", [('Content-Type', 'text/html')], response)

@web_app.route("/edit/<filename>")
def edit(request, filename):
    print("Editing ", filename)
    f = open(filename,"r",encoding='utf-8')
    textbuffer = ''
    for line in f:
        textbuffer = textbuffer + line
    f.close()
    response = edit_html.format(filename,textbuffer)
    #print(response)

    return("200 OK",[('Content-Type', 'text/html')], response)

@web_app.route("/write/<filename>",methods=["POST"])
def write_script(request, filename):

    data = request.body.getvalue()
    fields = data.split("&")
    form_data = {}
    for field in fields:
        key,value = field.split('=')
        form_data[key] = value

    #print(form_data)
    storage.remount("/",readonly=False)
    f = open(filename,"w",encoding='utf-8')
    textbuffer = form_data['scriptData']
    textbuffer = cleanup_text(textbuffer)
    #print(textbuffer)
    for line in textbuffer.splitlines():
        f.write(line + '\n')
    f.close()
    storage.remount("/",readonly=True)
    response = response_html.format("Wrote script " + filename)
    return("200 OK",[('Content-Type', 'text/html')], response)

@web_app.route("/new",methods=['GET','POST'])
def write_new_script(request):
    response = ''
    if(request.method == 'GET'):
        response = new_html
    else:
        data = request.body.getvalue()
        fields = data.split("&")
        form_data = {}
        for field in fields:
            key,value = field.split('=')
            form_data[key] = value
        #print(form_data)
        filename = form_data['scriptName']
        if ".dd" not in filename:
            filename = filename + ".dd"
        textbuffer = form_data['scriptData']
        textbuffer = cleanup_text(textbuffer)
        storage.remount("/",readonly=False)
        f = open(filename,"w",encoding='utf-8')
        for line in textbuffer.splitlines():
            f.write(line + '\n')
        f.close()
        storage.remount("/",readonly=True)
        response = response_html.format("Wrote script " + filename)
    return("200 OK",[('Content-Type', 'text/html')], response)

@web_app.route("/delete/<filename>")
def delete(request, filename):
    print("Deleting ", filename)
    storage.remount("/",readonly=False)
    os.remove(filename)
    response = response_html.format("Deleted script " + filename)
    storage.remount("/",readonly=True)
    return("200 OK",[('Content-Type', 'text/html')], response)

@web_app.route("/run/<filename>")
def run_script(request, filename):
    print("run_script ", filename)
    response = response_html.format("Running script " + filename)
    #print(response)
    runScript(filename)
    return("200 OK",[('Content-Type', 'text/html')], response)

@web_app.route("/")
def index(request):
    response = ducky_main(request)
    return("200 OK", [('Content-Type', 'text/html')], response)

@web_app.route("/api/run/<filenumber>")
def run_script(request, filenumber):
    filename = setPayload(int(filenumber))
    print("run_script ", filenumber)
    response = response_html.format("Running script " + filename)
    #print(response)
    runScript(filename)
    return("200 OK",[('Content-Type', 'text/html')], response)

async def startWebService():

    HOST = repr(wifi.radio.ipv4_address_ap)
    PORT = 80        # Port to listen on
    print(HOST,PORT)

    wsgiServer = server.WSGIServer(80, application=web_app)

    print(f"open this IP in your browser: http://{HOST}:{PORT}/")

    # Start the server
    wsgiServer.start()
    while True:
        wsgiServer.update_poll()
        await asyncio.sleep(0)