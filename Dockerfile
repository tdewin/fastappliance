FROM fedora

RUN dnf update -y && dnf install -y xorriso python3 curl
VOLUME /iso 
WORKDIR /app
ADD https://raw.githubusercontent.com/tdewin/fastappliance/refs/heads/main/ksmod.py /app
RUN chmod +x /app/ksmod.py

WORKDIR /iso
