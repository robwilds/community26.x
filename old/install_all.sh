#!/bin/bash
set -euo pipefail

SHARE_DIR="./installs/share"
CONTENT_DIR="./installs/content"

# Verify we're in the project root
if [ ! -f docker-compose.yaml ]; then
  echo "ERROR: Run this from the project root (where docker-compose.yaml lives)" >&2
  exit 1
fi

# Discover actual container names from docker-compose
ALFRESCO=$(docker compose ps -q alfresco 2>/dev/null | xargs docker inspect --format '{{.Name}}' 2>/dev/null | sed 's|^/||')
SHARE=$(docker compose ps -q share 2>/dev/null | xargs docker inspect --format '{{.Name}}' 2>/dev/null | sed 's|^/||')

if [ -z "$ALFRESCO" ]; then
  echo "ERROR: alfresco container not running (try: docker compose up -d)" >&2
  exit 1
fi

echo "Installing to: $ALFRESCO and $SHARE"

install_amps_and_jars() {
  local container="$1"
  local source_dir="$2"
  local webapp_dir="$3"
  local amps_dir="$4"

  local mmt_jar
  mmt_jar=$(docker exec "$container" bash -c 'ls /usr/local/tomcat/alfresco-mmt/alfresco-mmt-*.jar 2>/dev/null | head -1' | tr -d '\r')
  if [ -z "$mmt_jar" ]; then
    echo "ERROR: MMT not found in $container" >&2
    return 1
  fi

  find "$source_dir" -type f \( -name '*.jar' -o -name '*.amp' \) | while read -r file; do
    if [[ "$file" == *.jar ]]; then
      echo "  Installing JAR: $file"
      docker cp "$file" "$container:/usr/local/tomcat/webapps/$webapp_dir/WEB-INF/lib/"
    elif [[ "$file" == *.amp ]]; then
      echo "  Installing AMP: $file"
      docker cp "$file" "$container:/usr/local/tomcat/$amps_dir/"
      docker exec --user root "$container" java -jar "$mmt_jar" install \
        "/usr/local/tomcat/$amps_dir" \
        "/usr/local/tomcat/webapps/$webapp_dir" \
        -directory -nobackup -force
    fi
  done
}

install_amps_and_jars "$ALFRESCO" "$CONTENT_DIR" "alfresco" "amps"
install_amps_and_jars "$SHARE"     "$SHARE_DIR"   "share"   "amps_share"

echo "Install complete. Restarting containers..."
docker restart "$ALFRESCO" "$SHARE"
echo "Done. Waiting for Alfresco to become ready..."
docker compose exec -T alfresco bash -c '
  for i in $(seq 1 60); do
    curl -sf http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1/probes/-ready- >/dev/null 2>&1 && exit 0
    sleep 5
  done
  exit 1
' 2>/dev/null && echo "Alfresco is ready." || echo "WARNING: Timed out waiting for readiness."
