# Modifying the infra appliance iso

These instructions explain how to create a modified iso. You can then copy that iso to a usb stick for example or boot via a remote console from the iso file.

These instructions where tested on a Fedora 42 system, but they should work on other systems as well like Rocky Linux

# Identify iso and usb stick (if you want to copy the image to usb)
You can use dmesg with -W to follow the kernel log. Do this before plugging in the device and you will be able to identify which /dev name is given to it. Then double check with lsblk.

Make sure you have download the JeOS
```bash
sudo dmesg -W
lsblk
ls *JeOS*
```

# installing prereq
```bash
sudo dnf install -y lorax
```
# remove old mods

```bash
rm *.mod.iso -i
```

# setting up path variables
```bash
JEOS=$(realpath $(find -iname '*JeOS*.iso'))
MOD="${JEOS%.*}.mod.iso"
```

if you are trying to mod the Veeam Software Appliance (VBR), you can modify the JEOS variable as such
```bash
JEOS=$(realpath $(find -iname 'VeeamSoftwareAppliance*.iso'))
MOD="${JEOS%.*}.mod.iso"
```

if everything went ok, you should have the $JEOS set to the fullpath of your iso
```bash
echo "$JEOS"
echo "$MOD"
```


# extracting kickstart
using cat creates the file with the current user (cp copies the permissions)

```bash
KS=hardened-repo-ks.cfg
```

if you are trying to mod the Veeam Software Appliance (VBR)
```bash
KS=vbr-ks.cfg
```


```bash
mkdir -p extract
sudo mount $JEOS extract
cat extract/$KS > $KS
sudo umount $JEOS
```



# updating the kickstart

some helper variables if you want to setup a static ip. You might considering reservering an "installer ip". This way during post installation, you only have to change the last digits of the ip address and you dont need to specify the GW nor the DNS
```bash
N="192.168.0"
M="255.255.255.0"
IP=81
RNAME="repo001"
```

download the ksmod.py script to update the kickstart file. Alternatively, you can modify the file with nano or vim, or using inline sed commando's
```bash
curl -O https://raw.githubusercontent.com/tdewin/fastappliance/refs/heads/main/ksmod.py
chmod +x ksmod.py
./ksmod.py --timezone 'Europe/Brussels --utc' \
--timesource "time.cloudflare.com --nts" \
--keyboard "be" \
--network "--bootproto=static --ip=$N.$IP --netmask=$M --gateway=$N.1 --nameserver=$N.1 --hostname=$RNAME" \
$KS
```

check your changes
```bash
cat $KS | grep -E '^(network|keyb|time)'
```


# injecting the kickstart script
based on:
https://docs.rockylinux.org/10/guides/isos/iso_creation/
https://forums.rockylinux.org/t/create-custom-rocky-iso/7724

```bash
sudo mkksiso --ks $KS $JEOS $MOD
sudo chown $USER:$USER $MOD
```

it seems directly calling xorriso might also work.
```bash
sudo xorriso -indev $JEOS \
-outdev $MOD \
-add $KS
sudo chown $USER:$USER $MOD
```

# Verify the changes
```bash
sudo mount $MOD extract
cat extract/$KS | grep -E '^(network|keyb|time)'
sudo umount $MOD
```

# Building a usb stick
When the command is done, you should be able to start your custom iso
```bash
sudo dd if=$MOD of=/dev/sdc bs=4M status=progress oflag=direct
```

# Testing with KVM/virsh
Alternatively, test the vm with virsh/virt-install

```bash
virt-install \
-n $RNAME \
--description "$(printf 'Veeam Backup & Replication auto deploytest %s' $RNAME)" \
--graphics=spice \
--boot=uefi \
--os-variant=rocky9 \
--ram=4096 \
--vcpus=4 \
--disk pool=gnome-boxes,bus=virtio,size=240 \
--disk pool=gnome-boxes,bus=virtio,size=245 \
--cdrom $MOD \
--network network=br0 \
--noautoconsole
```

add `--check disk_size=off` to overprovision

when you are done, you can delete the vm and it disks
```bash
virsh destroy $RNAME; virsh undefine $RNAME --nvram --remove-all-storage
```
