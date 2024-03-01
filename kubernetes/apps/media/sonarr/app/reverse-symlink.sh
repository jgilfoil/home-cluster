#!/bin/bash

PERMPATH="$sonarr_episodefile_path"
LINKPATH="$sonarr_episodefile_sourcepath"

if [[ -f "$LINKPATH" ]]; then
    sleep 1
else
    exit 0
    # changed from Radarr as Sonarr fails on test unless exit normally
fi

ORIGFILESIZE=$(stat -c%s "$LINKPATH")
PERMFILESIZE=$(stat -c%s "$PERMPATH")

sleep 30

while [[ $PERMFILESIZE != $ORIGFILESIZE ]]; do
    sleep 60
    PERMFILESIZE=$(stat -c%s "$PERMPATH")
done

if [[ $PERMFILESIZE == $ORIGFILESIZE ]]; then
    # Save current time stamps to prevent radarr from identifying our simlink as new, and double-processing it
    LINKDIR=$(dirname "$LINKPATH")
    FOLDER_DATE=$(date -r "$LINKDIR" +@%s.%N)
    FILE_DATE=$(date -r "$LINKPATH" +@%s.%N)

    rm "$LINKPATH"
    ln -s "$PERMPATH" "$LINKPATH"

    touch --no-create --no-dereference  --date "$FILE_DATE" "$LINKPATH"
    touch --no-create --no-dereference  --date "$FILE_DATE" "$PERMPATH"
    touch --no-create --no-dereference  --date "$FOLDER_DATE" "$LINKDIR"
fi