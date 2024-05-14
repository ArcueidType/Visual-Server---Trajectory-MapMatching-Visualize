# Barefoot for China Cities

## Map server

1. Install prerequisites.

    - Docker Engine (version 1.6 or higher, see [https://docs.docker.com/installation/ubuntulinux/](https://docs.docker.com/installation/ubuntulinux/))
    - [osmosis](https://wiki.openstreetmap.org/wiki/Osmosis/Installation)
    - java 

2. Download the map data and extract the city data

    ``` bash
    git clone https://github.com/hujilin1229/barefoot.git
    cd barefoot/map/osm/
    curl http://download.geofabrik.de/asia/china-latest.osm.pbf -o barefoot/map/osm/china.osm.pbf
    osmosis --read-pbf file=china-latest.osm.pbf --bounding-box left=126.506130 right=126.771862 bottom=45.657920 top=45.830905 --write-pbf file=harbin.osm.pbf
    ```

    If you want to change the city, remember to modify the input in [this line](https://github.com/boathit/barefoot/blob/master/map/osm/import.sh#L28) in import.sh.

3. Load Existing Docker image.

    ``` bash
    docker pull hujilin1229/barefoot_map
    ```

4. Create Docker container.

    ``` bash
    docker run -it -p 5432:5432 --name="harbin-map" -v ${PWD}/map/:/mnt/map hujilin1229/barefoot_map:latest
    ```

5. Import OSM extract (in the container).

    ``` bash
    root@acef54deeedb# bash /mnt/map/osm/import.sh
    ```

    To detach the interactive shell from a running container without stopping it, use the escape sequence Ctrl-p + Ctrl-q.

    If we want to attach it again, we can do

    ```bash
    docker attach <container id>
    ```

6. Make sure the container is running ("up").

    ``` bash
    docker ps -a
    ...
    ```

We can restart the created container (if it is stopped)
```bash
docker start --interactive harbin-map
```


## Matching server

1. Install prerequisites.

    - Maven (e.g. with `sudo apt-get install maven`)
    - Java JDK (Java version 7 or higher, e.g. with `sudo apt-get install openjdk-1.7-jdk`)

2. Package Barefoot JAR. (Includes dependencies and executable main class.)

    ``` bash
    mvn package -DskipTests
    ```

3. Start server with standard configuration for map server and map matching, and option for 'slimjson' output format.

    ``` bash
    java -jar target/barefoot-0.1.5-matcher-jar-with-dependencies.jar --slimjson config/server.properties config/harbin.properties
    ```

    _Note: Stop server with Ctrl-c._

    _Note: In case of 'parse errors', use the following Java options: `-Duser.language=en -Duser.country=US`_

4. Results infer (Hints from answers of issues from master repository).
    
    Hi Jan,
    ids are generated during import which is necessary because OSM roads must be split to get a routable road network. Hence, each road has a unique identifier but also knows the id of the corresponding OSM road with a 1-to-n relationship.

    EDIT: The result format of the map matching library returns internal identifier that encodes the heading of the matched object. Hence, divide a road id (e.g. in SlimJSON format) by 2 where the remainder specifies the heading of your object, which is 0 for forward and 1 for backward relative to the road's direction (source node and target node of the road specify the road's direction). Example: A road id of 2001 refers to road gid 1000 where the object was heading backwards from the roads target node to the source node. In contrast, a road id of 2000 refers to road gid 1000 where the object was heading from the road's source node to the target node. This coding is library versions up to 0.0.2 and will be patched in later versions to have a more intuitive result format.

    To get information about the road, you can query the DB (PostgreSQL/PostGIS) as follows (example):
    ``` bash
    sudo docker exec -it barefoot-oberbayern psql -h localhost -d oberbayern -U osmuser
    oberbayern=> select gid,osm_id from bfmap_ways where gid=1;
     gid | osm_id 
    -----+--------
       1 |     99
    (1 row)
    oberbayern=> select tags from ways where id=99;
                                                 tags                                             
    ----------------------------------------------------------------------------------------------
     "ref"=>"FFB 11", "highway"=>"tertiary", "junction"=>"roundabout", "zone:traffic"=>"DE:urban"
    (1 row)
    oberbayern=> \q
    ```
    Alternatively, you can also get road information in software with the provided API, see http://bmwcarit.github.io/barefoot/doc/index.html

    I hope this helps. Please do not hesitate to ask more questions!
    Cheers, Sebastian
## Reference

P. Newson and J. Krumm. Hidden Markov Map Matching Through Noise and Sparseness. In Proceedings of International Conference on Advances in Geographic Information Systems, 2009.
