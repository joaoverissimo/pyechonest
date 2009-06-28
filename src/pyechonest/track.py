#!/usr/bin/env python
# encoding: utf-8
"""
A Python interface to the The Echo Nest's web API.  See
http://developer.echonest.com/ for details.
"""

from pyechonest.decorators import memoized
from pyechonest import util, config
import os

class Track(object):
    def __init__(self, identifier):
        if len(identifier)==18:
            identifier = 'music://id.echonest.com/~/TR/' + identifier
        self._identifier = identifier

    # These guys are all list of events (beats, etc)
    
    @property
    @memoized
    def bars(self):
        params = {'id': self.identifier}
        return parseToListOfEvents(util.call('get_bars', params).findall("analysis/bar"))

    @property
    @memoized
    def beats(self):
        params = {'id': self.identifier}
        return parseToListOfEvents(util.call('get_beats', params).findall("analysis/beat"))

    @property
    @memoized
    def tatums(self):
        params = {'id': self.identifier}
        return parseToListOfEvents(util.call('get_tatums', params).findall("analysis/tatum"))


    # These guys are all single float #s    
    
    @property
    @memoized
    def duration(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_duration', params).findall("analysis/duration"))
        
    @property
    @memoized
    def end_of_fade_in(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_end_of_fade_in', params).findall("analysis/end_of_fade_in"))
        
    @property
    @memoized
    def key(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_key', params).findall("analysis/key"),with_confidence=True)

    @property
    @memoized
    def loudness(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_loudness', params).findall("analysis/loudness"))

    @property
    @memoized
    def mode(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_mode', params).findall("analysis/mode"),with_confidence=True)

    @property
    @memoized
    def start_of_fade_out(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_start_of_fade_out', params).findall("analysis/start_of_fade_out"))

    @property
    @memoized
    def tempo(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_tempo', params).findall("analysis/tempo"),with_confidence=True)

    @property
    @memoized
    def time_signature(self):
        params = {'id': self.identifier}
        return parseToFloat(util.call('get_time_signature', params).findall("analysis/time_signature"),with_confidence=True)


    # And now the "special ones"
    
    @property
    @memoized
    def sections(self):
        params = {'id':self.identifier}
        tree = util.call('get_sections', params)
        output = []
        nodes = tree.findall('analysis/section')
        for n in nodes:
            start = float(n.attrib.get('start'))
            duration = float(n.attrib.get('duration'))
            output.append({"start":start,"duration":duration})
        return output

    @property
    @memoized
    def metadata(self):
        params = {'id':self.identifier}
        tree = util.call('get_metadata', params)
        output = {}
        for n in tree.findall("analysis")[0].getchildren():
            output[n.tag] = n.text
        return output

    @property
    @memoized
    def segments(self):
        params = {'id':self.identifier}
        tree = util.call('get_segments', params)
        output = []
        nodes = tree.findall('analysis/segment')
        for n in nodes:
            start = float(n.attrib.get('start'))
            duration = float(n.attrib.get('duration'))

            loudnessnodes = n.findall('loudness/dB')
            loudness_end = None
            for l in loudnessnodes:
                if 'type' in l.attrib:
                    time_loudness_max = float(l.attrib.get('time'))
                    loudness_max = float(l.text)
                else:
                    if float(l.attrib.get('time'))!=0:
                        loudness_end = float(l.text)
                    else:
                        loudness_begin = float(l.text)

            pitchnodes = n.findall('pitches/pitch')
            pitches=[]
            for p in pitchnodes:
                pitches.append(float(p.text))

            timbrenodes = n.findall('timbre/coeff')
            timbre=[]
            for t in timbrenodes:
                timbre.append(float(t.text))

            output.append({"start":start,"duration":duration,"pitches":pitches,"timbre":timbre,"loudness_begin":loudness_begin,
                            "loudness_max":loudness_max,"time_loudness_max":time_loudness_max,"loudness_end":loudness_end})
        return output
        
    @property
    def identifier(self):
        """A unique identifier for a track.
        See http://developer.echonest.com/docs/datatypes/
        for more information"""
        return self._identifier

    @property
    def thing_id(self):
        return self._identifier.split('/')[-1]

    def __repr__(self):
        return "<Track '%s'>" % self.name
    
    def __str__(self):
        return self.name


TRUTH = {True: 'Y', False: 'N'}

def upload(filename_or_url, wait=True):
    """
    Upload a file or give a URL to the EN analyze API. If you call this with wait=False it will return immediately.
    """
    if not filename_or_url.startswith("http://"):
        if os.path.isfile( filename_or_url ) : 
            # If file, upload using POST
            response = util.postChunked( host = config.API_HOST, 
                                     selector = config.API_SELECTOR + "upload",
                                     fields = {"api_key":config.ECHO_NEST_API_KEY, "wait":TRUTH[wait], 'version': 3}, 
                                     files = (( 'file', open(filename_or_url, 'rb')), )
                                     )
            response = util.parse_http_response(response).findall("track")
        else:
            raise Exception("File " + filename_or_url + " not found.")
    else :
        # Assume the filename is a URL. Call the upload method w/o a post.
        response = util.call('upload',{'url':filename_or_url, "wait":TRUTH[wait]}, POST=True).findall("track")
    
    if(len(response)>0):
        return Track(response[0].attrib.get("id"))
    else:
        return None

def parseToListOfEvents(evs):
    """
    parser for the list of events type calls
    """    
    events = []
    for x in evs:
        event = {}
        event["start"] = float(x.text)
        event["confidence"] = float(x.attrib.get("confidence"))
        events.append(event)
    return events
    
def parseToFloat(evs, with_confidence=False):
    """
    parser for the single float-type calls
    """
    ret = {}
    if(len(evs)):
        if(with_confidence):
            return {"value":float(evs[0].text), "confidence":float(evs[0].attrib.get("confidence"))}
        else:
            return {"value":float(evs[0].text)}
