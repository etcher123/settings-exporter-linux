#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-2.1+
# Copyright © 2020 Collabora Ltd. <arnaud.rebillout@collabora.com>

import argparse
import os
import shutil
import subprocess
import sys
from tzlocal import get_localzone

HAVE_DBUS = False
try:
    import dbus
    HAVE_DBUS = True
except ImportError:
    pass


def print_dict(d):
    output = ''
    for key, val in d.items():
        output += '{}={}\n'.format(key, val)
    return output

def export_user_settings(outdir):

    settings = {}

    # Get timezone
    tz = get_localzone()
    settings['TZ'] = tz.zone

    # Get local details
    if HAVE_DBUS:

        LOCALE1 = 'org.freedesktop.locale1'
        DBUS_PROPS = 'org.freedesktop.DBus.Properties'

        bus = dbus.SystemBus()
        locale1 = bus.get_object(LOCALE1, '/org/freedesktop/locale1')

        locale = locale1.Get(LOCALE1, 'Locale', dbus_interface=DBUS_PROPS)
        if locale:
            settings['LOCALE'] = locale[0]

        x11layout = locale1.Get(LOCALE1, 'X11Layout', dbus_interface=DBUS_PROPS)
        x11variant = locale1.Get(LOCALE1, 'X11Variant', dbus_interface=DBUS_PROPS)
        if x11variant:
            settings['KEYBOARD'] = x11layout + ':' + x11variant
        else:
            settings['KEYBOARD'] = x11layout

        #x11model = locale1.Get(LOCALE1, 'X11Model', dbus_interface=DBUS_PROPS)

    # Print to string
    output = print_dict(settings)

    # Output
    if outdir:
        try:
            os.mkdir(outdir)
        except FileExistsError:
            pass
        
        outfile = os.path.join(outdir, 'settings.conf')
        with open(outfile, 'w') as f:
            f.write(output)

    else:
        print("# settings.conf")
        print(output)

def get_wifi_ssid():

    if not HAVE_DBUS:
        return

    NM = 'org.freedesktop.NetworkManager'
    NMCA = NM + '.Connection.Active'
    NMDW = NM + '.Device.Wireless'
    NMAP = NM + '.AccessPoint'
    DBUS_PROPS = 'org.freedesktop.DBus.Properties'

    bus = dbus.SystemBus()
    nm = bus.get_object(NM, '/org/freedesktop/NetworkManager')
    conns = nm.Get(NM, 'ActiveConnections', dbus_interface=DBUS_PROPS)
    for conn in conns:
      #print("> " + str(conn))
      active_conn = bus.get_object(NM, conn)
      devices = active_conn.Get(NMCA, 'Devices', dbus_interface=DBUS_PROPS)
      dev_name = devices[0]
      #print("  > " + str(dev_name))
      dev = bus.get_object(NM, dev_name)
      try:
          ap_name = dev.Get(NMDW, 'ActiveAccessPoint', dbus_interface=DBUS_PROPS)
      except dbus.exceptions.DBusException:
          continue
      ap = bus.get_object(NM, ap_name)
      ssid = ap.Get(NMAP, 'Ssid', dbus_interface=DBUS_PROPS, byte_arrays=True)
      if ssid:
          return ssid.decode('utf-8')

def export_wifi_settings(outdir):
    ssid = get_wifi_ssid()
    if not ssid:
        return

    fn = "/etc/NetworkManager/system-connections/{}.nmconnection".format(ssid)
    if not os.path.exists(fn):
        fn = "/etc/NetworkManager/system-connections/${}".format(ssid)
        if not os.path.exists(fn):
            return

    if outdir:
        outdir = os.path.join(outdir, 'network-connections')
        try:
            os.mkdir(outdir)
        except FileExistsError:
            pass

        outfile = os.path.join(outdir, os.path.basename(fn))
        shutil.copyfile(fn, outfile)

    else:
        print("# network-connections/{}".format(os.path.basename(fn)))
        with open(fn, 'r') as f:
            print(f.read())

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--outdir')
    args = parser.parse_args()

    export_user_settings(args.outdir)
    export_wifi_settings(args.outdir)

if __name__ == "__main__":
    sys.exit(main())
