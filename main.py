#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Name:       Python M-JPEG Over RSTP Client
Version:    0.1
Purpose:    This program connects to an MJPEG source and saves retrived images.
Author:     Sergey Lalov
Date:       2011-02-18
License:    GPL
Target:     Cross Platform
Require:    Python 2.6. Modules: zope.interface, twisted
"""

from twisted.internet import reactor

import rtsp_client
import rtp_mjpeg_client
import rtcp_client

def processImage(img):
    'This function is invoked by the MJPEG Client protocol'
    # Process image
    # Just save it as a file in this example
    f = open('frame.jpg', 'wb')
    f.write(img)
    f.close()

def main():
    print 'Python M-JPEG Over RSTP Client 0.1'
    config = {'request': '/jpeg',
          'login': '',
          'password': 'admin',
          'ip': '192.168.0.252',
          'port': 554,
          'udp_port': 41760,
          'callback': processImage}
    # Prepare RTP MJPEG client (technically it's a server)
    reactor.listenUDP(config['udp_port'], rtp_mjpeg_client.RTP_MJPEG_Client(config))
    reactor.listenUDP(config['udp_port'] + 1, rtcp_client.RTCP_Client()) # RTCP
    # And RSTP client
    reactor.connectTCP(config['ip'], config['port'], rtsp_client.RTSPFactory(config))
    # Run both of them
    reactor.run()
    # On exit:
    print 'Python M-JPEG Client stopped.'

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
