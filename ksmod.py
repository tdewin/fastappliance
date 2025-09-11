#!/usr/bin/env python3
import argparse


def main():
    parser = argparse.ArgumentParser(description="Copy lines from input file to backup file.")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("--output_file","-o", help="Path to the output file, if not set it will do inline replace")

    parser.add_argument("--timezone", default="Etc/UTC --utc", help="Timezone for new system (default: UTC)")
    parser.add_argument("--timesource", default="time.nist.gov", help="Timesource for new system")
    parser.add_argument("--keyboard", default="us", help="Keyboard layout")
    parser.add_argument("--network", default="", help="Keyboard layout")
    parser.add_argument("--confirm", action="store_true",help="Remove the experimental confirm question")

    parser.add_argument("--backup_file", help="Path to the backup file")
    args = parser.parse_args()


    if not args.confirm:
      confirm = input(f"Do you understand this an experimental script only for lab environments (y/n): ").strip().lower()
      if confirm != 'y':
        return


    #print(args)

    backup_file = None

    outputfile = args.output_file
    if outputfile is None:
        outputfile = args.input_file
        backup_file = args.input_file + ".bkp"
        if args.backup_file:
          backup_file = args.backup_file

    networkline = ""
    if args.network != "":
        networkline = f"network {args.network}\n"

    try:
        # Read lines from input file
        with open(args.input_file, 'r') as f:
            lines = f.readlines()

        # Write lines to backup file
        if backup_file:
          print(f"Making a backup to {backup_file}")
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
                print(f"Updated {line} to {ln}")
                updated_lines.append(ln)
            else:
                updated_lines.append(line)

        with open(outputfile, 'w') as f:
            print(f"Writing update to {outputfile}")
            f.writelines(updated_lines)


    except FileNotFoundError:
        print(f"Error: File {args.input_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
        main()
    

