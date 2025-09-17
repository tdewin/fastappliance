#!/usr/bin/env python3
import argparse
import sys
import os
import subprocess
import tempfile

def prompt_user_to_select_file(cfg_files):
    print("Multiple .cfg files found. Please select one to process:", file=sys.stderr)
    for i, file_path in enumerate(cfg_files, start=1):
        print(f"{i}. {os.path.basename(file_path)}", file=sys.stderr)
    while True:
        try:
            choice = int(input("Enter the number of the file to process: ").strip())
            if 1 <= choice <= len(cfg_files):
                return cfg_files[choice - 1]
            else:
                print("Invalid selection. Try again.", file=sys.stderr)
        except ValueError:
            print("Please enter a valid number.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Copy lines from input file to backup file.")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("--output_file","-o", help="Path to the output file, if not set it will do inline replace")
    parser.add_argument("--backup_file","-b", help="Path to the backup file")

    parser.add_argument("--timezone","-t", default="Etc/UTC --utc", help="Timezone for new system (default: UTC)")
    parser.add_argument("--timesource","-ts", default="time.nist.gov", help="Timesource for new system")
    parser.add_argument("--keyboard","-k", default="us", help="Keyboard layout")

    parser.add_argument("--network","-n", default="", help="Single network line as defined in kickstart, eg '--bootproto=dhcp'. If empty, nothing is changed")

    parser.add_argument(
        "--staticip","-s",
        help="Optional: Static IP address to configure (e.g., 192.168.1.100)"
    )
    parser.add_argument(
        "--subnet","-m",
        help="Optional: Subnet configuration, works with staticip only",
        default="255.255.255.0"
    )
    parser.add_argument(
        "--gateway","-gw",
        help="Optional: Gateway IP address (e.g., 192.168.1.1), works with staticip only"
    )
    parser.add_argument(
        "--dnslist","-ns",
        help="Optional: Comma-separated list of DNS servers (e.g., 8.8.8.8,8.8.4.4) works with staticip only"
    )
    parser.add_argument(
        "--hostname","-hn",
        help="Optional: Hostname to assign (e.g., repo001), works with staticip only"
    )


    parser.add_argument("--confirm","-y", action="store_true",help="Remove the experimental confirm question")
    args = parser.parse_args()

    inputfile = args.input_file
    extractfile = None
    isofile = None


    outputfile = args.output_file

    grubcfg = f"/EFI/BOOT/grub.cfg"
    tmpdir = tempfile.TemporaryDirectory(delete=False)
    grubupdate = os.path.join(tmpdir.name,"grub.cfg")

    if os.path.isdir(inputfile):
      path = inputfile
      cfgs = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.cfg') and os.path.isfile(os.path.join(path, f))]
      inputfile = prompt_user_to_select_file(cfgs) 
    elif os.path.splitext(inputfile)[1].lower() == '.iso':
      try:
        t = subprocess.run(["xorriso","--help"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
      except:
        print("No xorriso detected")
        return
      result = subprocess.run(
            ['xorriso', '-indev', inputfile, '-ls', '/'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
      )
      isofile = inputfile

      cfgs = [f.strip("'") for f in result.stdout.split("\n") if f.endswith('.cfg\'') ]
      extractfile = prompt_user_to_select_file(cfgs)
      extracttmp = os.path.join(tmpdir.name,extractfile)
      subprocess.run([
            'xorriso', '-indev', inputfile , '-osirrox','on',
            '-extract', f"/{extractfile}", extracttmp
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
      )

      subprocess.run([
            'xorriso', '-indev', inputfile , '-osirrox','on',
            '-extract', grubcfg, grubupdate
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
      )


      with open(grubupdate, 'r') as f:
        lines = f.readlines()

      updated_lines = []

      linuxefi = None
      initrdefi = None
      entry = None
      p = ""
      storenext = False
      for line in lines:
          ln = line
          words = line.strip().split()
          
          if len(words) > 1:
           if words[0] == "set":
            whatset = words[1].split("=")[0].strip()
            match whatset:
                case "default":
                    ln = f'set default="ksmodautomated"\n'
                case "timeout":
                    ln = f'set timeout=20\n'
           elif words[0] == "linuxefi":
               if extractfile in ln and not "vreins" in ln:
                   linuxefi = ln
                   entry = p
                   storenext = True
           elif words[0] == "initrdefi" and storenext:
               initrdefi = ln
               storenext = False

          p = ln
          updated_lines.append(ln)

      entrysplit = entry.lstrip().split("'")
      if linuxefi and initrdefi and entry and len(entrysplit) > 2:

        

          updated_lines.append(f"\n{entrysplit[0]} 'ksmodautomated' {entrysplit[2]}")
          updated_lines.append(f"  {linuxefi.strip()} inst.assumeyes\n")
          updated_lines.append(f"  {initrdefi.lstrip()}")
          updated_lines.append("}\n")
          with open(grubupdate, 'w') as f:
            print(f"Writing updated grub to {grubupdate}",file=sys.stderr)
            f.writelines(updated_lines)
      else:
          print("Couldnt find matching entry to clone, will not update grub.cfg")

      inputfile = extracttmp
      isisoextract = True

    if not args.confirm:
      confirm = input(f"Do you understand this an experimental script only for lab environments (y/n): ").strip().lower()
      if confirm != 'y':
        return


    #print(args)

    backup_file = None

    if outputfile is None:
        outputfile = inputfile
        backup_file = inputfile + ".bkp"
        if args.backup_file:
          backup_file = args.backup_file
    elif outputfile != "-" and os.path.isdir(outputfile):
        basename = os.path.basename(inputfile)
        outputfile = os.path.join(outputfile,basename)

    networkline = ""
    if args.network != "":
        networkline = f"network {args.network}\n"
    
    if not args.staticip is None:
        if args.hostname and args.gateway and args.dnslist:
            networkline = f"network --bootproto=static --ip={args.staticip} --netmask={args.subnet} --gateway={args.gateway} --nameserver={args.dnslist} --hostname={args.hostname}\n"
        else:
            print("If you want to configure a static ip, you need to supply hostname, gateway and dnslist.. exiting",file=sys.stderr)
            return

    try:
        # Read lines from input file
        with open(inputfile, 'r') as f:
            lines = f.readlines()

        # Write lines to backup file
        if backup_file and not isisoextract:
          print(f"Making a backup to {backup_file}",file=sys.stderr)
          with open(backup_file, 'w') as f:
            f.writelines(lines)

        
        updated_lines = []
        for line in lines:
            words = line.split()
            ln = ""
            if words:
                word = words[0].lower()
                match word:
                  case "timezone":
                    ln = f"timezone {args.timezone}\n"
                  case "timesource":
                    ln = f"timesource --ntp-server {args.timesource}\n"
                  case "keyboard":
                    ln = f"keyboard --xlayouts='{args.keyboard}'\n"
                  case "network":
                    if networkline != "":
                      ln = networkline
            
            if ln != "":
                print(f"Updated {line} to {ln}",file=sys.stderr)
                updated_lines.append(ln)
            else:
                updated_lines.append(line)

        if outputfile != "-":
          with open(outputfile, 'w') as f:
            print(f"Writing update to {outputfile}",file=sys.stderr)
            f.writelines(updated_lines)
        else:
            print("".join(updated_lines))

        if not isofile is None and isofile != "":
          mod = f"{os.path.splitext(isofile)[0]}.mod.iso"
          postisoline = f"""
You can run the following command to build your iso:
ORIG="{isofile}"
MOD="{mod}"
[ -f "$MOD" ] && echo "$MOD Still exists" && rm -i $MOD
xorriso -indev "$ORIG" -outdev "$MOD" -boot_image any replay -map "{outputfile}" "/{extractfile}" "-map" "{grubupdate}" "{grubcfg}" 
"""
          try:
              print(f'Remastering {mod}')
              remaster = subprocess.run([
                    'xorriso', '-indev', isofile , '-outdev',mod,
                    '-boot_image','any','replay','-map',outputfile,f"/{extractfile}","-map",grubupdate,grubcfg
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
              )
          except subprocess.CalledProcessError as e:
              print("Couldn't remaster, maybe the existing file still exists")
              print(e.stderr)
              print(postisoline)

    except FileNotFoundError:
        print(f"Error: File {args.input_file} not found.",file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}",file=sys.stderr)

if __name__ == "__main__":
        main()
    

