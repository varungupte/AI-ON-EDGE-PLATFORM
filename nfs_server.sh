echo "ubuntu@123" | sudo -S apt-get install nfs-kernel-server
wait
echo "1"
echo $?

echo "ubuntu@123" | sudo -S mkdir -p /home/$USER/nfs
echo "2"
echo $?

echo "ubuntu@123" | sudo -S chown nobody:nogroup /home/$USER/nfs
echo "3"
echo $?

echo "ubuntu@123" | sudo -S chmod 777 /home/$USER/nfs
echo "4"
echo $?

#echo "ubuntu@123" | sudo -S echo "/home/anurag/Desktop/sharedfolder3 10.42.0.163(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports
#echo "ubuntu@123" | sudo echo "anurag" >> /etc/exports
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.228:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.58:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.177:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.96:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.1:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.238:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.163:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.222:/home/$USER/nfs

echo "ubuntu@123" | sudo exportfs -o rw 192.168.43.229:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 192.168.43.90:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 192.168.43.15:/home/$USER/nfs
echo "ubuntu@123" | sudo exportfs -o rw 192.168.43.230:/home/$USER/nfs


# echo "ubuntu@123" | sudo exportfs -o rw 10.42.0.199:/home/$USER/nfs

echo "5"
echo $?

echo "ubuntu@123" | sudo -S exportfs -a
echo "6"
echo $?
# echo "ubuntu@123" | sudo -S systemctl restart nfs-kernel-server
#echo "7"
#echo $?
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.228 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.58 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.96 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.177 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.1 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.238 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.222 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.163 to any port nfs

echo "ubuntu@123" | sudo -S ufw allow from 192.168.43.229 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 192.168.43.90 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 192.168.43.15 to any port nfs
echo "ubuntu@123" | sudo -S ufw allow from 192.168.43.230 to any port nfs



# echo "ubuntu@123" | sudo -S ufw allow from 10.42.0.199 to any port nfs
echo "8"
echo $?