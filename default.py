#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui,sys,xbmcaddon,base64,socket

pluginhandle = int(sys.argv[1])
xbox = xbmc.getCondVisibility("System.Platform.xbox")
addon = xbmcaddon.Addon(id='plugin.video.eurovisionsports_tv')
translation = addon.getLocalizedString
akamaiProxyServer = xbmc.translatePath(addon.getAddonInfo('path')+"/akamaiSecureHD.py")

forceViewMode=addon.getSetting("forceViewMode")
if forceViewMode=="true":
  forceViewMode=True
else:
  forceViewMode=False
viewMode=str(addon.getSetting("viewMode"))

def index():
        content = getUrl("http://www.eurovisionsports.tv/london2012/xml/london2012.xml")
        spl=content.split('<channel id=')
        for i in range(1,len(spl),1):
            entry=spl[i]
            match=re.compile('<title><!\\[CDATA\\[(.+?)\\]\\]></title>', re.DOTALL).findall(entry)
            title=match[0]
            match=re.compile('<graphicThumbnailUrl>(.+?)</graphicThumbnailUrl>', re.DOTALL).findall(entry)
            thumb=match[0]
            addDir(title,title,'listVideos',thumb)
        xbmcplugin.endOfDirectory(pluginhandle)
        if forceViewMode==True:
          xbmc.executebuiltin('Container.SetViewMode('+viewMode+')')

def listVideos(type):
        content = getUrl("http://www.eurovisionsports.tv/london2012/xml/london2012.xml")
        content = content[content.find('<![CDATA['+type+']]>'):]
        content = content[:content.find('</channel>')]
        spl=content.split('<item id=')
        for i in range(1,len(spl),1):
            entry=spl[i]
            match=re.compile('<title><!\\[CDATA\\[(.+?)\\]\\]></title>', re.DOTALL).findall(entry)
            title=match[0]
            title=cleanTitle(title)
            match=re.compile('<description><!\\[CDATA\\[(.+?)\\]\\]></description>', re.DOTALL).findall(entry)
            description=match[0]
            description=cleanTitle(description)
            match=re.compile('<enclosure url="(.+?)"', re.DOTALL).findall(entry)
            url=match[0]
            match=re.compile('<media:thumbnail xmlns:media="http://search.yahoo.com/mrss" url="(.+?)"/>', re.DOTALL).findall(entry)
            thumb=match[0]
            if description!="Featured Video":
              title=title+" - "+description
            addLink(title,url,'playVideo',thumb)
        xbmcplugin.endOfDirectory(pluginhandle)
        if forceViewMode==True:
          xbmc.executebuiltin('Container.SetViewMode('+viewMode+')')

def playVideo(urlMain):
        content = getUrl(urlMain)
        if urlMain.find(".smil")>0:
          match=re.compile('<meta name="httpBase" content="(.+?)"', re.DOTALL).findall(content)
          base=match[0]
          maxBitrate=0
          match=re.compile('<video src="(.+?)" system-bitrate="(.+?)"/>', re.DOTALL).findall(content)
          for urlTemp, bitrateTemp in match:
            bitrate=int(bitrateTemp)
            if bitrate>maxBitrate:
              maxBitrate=bitrate
              url=urlTemp
          fullUrl=base+url+"&v=1.1.12&fp=WIN%2011,3,300,268&r=&g="
          swfUrl="http://www.eurovisionsports.tv/london2012/site/Digotel.4.3.0.swf"
          VIDb64 = base64.encodestring(fullUrl).replace('\n','')
          SWFb64 = base64.encodestring(swfUrl).replace('\n','')
          fullUrl = 'http://127.0.0.1:64653/secureconne/%s/%s' % (VIDb64,SWFb64)
        elif urlMain.find(".xml")>0:
          playpath=urlMain[urlMain.find("gjmf=")+5:]
          match=re.compile('<hostname>(.+?)</hostname>', re.DOTALL).findall(content)
          base=match[0]
          match=re.compile('<appName>(.+?)</appName>', re.DOTALL).findall(content)
          app=match[0]
          match=re.compile('<authParams>(.+?)</authParams>', re.DOTALL).findall(content)
          auth=match[0].replace("&amp;","&")
          if app=="live":
            fullUrl="rtmp://"+base+"/"+app+" playpath="+playpath+"?"+auth+" swfurl=http://www.eurovisionsports.tv/london2012/site/Digotel.4.3.0.swf swfVfy=true live=true"
          elif app=="ondemand":
            fullUrl="rtmp://"+base+"/"+app+"?"+auth+" playpath="+playpath+" swfurl=http://www.eurovisionsports.tv/london2012/site/Digotel.4.3.0.swf swfVfy=true"
        listitem = xbmcgui.ListItem(path=fullUrl)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)

def cleanTitle(title):
        title=title.replace("&lt;","<").replace("&gt;",">").replace("&amp;","&").replace("&#039;","'").replace("&quot;","\"").replace("&szlig;","ß").replace("&ndash;","-")
        title=title.replace("&Auml;","Ä").replace("&Uuml;","Ü").replace("&Ouml;","Ö").replace("&auml;","ä").replace("&uuml;","ü").replace("&ouml;","ö")
        title=title.strip()
        return title

def getUrl(url):
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/13.0')
        if xbox==True:
          socket.setdefaulttimeout(30)
          response = urllib2.urlopen(req)
        else:
          response = urllib2.urlopen(req,timeout=30)
        link=response.read()
        response.close()
        return link

def parameters_string_to_dict(parameters):
        ''' Convert parameters encoded in a URL to a dict. '''
        paramDict = {}
        if parameters:
            paramPairs = parameters[1:].split("&")
            for paramsPair in paramPairs:
                paramSplits = paramsPair.split('=')
                if (len(paramSplits)) == 2:
                    paramDict[paramSplits[0]] = paramSplits[1]
        return paramDict

def addLink(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.setProperty('IsPlayable', 'true')
        liz.setProperty('mimetype', 'video/x-flv')
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz)
        return ok

def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

try:
  getUrl("http://127.0.0.1:64653/version")
  proxyIsRunning=True
except:
  proxyIsRunning=False
if not proxyIsRunning:
  xbmc.executebuiltin('RunScript('+akamaiProxyServer+')')

params=parameters_string_to_dict(sys.argv[2])
mode=params.get('mode')
url=params.get('url')
if type(url)==type(str()):
  url=urllib.unquote_plus(url)

if mode == 'listVideos':
    listVideos(url)
elif mode == 'listCategories':
    listCategories()
elif mode == 'playVideo':
    playVideo(url)
else:
    index()
