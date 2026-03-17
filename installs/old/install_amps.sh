#!/bin/bash
VERSION=25.3.0.81

docker cp support-tools-repo-1.2.3.0-SNAPSHOT-amp.amp community25x-alfresco-1:/usr/local/tomcat/amps
Docker cp support-tools-share-1.2.3.0-SNAPSHOT-amp.amp community25x-share-1:/usr/local/tomcat/amps_share


docker exec -it --user root community25x-alfresco-1 bash -c "java -jar /usr/local/tomcat/alfresco-mmt/alfresco-mmt-$VERSION.jar install /usr/local/tomcat/amps /usr/local/tomcat/webapps/alfresco -directory -nobackup -force"
docker exec -it --user root community25x-share-1 bash -c "java -jar /usr/local/tomcat/alfresco-mmt/alfresco-mmt-$VERSION.jar install /usr/local/tomcat/amps_share /usr/local/tomcat/webapps/share -directory -nobackup -force"