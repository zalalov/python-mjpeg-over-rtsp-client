# -*- coding: utf-8 -*-
"This module handles RTSP conversation"
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from base64 import b64encode
from os.path import basename
import rtp_audio_client
import rtcp_client

debug = 1


class RTSPClient(Protocol):
    def __init__(self):
        """
        Constructor
        """
        self.config = {}
        self.wait_description = False

    def connectionMade(self):
        self.session = "1"
        options_req = self.options_req()
        self.transport.write(options_req)

        if debug:
            print "We say:\n", options_req

    def get_authstring(self):
        """
        Returns string for authentication (Basic base64)
        :return:
        """
        if self.config["login"]:
            return "Authorization: Basic " + b64encode(self.config["login"]+":"+self.config["password"])
        else:
            return ""

    @staticmethod
    def get_useragent():
        """
        Get User-Agent string
        :return:
        """
        return "LibVLC/2.2.1 (LIVE555 Streaming Media v2014.07.25)"

    def options_req(self):
        """
        OPTIONS request
        :return:
        """
        req = "OPTIONS rtsp://%s%s %s" % (self.config["ip"], self.config["request"], " RTSP/1.0\r\n")
        req += self.get_authstring() + "\r\n"
        req += "CSeq: 1\r\n"
        req += "User-Agent: %s\r\n\r\n" % self.get_useragent()

        return req

    def describe_req(self):
        """
        DESCRIBE request
        :return:
        """
        req = "DESCRIBE rtsp://%s%s RTSP/1.0\r\n" % (self.config["ip"], self.config["request"])
        req += self.get_authstring() + "\r\n"
        req += "CSeq: 2\r\n"
        req += "Accept: application/sdp\r"
        req += "User-Agent: %s\r\n\r\n" % self.get_useragent()

        return req

    def setup_req(self, cseq, track, ports):
        """
        SETUP request
        :param cseq:
        :param track:
        :param ports:
        :return:
        """
        req = "SETUP %s RTSP/1.0r\n" % track
        req += "CSeq: %s\r\n" % cseq
        req += "Transport: RTP/AVP;unicast;client_port=%s-%s\r\n" % ports
        req += "Session: %s\r\n" % self.session
        req += "User-Agent: %s\r\n\r\n" % self.get_useragent()

        return req

    def play_req(self, cseq):
        """
        PLAY request
        :param cseq:
        :return:
        """
        req = "PLAY rtsp://%s:%s%s RTSP/1.0\r\n""" % (self.config["ip"], self.config["port"], self.config["request"])
        req += "CSeq: %s\r\n" % str(cseq)
        req += self.get_authstring() + "\r\n"
        req += "Session: %s\r\n" % self.session
        req += "Range: npt=0.000-\r\n"
        req += "User-Agent: %s" % self.get_useragent() + "\r\n\r\n"

        return req

    def dataReceived(self, data):
        if debug:
            print "Server said:\n", data

        data_ln = data.lower().strip().split("\r\n", 5)

        if data_ln[0] == "rtsp/1.0 200 ok" or self.wait_description:
            if "audio_track" in self.config:
                cseq_audio = 1
            else:
                cseq_audio = 0
            to_send = ""

            if "cseq: 1" in data_ln:
                to_send = self.describe_req()
            elif "cseq: 2" in data_ln or self.wait_description:
                data_sp = data.lower().strip().split("\r\n\r\n", 1)

                if len(data_sp) == 2 or self.wait_description:
                    video = audio = False
                    is_MJPEG = False
                    video_track = ""
                    audio_track = ""

                    if len(data_sp) == 2:
                        s = data_sp[1].lower()
                    elif self.wait_description:
                        s = data.lower()

                    for line in s.strip().split("\r\n"):
                        if line.startswith("m=video"):
                            video = True
                            audio = False
                            if line.endswith("26"):
                                is_MJPEG = True

                        if line.startswith("m=audio"):
                            video = False
                            audio = True
                            self.config["udp_port_audio"] = int(line.split(" ")[1])

                        if video:
                            params = line.split(":", 1)
                            if params[0] == "a=control":
                                video_track = params[1]

                        if audio:
                            params = line.split(":", 1)
                            if params[0] == "a=control":
                                audio_track = params[1]
                    if not is_MJPEG:
                        print "Stream", self.config["ip"] + self.config["request"], "is not an MJPEG stream!"

                    if video_track:
                        self.config["video_track"] = "rtsp://%s/trackID=0" % (self.config["ip"] + self.config["request"])

                    if audio_track:
                        self.config["audio_track"] = "rtsp://" + self.config["ip"] + self.config["request"] + "/trackID=1"

                    to_send = self.setup_req(3, self.config["video_track"], (str(self.config["udp_port"]), str(self.config["udp_port"] + 1)))
                    self.wait_description = False
                else:
                    self.wait_description = True
            elif "cseq: 3" in data_ln and "audio_track" in self.config:
                self.session = data_ln[3].split(";")[0].split()[1]
                to_send = self.setup_req(4, self.config["audio_track"], (str(self.config["udp_port_audio"]), str(self.config["udp_port_audio"] + 1)))
            elif "cseq: "+str(3 + cseq_audio) in data_ln:
                to_send = self.play_req(str(4 + cseq_audio))
            elif "cseq: "+str(4 + cseq_audio) in data_ln:
                if debug:
                    print "PLAY"
                pass
            elif "cseq: "+str(5 + cseq_audio) in data_ln:
                if debug:
                    print "TEARDOWN"
                pass

            if to_send:
                self.transport.write(to_send)

                if debug:
                    print "We say:\n", to_send

class RTSPFactory(ClientFactory):

    def __init__(self, config):
        self.protocol = RTSPClient
        self.config = config

    def buildProtocol(self, addr):
        prot = ClientFactory.buildProtocol(self, addr)
        prot.config = self.config

        return prot

    def clientConnectionLost(self, connector, reason):
        connector.connect()
