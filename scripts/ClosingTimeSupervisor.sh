#!/usr/bin/env bash
echo "Closing time supervisor"
echo "If not open hours, stop music."
OPENTIME="07:00"
CLOSINGTIME="00:00"
currenttime=$(date +%H:%M)
echo "OPENTIME: $OPENTIME"
echo "CLOSINGTIME: $CLOSINGTIME"
echo "System time: $currenttime"

{
  while :; do
   currenttime=$(date +%H:%M)
   if [[ "$currenttime" > "$OPENTIME" ]] || [[ "$currenttime" < "$CLOSINGTIME" ]]; then
     echo "It is open"
   else
     echo "It is closed"
      echo "Stopping music"
      #volumio stop stop
      echo "Closing Spotify connection"
      #systemctl restart volspotconnect2.service # Fixme not working
   fi
   test "$?" -gt 128 && break
   sleep 60 # closingtime-currenttime
  done &
}
