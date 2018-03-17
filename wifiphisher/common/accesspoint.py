"""
This module was made to fork the rogue access point
"""
import os
import time
import subprocess
import wifiphisher.common.constants as constants
import roguehostapd.config.hostapdconfig as hostapdconfig
import roguehostapd.apctrl as apctrl


class AccessPoint(object):
    """
    This class forks the softAP
    """

    def __init__(self):
        """
        Setup the class with all the given arguments
        :param self: An AccessPoint object
        :type self: AccessPoint
        :return: None
        :rtype: None
        """

        self.interface = None
        self.internet_interface = None
        self.channel = None
        self.essid = None
        self.psk = None
        self.force_hostapd = False
        # roguehostapd object
        self.hostapd_object = None
        self.deny_mac_addrs = []

    def enable_system_hostapd(self):
        """
        Set the interface for the softAP
        :param self: An AccessPoint object
        :type self: AccessPoint
        :return: None
        :rtype: None
        ..note: use hostapd on the system instead of using roguehostapd
        """
        self.force_hostapd = True

    def set_interface(self, interface):
        """
        Set the interface for the softAP
        :param self: An AccessPoint object
        :param interface: interface name
        :type self: AccessPoint
        :type interface: str
        :return: None
        :rtype: None
        """

        self.interface = interface

    def add_deny_macs(self, deny_mac_addrs):
        """
        Add the deny mac addresses
        :param self: An AccessPoint object
        :param deny_mac_addrs: list of deny mac addresses
        :type self: AccessPoint
        :type deny_mac_addrs: list
        :return: None
        :rtype: None
        """

        self.deny_mac_addrs.extend(deny_mac_addrs)

    def set_internet_interface(self, interface):
        """
        Set the internet interface
        :param self: An AccessPoint object
        :param interface: interface name
        :type self: AccessPoint
        :type interface: str
        :return: None
        :rtype: None
        """

        self.internet_interface = interface

    def set_channel(self, channel):
        """
        Set the channel for the softAP
        :param self: An AccessPoint object
        :param channel: channel number
        :type self: AccessPoint
        :type channel: str
        :return: None
        :rtype: None
        """

        self.channel = channel

    def set_essid(self, essid):
        """
        Set the ssid for the softAP
        :param self: An AccessPoint object
        :param essid: SSID for the softAP
        :type self: AccessPoint
        :type essid: str
        :return: None
        :rtype: None
        """

        self.essid = essid

    def set_psk(self, psk):
        """
        Set the psk for the softAP
        :param self: An AccessPoint object
        :param psk: passphrase for the softAP
        :type self: AccessPoint
        :type psk: str
        :return: None
        :rtype: None
        """

        self.psk = psk

    def start_dhcp_dns(self):
        """
        Start the dhcp server
        :param self: An AccessPoint object
        :type self: AccessPoint
        :return: None
        :rtype: None
        """

        config = ('no-resolv\n' 'interface=%s\n' 'dhcp-range=%s\n')

        with open('/tmp/dhcpd.conf', 'w') as dhcpconf:
            dhcpconf.write(config % (self.interface, constants.DHCP_LEASE))

        with open('/tmp/dhcpd.conf', 'a+') as dhcpconf:
            if self.internet_interface:
                dhcpconf.write("server=%s" % (constants.PUBLIC_DNS, ))
            else:
                dhcpconf.write("address=/#/%s" % (constants.NETWORK_GW_IP, ))
        # catch the exception if dnsmasq is not installed
        try:
            subprocess.Popen(
                ['dnsmasq', '-C', '/tmp/dhcpd.conf'],
                stdout=subprocess.PIPE,
                stderr=constants.DN)
        except OSError:
            print("[" + constants.R + "!" + constants.W + "] " +
                  "dnsmasq is not installed!")
            raise Exception

        subprocess.Popen(
            ['ifconfig', str(self.interface), 'mtu', '1400'],
            stdout=constants.DN,
            stderr=constants.DN)

        subprocess.Popen(
            [
                'ifconfig',
                str(self.interface), 'up', constants.NETWORK_GW_IP, 'netmask',
                constants.NETWORK_MASK
            ],
            stdout=constants.DN,
            stderr=constants.DN)
        # Give it some time to avoid "SIOCADDRT: Network is unreachable"
        time.sleep(1)
        # Make sure that we have set the network properly.
        proc = subprocess.check_output(['ifconfig', str(self.interface)])
        if constants.NETWORK_GW_IP not in proc:
            return False

    def start(self):
        """
        Start the softAP
        :param self: An AccessPoint object
        :type self: AccessPoint
        :return: None
        :rtype: None
        """

        # create the configuration for roguehostapd
        hostapd_config = {
            "ssid": self.essid,
            "interface": self.interface,
            "channel": self.channel,
            "deny_macs": self.deny_mac_addrs,
        }
        if self.psk:
            hostapd_config['wpa2password'] = self.psk
        self.hostapd_object = apctrl.Hostapd()
        if not self.force_hostapd:
            try:
                hostapd_config["karma_enable"] = 1
                hostapd_config["wpspbc"] = True
                hostapd_options = {
                    'mute': True,
                    "eloop_term_disable": True
                }
                self.hostapd_object.start(hostapd_config, hostapd_options)
            except KeyboardInterrupt:
                raise Exception
            except BaseException:
                print("[" + constants.R + "!" + constants.W + "] " +
                      "roguehostapd is not installed! You can supply --force-hostapd"
                      " to use the hostapd installed on the system instead")
                # just raise exception when hostapd is not installed
                raise Exception
        else:
            # use the hostapd on the users' system
            self.hostapd_object.create_hostapd_conf_file(hostapd_config,
                                                         {})
            try:
                self.hostapd_object = subprocess.Popen(
                    ['hostapd', hostapdconfig.ROGUEHOSTAPD_RUNTIME_CONFIGPATH],
                    stdout=constants.DN,
                    stderr=constants.DN)
            except OSError:
                print("[" + constants.R + "!" + constants.W + "] " +
                      "hostapd is not installed!")
                # just raise exception when hostapd is not installed
                raise Exception

            time.sleep(2)
            if self.hostapd_object.poll() is not None:
                print("[" + constants.R + "!" + constants.W + "] " +
                      "hostapd failed to lunch!")
                raise Exception

    def on_exit(self):
        """
        Clean up the resoures when exits
        :param self: An AccessPoint object
        :type self: AccessPoint
        :return: None
        :rtype: None
        """

        subprocess.call('pkill dnsmasq', shell=True)
        try:
            self.hostapd_object.stop()
        except BaseException:
            subprocess.call('pkill hostapd', shell=True)
            if os.path.isfile(hostapdconfig.ROGUEHOSTAPD_RUNTIME_CONFIGPATH):
                os.remove(hostapdconfig.ROGUEHOSTAPD_RUNTIME_CONFIGPATH)
            if os.path.isfile(hostapdconfig.ROGUEHOSTAPD_DENY_MACS_CONFIGPATH):
                os.remove(hostapdconfig.ROGUEHOSTAPD_DENY_MACS_CONFIGPATH)

        if os.path.isfile('/var/lib/misc/dnsmasq.leases'):
            os.remove('/var/lib/misc/dnsmasq.leases')
        if os.path.isfile('/tmp/dhcpd.conf'):
            os.remove('/tmp/dhcpd.conf')
        # sleep 2 seconds to wait all the hostapd process is
        # killed
        time.sleep(2)
