#!/bin/bash

# Loop through all files in current directory
echo "This installs all jars and amps "
echo " "

SHARE_DIR="./installs/share" #"${1:-.}"
CONTENT_DIR="./installs/content"
VERSION=26.1.0.61

echo "Recursively looping through files in: $SHARE_DIR"
echo "--------------------------------------------------"

# Loop through share files recursively
find "$SHARE_DIR" -type f | while read -r file; do
   

    if [[ $file == *".jar"* ]]; then
        echo "JAR File: $file"
        docker cp $file community26x-share-1:/usr/local/tomcat/webapps/share/WEB-INF/lib
        echo " "
    fi

    if [[ $file == *".amp"* ]]; then
        echo "AMP File: $file"
        docker cp $file community26x-share-1:/usr/local/tomcat/amps_share
        docker exec --user root community26x-share-1 bash -c "java -jar /usr/local/tomcat/alfresco-mmt/alfresco-mmt-$VERSION.jar install /usr/local/tomcat/amps_share /usr/local/tomcat/webapps/share -directory -nobackup -force"
        echo " "
    fi
    
done

echo "Recursively looping through files in: $CONTENT_DIR"
echo "--------------------------------------------------"
# Loop through content files recursively
find "$CONTENT_DIR" -type f | while read -r file; do
   

    if [[ $file == *".jar"* ]]; then
        echo "JAR File: $file"
        docker cp $file community26x-alfresco-1:/usr/local/tomcat/webapps/alfresco/WEB-INF/lib
        echo " "
    fi

    if [[ $file == *".amp"* ]]; then
        echo "AMP File: $file"
        docker cp $file community26x-alfresco-1:/usr/local/tomcat/amps
        docker exec --user root community26x-alfresco-1 bash -c "java -jar /usr/local/tomcat/alfresco-mmt/alfresco-mmt-$VERSION.jar install /usr/local/tomcat/amps /usr/local/tomcat/webapps/alfresco -directory -nobackup -force"
        echo " "
    fi
    
done

echo "Done!"