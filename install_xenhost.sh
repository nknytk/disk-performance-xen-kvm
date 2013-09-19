#!/bin/bash
# http://wiki.centos.org/HowTos/Xen/Xen4QuickStart
# http://wiki.centos.org/HowTos/Xen/Xen4QuickStart/Xen4Libvirt

yum install sysstat
yum install -y wget
yum install centos-release-xen
yum install xen
/usr/bin/grub-bootxen.sh

yum install rsync wget vim-enhanced openssh-clients
yum install libvirt python-virtinst libvirt-daemon-xen

mkdir -p /etc/polkit-1/localauthority/50-local.d/
echo "[Remote libvirt SSH access]
Identity=unix-group:group_name
Action=org.libvirt.unix.manage
ResultAny=yes
ResultInactive=yes
ResultActive=yes" > /etc/polkit-1/localauthority/50-local.d/50-libvirt-remote-access.pkla
groupadd remote-libvirt 
useradd windows8
usermod -G remote-libvirt windows8 root

echo "
Caution !!!
You should enable xend-http-server to use remote virt-manager.

vi /etc/xen/xend-config.sxp
(xend-http-server yes)
" | tee -a readme4virtmanager

reboot
