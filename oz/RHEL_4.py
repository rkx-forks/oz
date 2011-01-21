# Copyright (C) 2010  Chris Lalancette <clalance@redhat.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import Guest
import shutil
import re
import ozutil
import RedHat

class RHEL4Guest(RedHat.RedHatCDGuest):
    def __init__(self, tdl, config, nicmodel, diskbus):
        self.tdl = tdl
        self.ks_file = ozutil.generate_full_auto_path("rhel-4-jeos.ks")

        if self.tdl.installtype == 'url':
            self.url = self.tdl.url
            ozutil.deny_localhost(self.url)
        elif self.tdl.installtype == 'iso':
            self.url = self.tdl.iso
        else:
            raise Guest.OzException("RHEL-4 installs must be done via url or iso")

        RedHat.RedHatCDGuest.__init__(self, "RHEL-4", self.tdl.update,
                                      self.tdl.arch, self.tdl.installtype,
                                      nicmodel, None, None, diskbus, config)

    def modify_iso(self):
        self.log.debug("Putting the kickstart in place")

        shutil.copy(self.ks_file, self.iso_contents + "/ks.cfg")

        self.log.debug("Modifying the boot options")
        f = open(self.iso_contents + "/isolinux/isolinux.cfg", "r")
        lines = f.readlines()
        f.close()
        for line in lines:
            if re.match("timeout", line):
                lines[lines.index(line)] = "timeout 1\n"
            elif re.match("default", line):
                lines[lines.index(line)] = "default customiso\n"
        lines.append("label customiso\n")
        lines.append("  kernel vmlinuz\n")
        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg method="
        if self.tdl.installtype == "url":
            initrdline += self.url + "\n"
        else:
            initrdline += "cdrom:/dev/cdrom\n"
        lines.append(initrdline)

        f = open(self.iso_contents + "/isolinux/isolinux.cfg", "w")
        f.writelines(lines)
        f.close()

    def check_dvd(self):
        f = open(self.iso_contents + "/.discinfo")
        lines = f.readlines()
        f.close()

        if not lines[1].startswith("Red Hat Enterprise Linux 4."):
            raise Guest.OzException("Invalid .discinfo file on ISO")
        if lines[2].strip() != self.arch:
            raise Guest.OzException("Invalid .discinfo architecture on ISO")
        if lines[3].strip() != "1,2,3,4,5":
            raise Guest.OzException("Only DVDs are supported for RHEL-4 ISO installs")

    def generate_install_media(self, force_download):
        self.log.info("Generating install media")
        fetchurl = self.url
        if self.tdl.installtype == 'url':
            fetchurl += "/images/boot.iso"
        self.get_original_iso(fetchurl, force_download)
        self.copy_iso()
        if self.tdl.installtype == 'iso':
            self.check_dvd()
        self.modify_iso()
        self.generate_iso()
        self.cleanup_iso()

def get_class(tdl, config):
    if tdl.update in ["GOLD", "U1", "U2", "U3", "U4", "U5", "U6", "U7"]:
        return RHEL4Guest(tdl, config, "rtl8139", None)
    if tdl.update in ["U8"]:
        return RHEL4Guest(tdl, config, "virtio", "virtio")
    raise Guest.OzException("Unsupported RHEL-4 update " + tdl.update)
