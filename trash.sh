#!/usr/bin/bash
PW="eko,1994"
echo "Trashing local files"
python trash_to.py "${@:1}" ~/Pictures/DarktableLocal ~/trash files.txt
echo "Copy script and filelist"
sshpass -p $PW scp -P2200 \
    trash_to.py files.txt har0ke@192.168.20.2:/homes/har0ke/
echo "Trash remote files"
echo "$PW" | sshpass -p $PW ssh -t har0ke@192.168.20.2 -p2200 \
    sudo -S python \
    trash_to.py "${@:1}" \
    /volume1/homes/oke/lenovo-darktable/home/oke/Pictures/DarktableLocal \
    /volume1/homes/oke/trash \
    files.txt
