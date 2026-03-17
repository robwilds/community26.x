# Info

This is a build of Alfresco community 26.x with ldap, a python mcp server and ldap server and other goodies.

https://connect.hyland.com/t5/alfresco-blog/alfresco-community-edition-26-1-release-notes/ba-p/497107

# Getting Started

Run "docker compose up -d" from command line within the root directory of this project.

Login with demo/demo.

After services start you can run ./install_all.sh in the root to load up
OOTBEE tools (https://github.com/OrderOfTheBee/ootbee-support-tools)
and a mechanism to execute httpclient style transactions from a javascript in a rule. There's also a custom hyland theme jar - select the theme from the admin view

Pretty straight forward...

### note

There's a container called wildsalfmcp that will start up an MCP server for use with coPilot or Clause desktop etc.

If you want to run a local model with a dedicated chat client, you must install ollama on your computer. Once installed pull a model in terminal (ollama pull llama3). The start (or restart) the doocker services. You can access the open-webui interface with http://localhost:3000. Configure the tools under settings to point to http://localhost:8001
