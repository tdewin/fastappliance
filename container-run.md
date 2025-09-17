# build
```
mkdir -p ksmod/iso && cd ksmod
cat << EOF > Dockerfile
FROM fedora

RUN dnf update -y && dnf install -y xorriso python3 curl
VOLUME /iso 
WORKDIR /app
ADD https://raw.githubusercontent.com/tdewin/fastappliance/refs/heads/main/ksmod.py /app
RUN chmod +x /app/ksmod.py

WORKDIR /iso
EOF
podman build -t ksmod .
```

# generate
```
# :z is required for selinux, but if you are running docker, this probably can be ommited
podman run -it --rm -v `pwd`/iso:/iso:z ksmod

#replace something here with the correct parameters. go to my.veeam.com, start the download, cancel quickly but copy the link
#notice that you might only have to do this once
curl -O https://<somethinghere>.veeam.com/<somethinghere>/VeeamJeOS_13.0.0.4967_20250822.iso

touch postmod.cfg
/app/ksmod.py --postmod postmod.cfg --keyboard "be" --timezone "Europe/Brussels --utc" --timesource "time.cloudflare.com --nts" VeeamJeOS_13.0.0.4967_20250822.iso --staticip "192.168.0.81" --hostname "autorepo01" --gateway "192.168.0.1" --subnet "255.255.255.0" --dnslist "192.168.0.1"

exit
```

# mess around with selinux if you are using podman

This should not be required if you are running docker and containers as root per default or you don't experience selinux issue

Pre context, if you predownload the iso, or have a a postmod.cfg, you need to put the container context on those files
```
chcon -Rt container_file_t iso
ls -lZ iso
```

Post generation, you might want to change the context to user_home_t so you can use it. It will move the modded iso outside the folder and change it to the user_home_t context for only that file
```
mv iso/*.mod.iso .
chcon -t user_home_t *.mod.iso
```

# virsh test
```
RNAME=testdeploy
virt-install -n $RNAME --description "$(printf 'Veeam Backup & Replication auto deploytest %s' $RNAME)" --graphics=spice --boot=uefi --os-variant=rocky9 --ram=4096 --vcpus=4 --disk pool=gnome-boxes,bus=virtio,size=240 --disk pool=gnome-boxes,bus=virtio,size=245 --cdrom VeeamJeOS_13.0.0.4967_20250822.mod.iso --network network=br0 --check disk_size=off
# when you are done
# virsh destroy $RNAME; virsh undefine --nvram --remove-all-storage $RNAME
```

