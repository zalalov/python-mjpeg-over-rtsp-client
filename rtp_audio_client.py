# -*- coding: utf-8 -*-
"""
This module handles audio stream. It's not complete since there is
no decoding for RTP payload, which could be realised in rfc2198pcm module
"""
import rtp_datagram
#import rfc2198pcm

from twisted.internet.protocol import DatagramProtocol

class RTP_AUDIO_Client(DatagramProtocol):
    def __init__(self, config):
        self.config = config
        self.prevSeq = -1
        self.lost_packet = 0
        #self.audio = rfc2198pcm.PCM()

    def datagramReceived(self, datagram, address):
        rtp_dg = rtp_datagram.RTPDatagram()
        rtp_dg.Datagram = datagram
        rtp_dg.parse()
        if self.prevSeq != -1:
            if (rtp_dg.SequenceNumber != self.prevSeq + 1) and rtp_dg.SequenceNumber != 0:
                self.lost_packet = 1
        self.prevSeq = rtp_dg.SequenceNumber
        if rtp_dg.PayloadType == 0: # PCM audio
            #self.audio.Datagram = rtp_dg.Payload
            #self.audio.parse()
            #self.config['callback_audio'](self.audio.PCMBuffer)
            #if self.lost_packet:
            #    print "RTP audio packet lost"
            #    self.lost_packet = 0
            pass
