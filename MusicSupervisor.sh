#!/usr/bin/env bash
## Music supervisor running to supervise the use of the local Audio system.
# To be sechedueled by e.g crone @ clk NN:N5. https://www.raspberrypi.org/documentation/linux/usage/cron.md
# Stops music and restart Spotify client to disable remote connection.

echo "Audio supervisor is running"
OPENTIME="07:00"
CLOSINGTIME="00:00"
currenttime=$(date +%H:%M)
echo "OPENTIME: $OPENTIME"
echo "CLOSINGTIME: $CLOSINGTIME"
echo "System time: $currenttime"


# Closing time supervisor
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

# Remote connection supervisor. If no music is playing for ~15min, disconnect user by restarting service.

# if [t_last_played > currentitme + 15 && grep 'status' volumio status != 'playing']
#then
    #  echo "Closing Spotify connection"
      #systemctl restart volspotconnect2.service # Fixme not working
#fi



echo "Audio supervisor done."