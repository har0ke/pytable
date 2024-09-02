#!/usr/bin/bash
shopt -s nocaseglob
shopt -s dotglob

trap "exit" INT

read -r -s -p "Password: " PWD
echo ""

host="192.168.20.2"
user="oke"
extra_args=("--info=progress2" "-h" "${@:1}")
do_backup() (
        set -e
        echo "Waiting for '$host' to be up ..."
        until ping -c1 "$host" >/dev/null 2>&1; do :; done
        echo "... done waiting"

        sshpass -p "$PWD" \
        rsync -av "${extra_args[@]}" --relative "$HOME/Pictures/DarktableLocal" "$user@$host":lenovo-darktable

        sshpass -p "$PWD" \
        rsync -av "${extra_args[@]}" --relative "$HOME/.config/darktable" "$user@$host":lenovo-darktable

    )

do_backup
