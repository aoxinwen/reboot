
/oem/ecbtool -e 0x3 1

sleep 5
if [[ $? != 0 ]]; then
echo "fail"

else
echo "pass,begin reboot"
sleep 5
reboot
fi
