"""
XBMCLocalProxy 0.1
Copyright 2011 Torben Gerkensmeyer

Modified for Akamai SecureHD by BlueCop

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.
"""

import base64
import re
import time
import urllib
import urllib2
import sys
import traceback
import socket
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib import *

from flvlib import tags
from flvlib import helpers
from flvlib.astypes import MalformedFLV

import zlib
from StringIO import StringIO
import hmac
import hashlib
import base64


class MyHandler(BaseHTTPRequestHandler):
    """
    Serves a HEAD request
    """
    def do_HEAD(s):
        print "XBMCLocalProxy: Serving HEAD request..."
        s.answer_request(0)

    """
    Serves a GET request.
    """
    def do_GET(s):
        print "XBMCLocalProxy: Serving GET request..."
        s.answer_request(1)

    def answer_request(s, sendData):
        try:
            request_path=s.path[1:]
            extensions = ['.Vprj','.edl','.txt','.chapters.xml']
            for extension in extensions:
                if request_path.endswith(extension):
                    s.send_response(404)
                    request_path=''      
            request_path=re.sub(r"\?.*","",request_path)
            if request_path=="stop":
                sys.exit()
            elif request_path=="version":
                s.send_response(200)
                s.end_headers()
                s.wfile.write("Proxy: Running\r\n")
                s.wfile.write("Version: 0.1")
            elif request_path[0:12]=="secureconne/":
                (realpath,sep,swfUrlb64)=request_path[12:].partition("/")
                fURL=base64.b64decode(realpath)
                swfUrl=base64.b64decode(swfUrlb64)
                print swfUrl
                print fURL
                s.serveFile(fURL, swfUrl, sendData)
            else:
                s.send_response(403)
        except:
                traceback.print_exc()
                s.wfile.close()
                return
        try:
            s.wfile.close()
        except:
            pass

            
    """
    Sends the requested file and add additional headers.
    """
    def serveFile(s, fURL, swfUrl, sendData):
        opener = FancyURLopener()
        opener.addheaders=[]
        response = opener.open(fURL)
        s.send_response(response.code)
        print "XBMCLocalProxy: Sending headers..."
        headers=response.info()
        for key in headers:
            try:
                val=headers[key]
                if 'content-length' == key.lower():
                    pass
                else:
                    s.send_header(key, val)
            except Exception, e:
                print e
                pass
        s.end_headers()
        
        if (sendData):
            print "XBMCLocalProxy: Sending data..."
            fileout=s.wfile
            try:
                buf="INIT"
                firstBlock=True
                try:
                    while (buf!=None and len(buf)>0):
                        buf=response.read(200*1024)
                        fileout.write(buf)
                        fileout.flush()
                        if firstBlock:
                            EdgeClass(buf,fURL,swfUrl)
                            firstBlock=False
                    response.close()
                    fileout.close()
                    print time.asctime(),"Closing connection"
                except socket.error, e:
                    print time.asctime(),"Client Closed the connection."
                    try:
                        response.close()
                        fileout.close()
                    except Exception, e:
                        return
                except Exception,e:
                    traceback.print_exc(file=sys.stdout)
                    response.close()
                    fileout.close()
            except:
                traceback.print_exc()
                s.wfile.close()
                return
        try:
            s.wfile.close()
        except:
            pass


class EdgeClass():
    def __init__(self, data, url, swfUrl):
        self.url = url
        self.swfUrl = swfUrl 
        self.domain = self.url.split('://')[1].split('/')[0]
        self.control = 'http://%s/control/' % self.domain
        self.onEdge = self.extractTags(data,onEdge=True)
        #self.MetaData = self.extractTags(data,onMetaData=True)
        self.sendNewToken(self.onEdge['session'],self.onEdge['streamName'],self.swfUrl,self.control)

    def getURL(self, url, post=False, sessionID=False, sessionToken=False):
        try:
            print 'GetURL --> url = '+url
            opener = urllib2.build_opener()
            if sessionID and sessionToken:
                opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:14.0) Gecko/20100101 Firefox/14.0.1' ),
                                     ('x-Akamai-Streaming-SessionToken', sessionToken ),
                                     ('x-Akamai-Streaming-SessionID', sessionID ),
                                     ('Content-Type', 'text/xml' )]
            else:
                opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:14.0) Gecko/20100101 Firefox/14.0.1' )]
            if not post:
                usock=opener.open(url)
            else:
                usock=opener.open(url,':)')
            response=usock.read()
            usock.close()
        except urllib2.URLError, e:
            print 'Error reason: ', e
            return False
        else:
            return response

    def extractTags(self, filedata, onEdge=True,onMetaData=False):
        f = StringIO(filedata)
        flv = tags.FLV(f)
        try:
            tag_generator = flv.iter_tags()
            for i, tag in enumerate(tag_generator):
                if isinstance(tag, tags.ScriptTag):
                    if tag.name == "onEdge" and onEdge:
                        return tag.variable
                    elif tag.name == "onMetaData" and onMetaData:
                        return tag.variable
        except MalformedFLV, e:
            return False
        except tags.EndOfFile:
            return False
        f.close()
        return False
        
    def decompressSWF(self,f):
        if type(f) is str:
            f = StringIO(f)
        f.seek(0, 0)
        magic = f.read(3)
        if magic == "CWS":
            return "FWS" + f.read(5) + zlib.decompress(f.read())
        elif magic == "FWS":
            #SWF Not Compressed
            f.seek(0, 0)
            return f.read()
        else:
            #Not SWF
            return None

    def MD5(self,data):
        m = hashlib.md5()
        m.update(data)
        return m.digest()

    def makeToken(self,sessionID,swfUrl):
        swfData = self.getURL(swfUrl)
        decData = self.decompressSWF(swfData)
        swfMD5 = self.MD5(decData)
        data = sessionID+swfMD5
        sig = hmac.new('foo', data, hashlib.sha1)
        return base64.encodestring(sig.digest()).replace('\n','')

    def sendNewToken(self,sessionID,path,swf,domain):
        sessionToken = self.makeToken(sessionID,swf)
        commandUrl = domain+path+'?cmd=sendingNewToken&v=2.7.6&swf='+swf.replace('http://','http%3A//')
        self.getURL(commandUrl,True,sessionID,sessionToken)
    

class Server(HTTPServer):
    """HTTPServer class with timeout."""

    def get_request(self):
        """Get the request and client address from the socket."""
        self.socket.settimeout(5.0)
        result = None
        while result is None:
            try:
                result = self.socket.accept()
            except socket.timeout:
                pass
        result[0].settimeout(1000)
        return result

class ThreadedHTTPServer(ThreadingMixIn, Server):
    """Handle requests in a separate thread."""

HOST_NAME = '127.0.0.1'
PORT_NUMBER = 64653

if __name__ == '__main__':
    socket.setdefaulttimeout(10)
    server_class = ThreadedHTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    print "XBMCLocalProxy Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
    while(True):
        httpd.handle_request()
    httpd.server_close()
    print "XBMCLocalProxy Stops %s:%s" % (HOST_NAME, PORT_NUMBER)