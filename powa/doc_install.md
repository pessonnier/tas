# Présentation
Le but de ce document est de guider l'installation de l'outil de supervision PoWA sur une distribution CentOS 7. Il est basé sur la [documentation](https://powa.readthedocs.io/en/latest/) en ligne, mais tente d'apporter des clarifications.
Les prochaines versions de ce documents se trouveront à l'adresse suivante : https://powa.s3.eu-west-3.amazonaws.com/doc_install.zip

# Vue d'ensemble de l'installation
[PoWA](https://powa.readthedocs.io/en/latest/index.html) est composé d'une extension postgreSQL nommée [PoWA-archivist](https://github.com/powa-team/powa-archivist), d'une application web nommée [PoWA-web](https://github.com/powa-team/powa-web) et d'un processus nommé [PoWA-collector](https://github.com/powa-team/powa-collector). PoWA-archivist historise les métriques provenant d'une base PostgreSQL locale ou distante  permettant le transfert desmétriques depuis la base supervisée vers le superviseur. PoWA-web permet d'explorer ses métriques. L'installation se déroulera en plusieurs étapes.
- Installation d'un PostgreSQL (base superviseur) qui collectera les métriques d'une ou plusieurs autres bases PostgreSQL (bases métier)
- Compilation et installation des extensions dans les différentes base
- Configuration de la base superviseur
- Installation de l'application web et de ces dépendances
- Configuration de la base supervisée
- Installation de la collecte (PoWA-collector) entre superviseur et supervisé

Plusieurs architectures de déploiement sont possibles. La plus simple consiste à tout installer sur le même serveur :
```mermaid
graph LR
	subgraph serveur métier
		subgraph BdD PostgreSQL
		powa(PoWA archivist) --> appli(BdD Appli)
		end
	web[PoWA Web] --> powa
	end
```
L'application Web peut être mutualisée entre plusieurs serveurs PostgreSQL.
```mermaid
graph LR
	subgraph serveur métier 1
		subgraph BdD PostgreSQL
		powa1(PoWA archivist) --> appli1(BdD Appli)
		end
	end
	
	subgraph serveur métier 2
		subgraph BdD PostgreSQL
		powa2(PoWA archivist) --> appli2(BdD Appli)
		end
	end
	subgraph supervision
		web[PoWA Web] --> powa1
		web[PoWA Web] --> powa2
	end
```
En fonction du nombre de serveurs et pour réduire le volume de données contenues sur les serveur métiers, il est possible de choisir de collecter tous les métriques dans une seule base de données dédiée à la supervision.

```mermaid
graph TB
	subgraph serveur métier 1
		collector1[PoWA collector] --- powa1
		subgraph BdD PostgreSQL
			powa1(PoWA archivist) --> appli1(BdD Appli)
		end
	end
	
	subgraph serveur métier 2
		collector2[PoWA collector] --- powa2
		subgraph BdD PostgreSQL
			powa2(PoWA archivist) --> appli2(BdD Appli)
		end
	end
	subgraph supervision
		subgraph BdD PostgreSQL
			powa(PoWA archivist)
		end
		web[PoWA Web] --> powa
		powa --- collector1
		powa --- collector2
	end
```
Dans les schémas ci-dessus, les bloc PoWA archivist représentent plusieurs extentions PostgreSQL décrites plus loin. Le reste du document décrira une installation avec un serveur de supervision dédié connecté  à une BdD métier distante :

```mermaid
graph LR
	subgraph app1.serveur.metier
		collector1[PoWA collector] --> powa1
		subgraph BdD PostgreSQL
			subgraph base powa
				powa1(PoWA archivist)
				extmetier(autres extensions)
			end
			subgraph base métier
				appli1(BdD Appli)
			end
			powa1 --> appli1
		end
	end
	subgraph serveur.supervision
		subgraph BdD PostgreSQL
			subgraph base powa
				powa(PoWA archivist)
				ext(autres extensions)
			end
		end
		web[PoWA Web] --> powa
		powa --- collector1
	end
```
Dans la suite du document ce schéma sera réutilisé pour indiquer en vert quel composant est traité par le paragraphe courrant.
# Installation du PostgreSQL superviseur
Il s'agit d'installer une base de données PostgreSQL d'une version >=9.6 avec ses dépendances pour pouvoir par la suite compiler des extensions.

```mermaid
graph LR
	subgraph app1.serveur.metier
		collector1[PoWA collector] --> powa1
		subgraph BdD PostgreSQL
			subgraph base powa
				powa1(PoWA archivist)
				extmetier(autres extensions)
			end
			subgraph base métier
				appli1(BdD Appli)
			end
			powa1 --> appli1
		end
	end
	subgraph serveur.supervision
		subgraph BdD PostgreSQL
			subgraph base powa
				powa(PoWA archivist)
				ext(autres extensions)
				style powa fill:lightgreen,stroke:green,stroke-width:4px
				style ext fill:lightgreen,stroke:green,stroke-width:4px
			end
		end
		web[PoWA Web] --> powa
		powa --- collector1
	end
```
Dans cette documentation la version 9.6 est utilisée, mais j'ai fait mes tests avec la 10 et vous pouvez choisir d'installer la 11 ou la 12.
La procédure ci-dessous est données à titre indicative : je ne suis pas capable d'anticiper les spécificités de votre environnement. Cependant je suis intéressé de connaître les détails de votre installation.
## Avec dépôt
Si vous avez accès à un dépôt PostgreSQL, alors vous pouvez utiliser les commandes suivantes :
```bash
yum install postgresql96 postgresql96-server postgresql96-contrib postgresql96-devel
yum groupinstall "Development Tools"
```

## Sans dépot
Si le serveur n'a pas accès a un dépôt avec la version voulue, une archive a été préparée avec toutes les dépendances.
```bash
wget https://powa.s3.eu-west-3.amazonaws.com/rpm_postgresql.tar.gz
tar xzvf rpm_postgresql.tar.gz
yum localinstall rpm_postgresql/* 
```
Dans la pratique vous pourriez préférer installer les packages PostgreSQL depuis cette archive `yum localinstall rpm_postgresql/postgresql* ...` et les outils de développements depuis votre dépôt `yum groupinstall "Development Tools"`.
Si vous souhaitez installer une version différente, je peux vous préparer une archive assez rapidement.

## Initialisation de la base
En root
```bash
/usr/pgsql-9.6/bin/postgresql96-setup initdb
systemctl start postgresql-9.6
```
Les fichiers dans `/usr/pgsql-9.6` auront `root` comme propriétaire et les données dans `/var/lib/pgsql/9.6/data/` comme les processus auront `postgres` comme propriétaire ce qui me semble standard.

## Compilation et installation des extensions
Ce paragraphe va décrire l'installation des extensions suivantes :
- powa-archivist
- pg_stat_statements
- btree_gist
- hypopg
- pg_qualstats
- pg_stat_kcache
- pg_wait_sampling

`pg_stat_statements` et `btree_gist` sont inclus dans le package postgresql-contrib, les autres doivent être téléchargés. Le coeur de PoWA est PoWA-archivist mais il contient actuellement une petite erreur qui le rend innutilisable en version 4.0.0 la dernière version disponible sur github. Pour dépaner le développeur m'a fait une version 4.0.1 qui fonctionne parfaitement. Vous pouvez télécharger une archive prête à l'emploi :
```bash
wget https://powa.s3.eu-west-3.amazonaws.com/powa-archivist_401.tar.gz
tar xzvf powa-archivist_401.tar.gz
cd powa-archivist
```
ou bien repartir des sources
```bash
git clone https://github.com/powa-team/powa-archivist.git
cd powa-archivist
```
on se positionne précisément sur le commit qui corrige le bug :
```bash
git checkout 37a09c6
```
Que vous utilisiez l'archive préparée ou git il faut compiler et installer en tant que `root`, mais la procédure utilise `pg_config`. Cet exécutable peut être accessible ou non par défaut en fonction de la distribution linux. Sur une Ubuntu je n'ai rien eu de particulier à faire par contre sur une CentOS 7 j'ai modifié le `PATH`. Si besoin, mettre à jour son `PATH` :
```bash
export PATH=$PATH:/usr/pgsql-9.6/bin/
```
Puis la compilation et l'installation se font classiquement.
```bash
cd powa-archivist
make install
cd ..
```
Ce qui devrait produire la sortie suivante :
```
# make install
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o powa.o powa.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -L/usr/pgsql-9.6/lib -Wl,--as-needed  -L/usr/lib64 -Wl,--as-needed -Wl,-rpath,'/usr/pgsql-9.6/lib',--enable-new-dtags  -shared -o powa.so powa.o
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/lib'
	/usr/bin/install -c -m 644 .//powa.control '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//powa--3.2.0.sql .//powa--3.1.2--3.2.0.sql .//powa--3.1.1--3.1.2.sql .//powa--3.1.0--3.1.1.sql .//powa--4.0.1.sql  '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 755  powa.so '/usr/pgsql-9.6/lib/'
```
Pour les autres extensions on peu utiliser les releases disponibles
```bash
wget https://github.com/powa-team/pg_stat_kcache/archive/REL2_1_1.tar.gz -O pg_stat_kcache_REL2_1_1.tar.gz
wget https://github.com/powa-team/pg_qualstats/archive/2.0.1.tar.gz -O pg_qualstats_2.0.1.tar.gz
wget https://github.com/HypoPG/hypopg/archive/1.1.3.tar.gz -O hypopg_1.1.3.tar.gz
wget https://github.com/postgrespro/pg_wait_sampling/archive/v1.1.1.tar.gz -O pg_wait_sampling_v1.1.1.tar.gz
wget https://github.com/rjuju/pg_track_settings/archive/2.0.0.tar.gz -O pg_track_settings-2.0.0.tar.gz

tar xzvf hypopg_1.1.3.tar.gz
tar xzvf pg_qualstats_2.0.1.tar.gz
tar xzvf pg_stat_kcache_REL2_1_1.tar.gz
tar xzvf pg_wait_sampling_v1.1.1.tar.gz
tar zxvf pg_track_settings-2.0.0.tar.gz
```
Puis on compile
```bash
export PATH=$PATH:/usr/pgsql-9.6/bin/
cd hypopg-1.1.3/
make install
cd ../pg_qualstats-2.0.1/
make install
cd ../pg_stat_kcache-REL2_1_1/
make install
cd ../pg_wait_sampling-1.1.1/
make USE_PGXS=1 install
cd ../pg_track_settings-2.0.0
make install
```

Cela devrait produire la sortie suivante :
```
# cd hypopg-1.1.3/
# make install
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o hypopg.o hypopg.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o hypopg_index.o hypopg_index.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o import/hypopg_import.o import/hypopg_import.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o import/hypopg_import_index.o import/hypopg_import_index.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -shared -o hypopg.so hypopg.o hypopg_index.o import/hypopg_import.o import/hypopg_import_index.o -L/usr/pgsql-9.6/lib  -Wl,--as-needed  -L/usr/lib64 -Wl,--as-needed -Wl,-rpath,'/usr/pgsql-9.6/lib',--enable-new-dtags  
	/usr/bin/mkdir -p '/usr/pgsql-9.6/lib'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/install -c -m 755  hypopg.so '/usr/pgsql-9.6/lib/hypopg.so'
	/usr/bin/install -c -m 644 .//hypopg.control '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//hypopg--1.1.3.sql  '/usr/pgsql-9.6/share/extension/'
# cd ../pg_qualstats-2.0.1/
# make install
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o pg_qualstats.o pg_qualstats.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -L/usr/pgsql-9.6/lib -Wl,--as-needed  -L/usr/lib64 -Wl,--as-needed -Wl,-rpath,'/usr/pgsql-9.6/lib',--enable-new-dtags  -shared -o pg_qualstats.so pg_qualstats.o
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/lib'
	/usr/bin/install -c -m 644 .//pg_qualstats.control '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//pg_qualstats--2.0.1.sql  '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 755  pg_qualstats.so '/usr/pgsql-9.6/lib/'
# cd ../pg_stat_kcache-REL2_1_1/
# make install
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o pg_stat_kcache.o pg_stat_kcache.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -shared -o pg_stat_kcache.so pg_stat_kcache.o -L/usr/pgsql-9.6/lib  -Wl,--as-needed  -L/usr/lib64 -Wl,--as-needed -Wl,-rpath,'/usr/pgsql-9.6/lib',--enable-new-dtags  
	/usr/bin/mkdir -p '/usr/pgsql-9.6/lib'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/install -c -m 755  pg_stat_kcache.so '/usr/pgsql-9.6/lib/pg_stat_kcache.so'
	/usr/bin/install -c -m 644 .//pg_stat_kcache.control '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//pg_stat_kcache--2.1.1.sql .//pg_stat_kcache--2.1.0.sql .//pg_stat_kcache--2.1.0--2.1.1.sql  '/usr/pgsql-9.6/share/extension/'
# cd ../pg_wait_sampling-1.1.1/
# make USE_PGXS=1 install
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o pg_wait_sampling.o pg_wait_sampling.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o collector.o collector.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -I. -I./ -I/usr/pgsql-9.6/include/server -I/usr/pgsql-9.6/include/internal -D_GNU_SOURCE -I/usr/include/libxml2  -I/usr/include  -c -o compat.o compat.c
	gcc -Wall -Wmissing-prototypes -Wpointer-arith -Wdeclaration-after-statement -Wendif-labels -Wmissing-format-attribute -Wformat-security -fno-strict-aliasing -fwrapv -fexcess-precision=standard -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -m64 -mtune=generic -fPIC -shared -o pg_wait_sampling.so pg_wait_sampling.o collector.o compat.o -L/usr/pgsql-9.6/lib  -Wl,--as-needed  -L/usr/lib64 -Wl,--as-needed -Wl,-rpath,'/usr/pgsql-9.6/lib',--enable-new-dtags  
	cat setup.sql > pg_wait_sampling--1.1.sql
	/usr/bin/mkdir -p '/usr/pgsql-9.6/lib'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/install -c -m 755  pg_wait_sampling.so '/usr/pgsql-9.6/lib/pg_wait_sampling.so'
	/usr/bin/install -c -m 644 .//pg_wait_sampling.control '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//pg_wait_sampling--1.0--1.1.sql pg_wait_sampling--1.1.sql '/usr/pgsql-9.6/share/extension/'
# cd ../pg_track_settings-2.0.0
# make install
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/share/extension'
	/usr/bin/mkdir -p '/usr/pgsql-9.6/doc/extension'
	/usr/bin/install -c -m 644 .//pg_track_settings.control '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//pg_track_settings--1.0.1--1.1.0.sql .//pg_track_settings--1.0.1.sql .//pg_track_settings--1.0.0.sql .//pg_track_settings--1.1.0.sql .//pg_track_settings--1.0.0--1.0.1.sql .//pg_track_settings--2.0.0.sql  '/usr/pgsql-9.6/share/extension/'
	/usr/bin/install -c -m 644 .//README.md '/usr/pgsql-9.6/doc/extension/'
	
```

## Configuration de la base du superviseur
Sur le serveur de supervision il va falloir créer une base pour PoWA puis configurer les connexions et les extensions. Ces opérations se font en modifiant les fichiers `pg_hba.conf`, `postgresql.conf` et en se connectant à la base en tant que postgres.
### Configuration des connexions
La base superviseur devra accepter les connexions provenant de PoWA-Web et de PoWA-collector. Dans cet exemple la configuration est préparée pour accepter PoWA-Web installé sur le serveur de supervision et PoWA-collector installé sur le serveur métier à superviser.
Pour PoWA-Web, il faut au minimum vérifier que la première ligne de type `host` du fichier d'authenfication par hôte `/var/lib/pgsql/9.6/data/pg_hba.conf` soit
```
host    powa            powa            127.0.0.1/32            md5
```
Optionnellement il est possible de prévoir que l'IHM Web (powa-web) soit sur un serveur différent de la base de données. Dans ce cas il faudrait autoriser les connexions distantes en ajoutant une ligne du type :
```
host    powa            powa            powaweb.supervision/32      md5
```
Pour PoWA-collector, il faut autoriser une connexion distante depuis le serveur métier supervisé.
```
host    powa            powa            app1.serveur.metier/32      md5
```

De plus il faut modifier l'option `listen_addresses` dans `/var/lib/pgsql/9.6/data/postgres.conf`. Par exemple :
```
listen_addresses = 'localhost, app1.serveur.metier' # '*' pour tous, ajouter powaweb.suprevision si PoWA-Web est sur un autre serveur
```
Puis ouvrir le port postgres du firewall
```
su
firewall-cmd --zone=public --permanent --add-port=5432/tcp
systemctl restart firewalld
```
A ce stade il est possible de tester une connexion distante depuis le serveur métier vers la base de données du serveur de supervision dont l'adresse serait `Y.Y.Y.Y`. Dans cet exemple un client en version 10 se connecte à une base en version 9.6.
```
psql -h Y.Y.Y.Y powa powa
Password for user powa: 
psql (10.12 (Ubuntu 10.12-0ubuntu0.18.04.1), server 9.6.17)
Type "help" for help.

powa=#
```

### Chargement des extensions
Certaines des extensions ont des librairies qui doivent être chargées au démarrage du serveur PostgreSQL. Cette déclaration se fait en tant que `postgres` dans `/var/lib/pgsql/9.6/data/postgresql.conf` avec le paramètre `shared_preload_libraries`. Il faut changer la ligne suivante :
```
#shared_preload_libraries = ''		# (change requires restart)
```
Par
```
shared_preload_libraries='pg_stat_statements,powa,pg_stat_kcache,pg_qualstats,pg_wait_sampling'
```
Puis redémarer le serveur PostgreSQL
```bash
su
systemctl restart postgresql-9.6
```
<!--
ou peut-être
systemctl restart postgresql
/etc/init.d/postgresql-9.6 restart
  -->
Après redémarrage il est possible de vérifier la configuration depuis la console `psql`
```
postgres=# show shared_preload_libraries ;
                       shared_preload_libraries                       
----------------------------------------------------------------------
 pg_stat_statements,powa,pg_stat_kcache,pg_qualstats,pg_wait_sampling
(1 row)
```

### Activation des extensions
L'activation des extensions se fait au niveau d'une base dédiée à PoWA en utilisant la commande plsq `CREATE EXTENSION`.
```bash
su postgres
psql
```
Création de la base dédiée
```
postgres=# create database powa;
CREATE DATABASE

postgres=# \c powa
You are now connected to database "powa" as user "postgres".

powa=# CREATE ROLE powa SUPERUSER LOGIN PASSWORD 'powa';
CREATE ROLE
```
Pour vérification on peut regarder la liste des extensions par défault :
```
powa=# \dx
                 List of installed extensions
  Name   | Version |   Schema   |         Description          
---------+---------+------------+------------------------------
 plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
(1 row)
```
Puis on ajoute celles utilisées par PoWA :
```sql
CREATE EXTENSION btree_gist;
CREATE EXTENSION hypopg;
CREATE EXTENSION pg_stat_statements;
CREATE EXTENSION pg_stat_kcache;
CREATE EXTENSION pg_qualstats;
CREATE EXTENSION pg_wait_sampling;
CREATE EXTENSION powa;
```
<!-- CREATE EXTENSION pg_track_settings; -->
<!--
certaines extentions doivent être signalées à PoWA Web pour restituer les métriques.
```sql
SELECT powa_kcache_register();
SELECT powa_qualstats_register();
--SELECT powa_track_settings_register();
SELECT powa_wait_sampling_register();
```
pour le moment l'extension `pg_track_settings` ne peut pas être activée à cause d'un bug en cours de résolution.
-->
```
powa=# \dx
                                     List of installed extensions
        Name        | Version |   Schema   |                        Description                        
--------------------+---------+------------+-----------------------------------------------------------
 btree_gist         | 1.2     | public     | support for indexing common datatypes in GiST
 hypopg             | 1.1.3   | public     | Hypothetical indexes for PostgreSQL
 pg_qualstats       | 2.0.1   | public     | An extension collecting statistics about quals
 pg_stat_kcache     | 2.1.1   | public     | Kernel statistics gathering
 pg_stat_statements | 1.4     | public     | track execution statistics of all SQL statements executed
 pg_wait_sampling   | 1.1     | public     | sampling based statistics of wait events
 plpgsql            | 1.0     | pg_catalog | PL/pgSQL procedural language
 powa               | 4.0.1   | public     | PostgreSQL Workload Analyser-core
(8 lignes)
```
En cas d'erreur avec les commandes `CREATE EXTENSION` vérifier si le `make install` correspondant c'est bien passé. Si besoin, les extensions peuvent être retirées avec la commande `DROP EXTENSION` puis recrée.
## Configuration pour PoWA-collector
PoWA-collector sera [installé](#installation-de-powa-collector) sur le serveur métier à superviser et il se connectera à la base de supervision pour obtenir sa configuration. cette configuration consiste à indiquer quels sont les serveurs à superviser. 
La fonction `powa_register_server` sert à référencer chacun des serveurs à superviser. Dans l'exemple ci-dessous le serveur `app1.serveur.metier` sera ajouté et il apparaitra sous le nom de `serveur métier` dans l'interface Web.
```sql
SELECT powa_register_server(hostname => 'app1.serveur.metier',
    alias => 'serveur métier',
    password => 'powa',
    extensions => '{pg_stat_kcache,pg_qualstats,pg_wait_sampling}');
```
Cette commande est à lancer sur le serveur de supervision dans la base `powa` pour chaque serveurs à superviser. Plus d'informations dans la [documention](https://powa.readthedocs.io/en/latest/components/powa-archivist/configuration.html#powa-register-server). La configuration peut être vérifiée avec la commande suivante :
```sql
select * from powa_servers;
 id |   hostname   |   alias    | port | username | password | dbname | frequency | powa_coalesce | retention | allow_ui_connection 
----+--------------+------------+------+----------+----------+--------+-----------+---------------+-----------+---------------------
  0 |              | <local>    |    0 |          |          |        |        -1 |           100 | 00:00:00  | t
  1 | vmcentos     | vm centos  | 5432 | powa     | powa     | powa   |       300 |           100 | 1 day     | t
(2 rows)
```
En cas d'évolution, la configuration peut être modifiée avec la commande [powa_configure_server](https://powa.readthedocs.io/en/latest/components/powa-archivist/configuration.html#powa-configure-server)

# Installation de l'interface Web
PoWA-Web est l'interface web de PoWA. C'est un serveur Web écrit en Python. Son installation nécessite des packages RPM liés au Python puis l'application PoWA-Web et les package Python dépendants.
```mermaid
graph LR
	subgraph app1.serveur.metier
		collector1[PoWA collector] --> powa1
		subgraph BdD PostgreSQL
			subgraph base powa
				powa1(PoWA archivist)
				extmetier(autres extensions)
			end
			subgraph base métier
				appli1(BdD Appli)
			end
			powa1 --> appli1
		end
	end
	subgraph serveur.supervision
		subgraph BdD PostgreSQL
			subgraph base powa
				powa(PoWA archivist)
				ext(autres extensions)
			end
		end
		web[PoWA Web] --> powa
		powa --- collector1
		style web fill:lightgreen,stroke:green,stroke-width:4px;
		end
	end
```
## Installation du Python
Installation de Python 3 et de son gestionnaire de package.

### Avec dépot
```bash
yum install python3-pip python3-devel
```

### Sans dépot
Une archive a été préparée avec toutes les dépendances :
```bash
wget https://powa.s3.eu-west-3.amazonaws.com/rpm_python.tar.gz
tar xzvf rpm_python.tar.gz
yum localinstall rpm_python/* 
```
### Test
```bash
python3 --version
Python 3.6.8
```
## Installation de PoWA-Web
PoWA-Web est une application Web embarquant son propre serveur. Elle est écrite en python avec le frameworke Tornado. Les dépendances de ce package sont :
- psycopg2
- SQLAlchemy
- tornado
Ils sont tous réunis dans une archive à télécharger :
```bash
wget https://powa.s3.eu-west-3.amazonaws.com/powa.tar.gz
tar xzvf dependances_powa_web.tar.gz
```
La décompression crée un répertoire  contenant PoWA-Web et ces dépendances. Ils peuvent être installés avec la commande `pip` suivante :
```bash
pip3 install --no-index --find-links=powa_web/ powa-web
```
## Configuration de powa-web
La configuration de powa-web consiste à indiquer où se trouve la base de données de supervision et comment s'y connecter. Pour cela il faut renseigner le fichier de configuration `/etc/powa-web.conf`
```bash
cat <<FIN > /etc/powa-web.conf
servers={
 'main': {
  'host': 'localhost',
  'port': '5432',
  'database': 'powa',
  'query': {'client_encoding': 'utf8'}
 }
}
cookie_secret="cookie"
FIN
```
Le paramètre `cookie_secret` peut être changé pour une valeur quelconque. Le port d'écoute peut être défini avec l'option `port=80` par exemple. Plus d'options et d'explications se trouvent dans la [documentation](https://powa.readthedocs.io/en/latest/components/powa-web/index.html#configuration)
Pour permettre les connexions depuis un poste client il faut déclarer le port utilisé au firewall :
```
firewall-cmd --zone=public --permanent --add-port=8888/tcp
systemctl restart firewalld
```
## Lancement
PoWA-Web se lance avec la commande `powa-web` depuis un utilisateur quelconque.
```
# powa-web 
[I 200501 21:49:02 powa-web:13] Starting powa-web on http://0.0.0.0:8888/
```
En fonction de l'utilisateur choisi, il peut être plus simple de positionner le fichier de configuration dans `~/.powa-web.conf`.
Le choix de la méthode pour automatiser ce lancement est laissé à l'exploitant.

# Configuration du serveur supervisé
La base de données du serveur supervisé est en partie configurée comme le serveur de supervision : il faudra y créer une base `powa` et y installer les mêmes extensions. Cette procédure est décrite [précédement](#compilation-et-installation-des-extensions).
```mermaid
graph LR
	subgraph app1.serveur.metier
		collector1[PoWA collector] --> powa1
		subgraph BdD PostgreSQL
			subgraph base powa
				powa1(PoWA archivist)
				extmetier(autres extensions)
			end
			subgraph base métier
				appli1(BdD Appli)
			end
			powa1 --> appli1
		end
	end
	subgraph serveur.supervision
		subgraph BdD PostgreSQL
			subgraph base powa
				powa(PoWA archivist)
				ext(autres extensions)
			end
		end
		web[PoWA Web] --> powa
		powa --- collector1
	end
	style powa1 fill:lightgreen,stroke:green,stroke-width:4px
	style extmetier fill:lightgreen,stroke:green,stroke-width:4px

```
## Modification de la configuration de la base à superviser
La base supervisée devra accepter les connexions provenant de PoWA-collector qui se trouvera sur le même serveur. mais PoWA-collector ne fait pas de connexion par socket mais par host. Le fichier d'authentification par hôte `/var/lib/pgsql/9.6/data/pg_hba.conf` doit donc contenir la ligne suivante en ramplaçant `app1.serveur.metier` par le nom du serveur métier.
```
host    powa            powa            app1.serveur.metier/32      md5
```
De même, l'option `listen_addresses` dans `/var/lib/pgsql/9.6/data/postgres.conf` devra contenir le nom de son serveur. 
Si besoin, il faut ajouter le port postgres aux entrées du firewall :
```
firewall-cmd --zone=public --permanent --add-port=5432/tcp
systemctl restart firewalld
```
## Installation des extensions
Les mêmes extension PostgreSQL doivent être installées sur le serveur de supervision et sur les serveurs supervisés. Récupérez les dossiers des extensions précédement compilées sur le serveur de supervision et les déposer sur le serveur à superviser pour obtenir la liste des dossiers suivants :
- hypopg-1.1.3/
- pg_qualstats-2.0.1/
- pg_stat_kcache-REL2_1_1/
- pg_wait_sampling-1.1.1/
- pg_track_settings-2.0.0/
- powa-archivist/

Les opérations à réaliser sont similaires à celle du serveur de supervision :
- Exécutez un `make install` dans chaque dossiers pour [compiler et installer les extensions](#compilation-et-installation-des-extensions)
- [Chargez les extensions](#chargement-des-extensions) dans `/var/lib/pgsql/9.6/data/postgresql.conf`
- Créez la base powa, son utilisateur et [activer les extensions](#activation-des-extensions)

## Installation de PoWA-collector
PoWA-collector est un processus dont le rôle est de transférer les métriques historisés dans la base powa d'un serveur supervisé, vers la base powa du serveur de supervision.

```mermaid
graph LR
	subgraph app1.serveur.metier
		collector1[PoWA collector] --> powa1
		style collector1 fill:lightgreen,stroke:green,stroke-width:4px
		subgraph BdD PostgreSQL
			subgraph base powa
				powa1(PoWA archivist)
				extmetier(autres extensions)
			end
			subgraph base métier
				appli1(BdD Appli)
			end
			powa1 --> appli1
		end
	end
	subgraph serveur.supervision
		subgraph BdD PostgreSQL
			subgraph base powa
				powa(PoWA archivist)
				ext(autres extensions)
			end
		end
		web[PoWA Web] --> powa
		powa --- collector1
	end
```
Pour commencer, récupérez de l'archive de packages python utilisée pour [PoWA-Web](#installation-de-powa-web) car elle contient aussi PoWA-collector.
```
wget https://powa.s3.eu-west-3.amazonaws.com/powa.tar.gz
```
Transférez l'archive sur le serveur à superviser puis installez le package python `powa-collector`
```
tar xzvf powa.tar.gz
export PATH=$PATH:/usr/pgsql-9.6/bin/
pip3 install --no-index --find-links=powa/ powa-collector
```

## Configuration de PoWA-collector
La configuration de PoWA-collector revient à indiquer où se trouve le serveur de supervision.
```
cat <<FIN >> /etc/powa-collector.conf 
{
    "repository": {
        "dsn": "postgresql://powa:powa@supervision:5432/powa"
    },
    "debug": false
}
FIN
```
PoWA-collector utilise l'URI de connexion définie pour obtenir la configuration [précédement renseignée](#configuration-pour-powa-collector) permettant de se connecter à la base supervisée.

## lancement de PoWA-collector
PoWA-collector se lance avec la commande `powa-collector.py` et doit produire une sortie du type :
```
2020-05-01 01:21:26,060 - INFO  : Starting powa-collector... 
2020-05-01 01:21:26,076 vmcentos:5432 INFO  : Starting worker 
2020-05-01 01:21:26,077 192.168.1.35:5432 INFO  : Starting worker 
2020-05-01 01:21:26,078 - INFO  : List of workers: 
2020-05-01 01:21:26,078 - INFO  : vmcentos:5432: {'host': 'vmcentos', 'port': 5432, 'user': 'powa', 'password': 'powa', 'dbname': 'powa'} (no connection to remote server) 
```
Après quelques minutes, l'utilisation du bouton `Reload collector` depuis PoWA-Web devrait produire l'affichage de la `List of workers` avec la mention `(running)` à la place de `(no connection to remote server)`
Pour vérifier si PoWA-collector est bien connecté au serveur de supervision et au serveur supervisé on peut regarder les processus et le réseau. Dans l'exemple ci-dessous `powa-collector.py` est le processus `2360` et il établi une connexion vers `coquille` le serveur de supervision et vers `vmcentos` le serveur supervisé.
```bash
ps all | grep powa-collector.py
	0    26  2360  2359  20   0 377104 15480 poll_s Sl+  pts/2      0:01 /usr/bin/python3 /usr/local/bin/powa-collector.py
netstat -ep | grep 2360
	tcp        0      0 localhost.localdo:60310 coquille:postgres       ESTABLISHED postgres   26124      2360/python3        
	tcp        0      0 vmcentos:53466          vmcentos:postgres       ESTABLISHED postgres   26134      2360/python3        
```

# Tests
A ce stade on doit avoir une interface utilisateur Web capable d'afficher l'activité d'une base PostgreSQL distante. L'écran de connexion est accessible à une adresse du type http://serveur.supervision:8888. La connexion se fait avec l'utilisateur powa et le mot de passe défini à la [création du rôle](#activation-des-extensions) powa. Il faut souvent attendre 10mn et bien régler la plage horaire (en haut à droite) avant de voir les premiers métriques apparaître. Si des erreurs se produisent, des messages apparaîtront en haut de la page en rouge ou dans la console qui aura lancé la commande `powa-web`. Dans tous les cas appelez-moi.

<!--
truc utiles pour ubuntu
xxx bin
vi /etc/postgresql/10/main/pg_hba.conf
vi /etc/postgresql/10/main/postgres.conf
sudo /etc/init.d/postgresql restart
tail -n 100 /var/log/postgresql/postgresql-10-main.log 
xxx firewall

truc utiles centos
export PATH=$PATH:/usr/pgsql-9.6/bin/
vi /var/lib/pgsql/9.6/data/pg_hba.conf
vi /var/lib/pgsql/9.6/data/postgres.conf
systemctl restart postgresql-9.6
xxx log
firewall-cmd --zone=public --permanent --add-port=5432/tcp
systemctl restart firewalld
-->
<!--stackedit_data:
eyJoaXN0b3J5IjpbLTEyMDg1MjMwMDEsMTUwOTkyMzA0MywtMT
A2MDgzNTc5Ml19
-->