# -*- coding: utf-8 -*-
'This module handles RTSP conversation'
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from base64 import b64encode
from os.path import basename
import rtp_audio_client
import rtcp_client

debug = 1

class RTSPClient(Protocol):
    def __init__(self):
        self.config = {}
        self.wait_description = False

    def connectionMade(self):
        self.session = 1
        # Authorization part
        if self.config['login']:
            authstring = 'Authorization: Basic ' + b64encode(self.config['login']+':'+self.config['password']) + '\r\n'
        else:
            authstring = ''
        # send OPTIONS request
        to_send = """\
OPTIONS rtsp://""" + self.config['ip'] + self.config['request'] + """ RTSP/1.0\r
""" + authstring + """CSeq: 1\r
User-Agent: Python MJPEG Client\r
\r
"""
        self.transport.write(to_send)
        if debug:
            print 'We say:\n', to_send

    def dataReceived(self, data):
        if debug:
            print 'Server said:\n', data
        # Unify input data
        data_ln = data.lower().strip().split('\r\n', 5)
        # Next behaviour is relevant to CSeq
        # which defines current conversation state
        if data_ln[0] == 'rtsp/1.0 200 ok' or self.wait_description:
            # There might be an audio stream
            if 'audio_track' in self.config:
                cseq_audio = 1
            else:
                cseq_audio = 0
            to_send = ''
            if 'cseq: 1' in data_ln:
                # CSeq 1 -> DESCRIBE
                to_send = """\
DESCRIBE rtsp://""" + self.config['ip'] + self.config['request'] + """ RTSP/1.0\r
CSeq: 2\r
Accept: application/sdp\r
User-Agent: Python MJPEG Client\r
\r
"""
            elif 'cseq: 2' in data_ln or self.wait_description:
                # CSeq 2 -> Parse SDP and then SETUP
                data_sp = data.lower().strip().split('\r\n\r\n', 1)
                # wait_description is used when SDP is sent in another UDP
                # packet
                if len(data_sp) == 2 or self.wait_description:
                    # SDP parsing
                    video = audio = False
                    is_MJPEG = False
                    video_track = ''
                    audio_track = ''
                    if len(data_sp) == 2:
                        s = data_sp[1].lower()
                    elif self.wait_description:
                        s = data.lower()
                    for line in s.strip().split('\r\n'):
                        if line.startswith('m=video'):
                            video = True
                            audio = False
                            if line.endswith('26'):
                                is_MJPEG = True
                        if line.startswith('m=audio'):
                            video = False
                            audio = True
                            self.config['udp_port_audio'] = int(line.split(' ')[1])
                        if video:
                            params = line.split(':', 1)
                            if params[0] == 'a=control':
                                video_track = params[1]
                        if audio:
                            params = line.split(':', 1)
                            if params[0] == 'a=control':
                                audio_track = params[1]
                    if not is_MJPEG:
                        print "Stream", self.config['ip'] + self.config['request'], 'is not an MJPEG stream!'
                    if video_track: self.config['video_track'] = 'rtsp://' + self.config['ip'] + self.config['request'] + '/trackID=0' 
                    if audio_track: self.config['audio_track'] = 'rtsp://' + self.config['ip'] + self.config['request'] + '/trackID=1'
                    to_send = """\
SETUP """ + self.config['video_track'] + """ RTSP/1.0\r
CSeq: 3\r
Transport: RTP/AVP;unicast;client_port=""" + str(self.config['udp_port']) + """-"""+ str(self.config['udp_port'] + 1) + """\r
User-Agent: Python MJPEG Client\r
\r
"""
                    self.wait_description = False
                else:
                    # Do not have SDP in the first UDP packet, wait for it
                    self.wait_description = True
            elif "cseq: 3" in data_ln and 'audio_track' in self.config:
                # CSeq 3 -> SETUP audio if present
                self.session = data_ln[5].strip().split(' ')[1]
                to_send = """\
SETUP """ + self.config['audio_track'] + """ RTSP/1.0\r
CSeq: 4\r
Transport: RTP/AVP;unicast;client_port=""" + str(self.config['udp_port_audio']) + """-"""+ str(self.config['udp_port_audio'] + 1) + """\r
Session: """ + self.session + """\r
User-Agent: Python MJPEG Client\r
\r
"""
                reactor.listenUDP(self.config['udp_port_audio'], rtp_audio_client.RTP_AUDIO_Client(self.config))
                reactor.listenUDP(self.config['udp_port_audio'] + 1, rtcp_client.RTCP_Client()) # RTCP
            elif "cseq: "+str(3+cseq_audio) in data_ln:
                # PLAY
                to_send = """\
PLAY rtsp://""" + self.config['ip'] + self.config['request'] + """/ RTSP/1.0\r
CSeq: """ + str(4+cseq_audio) + """\r
Session: """ + self.session + """\r
Range: npt=0.000-\r
User-Agent: Python MJPEG Client\r
\r
"""
            elif "cseq: "+str(4+cseq_audio) in data_ln:
                if debug:
                    print 'PLAY'
                pass

            elif "cseq: "+str(5+cseq_audio) in data_ln:
                if debug:
                    print 'TEARDOWN'
                pass

            if to_send:
                self.transport.write(to_send)
                if debug:
                    print 'We say:\n', to_send

class RTSPFactory(ClientFactory):

    def __init__(self, config):
        self.protocol = RTSPClient
        self.config = config
    def buildProtocol(self, addr):
        prot = ClientFactory.buildProtocol(self, addr)
        prot.config = self.config
        return prot

    def clientConnectionLost(self, connector, reason):
        print 'Reconnecting'
        connector.connect()
