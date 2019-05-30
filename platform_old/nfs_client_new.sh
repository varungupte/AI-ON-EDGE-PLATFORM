echo $1 | sudo -S apt-get update
echo $1 | sudo -S apt-get install -o StrictHostKeyChecking=no nfs-common


mkdir -p /home/$USER/nfs
echo $1 | sudo -S mount 10.42.0.199:/home/mypc/nfs /home/$USER/nfs
