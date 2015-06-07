# lol-master-ease
Analyzes League of Legends game stats for a summoner and gives granular rankings and advice on how to improve

To Setup:

 1) [2m] Download & Virtual Box: https://www.virtualbox.org/wiki/Downloads
 
 2) [2m] Download & Install Vangrant: https://www.vagrantup.com/downloads.html
 
 3) [1m] Goto the folder you want to hold your local version in with cd [filepath]
 
 4) [5m] Run: vagrant init ubuntu/trusty64
 
 5) [2m] Run: vagrant up
 
 6) [1m] Dpwnload and install putty: http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html
 
 7) Run putty and connect to 127.0.0.1 as hostname and 2222 as port
 
 8) Use vagrant as login and password.
 
 9) Download all the things!
 	
	sudo apt-get update
 	
	sudo apt-get install git
	
	sudo apt-get install python-virtualenv
	
	sudo pip install Flask
	
	sudo pip install tornado
	
	sudo pip install Flask-RESTful
	
	sudo apt-get install python-mysqldb
	
	sudo apt-get install mysql-server
		
		*Note you will be asked to insert a password at this step.  Remember it! Use the same for mariaDB
	
	apt-get install mariadb-server
	
	sudo su
	
	echo never > /sys/kernel/mm/transparent_hugepage/enabled
	
	echo never > /sys/kernel/mm/transparent_hugepage/defrag
	
	echo "plugin-load=ha_tokudb" > /etc/mysql/conf.d/tokudb.cnf
	
	exit
	
	
	
10) Goto your vagrant folder (Run: cd /vagrant/)

11) Pull the git down using: git clone [urltothetright]

12) Back to your machine!

13) Download your prefered IDE (such as sublime) and point it at lol-master-ease in the folder you saved your vagrant box in.

14) Create a new file settings_local.py!  Do not make a mistake!

15) Copy the setup block over from settings into settings_local.py.  Get your API key from developer.riotgames.com. Use the password you set earlier for root here as well.

???
