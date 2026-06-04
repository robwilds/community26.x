<%-- #%L Alfresco ROOT Web Application %% Copyright (C) 2005 - 2023 Alfresco
Software Limited %% This file is part of the Alfresco software. If the software
was purchased under a paid Alfresco license, the terms of the paid license
agreement will prevail. Otherwise, the software is provided under the following
open source license terms: Alfresco is free software: you can redistribute it
and/or modify it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. Alfresco is distributed in the hope that it
will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
Public License for more details. You should have received a copy of the GNU
Lesser General Public License along with Alfresco. If not, see
<http://www.gnu.org/licenses/>. #L% --%> <%@page isErrorPage="true"
session="true" import="jakarta.servlet.ServletContext,
jakarta.servlet.RequestDispatcher" %><% boolean alfrescoInstalled = false;
String alfrescoContextName = "alfresco"; ServletContext alfrescoContext =
application.getContext("/"+alfrescoContextName); if( (alfrescoContext != null)
&& !alfrescoContext.equals(getServletConfig().getServletContext()) ) {
alfrescoInstalled = true; } if(request.getMethod().equals("PROPFIND") ||
request.getMethod().equals("OPTIONS")) { if(alfrescoInstalled) {
RequestDispatcher rd =
alfrescoContext.getRequestDispatcher("/AosResponder_ServerRoot"); if(rd != null)
{ rd.forward(request, response); return; } } } %><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Alfresco</title>
    <link rel="stylesheet" type="text/css" href="./css/reset.css" />
    <link rel="stylesheet" type="text/css" href="./css/alfresco.css" />
  </head>
  <body>
    <div class="sticky-wrapper">
      <div class="index">
        <div class="title">
          <span class="logo"
            ><a href="http://www.alfresco.com"
              ><img
                src="./images/logo/logo.png"
                width="145"
                height="48"
                alt=""
                border="0" /></a
          ></span>
          <span class="logo-separator">&nbsp;</span>
          <h1>Welcome to Alfresco</h1>
        </div>

        <div class="index-list">
          <h2>Core Features</h2>
          <p>
            <a href="http://docs.alfresco.com/" target="_blank"
              >Online Documentation</a
            >
          </p>
          <p></p>
          <% if(alfrescoInstalled) { %>
          <p>
            <a href="/<%=alfrescoContextName%>" target="_blank"
              >Alfresco Repository</a
            >
          </p>
          <p></p>
          <p><a href="/share" target="_blank">Share</a></p>
          <p></p>
          <p><a href="/control-center" target="_blank">Control Center</a></p>
          <p></p>
          <!--p><a href="/activiti-app" target="_blank">Process Services</a></a></p>
          <p></p>
          <p><a href="/activiti-admin" target="_blank">Process Admin</a></a></p>
         <p></p-->
          <p><a href="/content-app" target="_blank">Content App</a></p>
          <p></p>
          <p><a href="/api-explorer" target="_blank">API explorer</a></p>
          <p></p>
          <p>
            <a href="/gs-api-explorer" target="_blank"
              >Governace API explorer</a
            >
          </p>
          <p></p>

          <h2>Customizations</h2>
          <p>
            <a
              href=""
              onclick="window.open('http://'+ window.location.hostname + ':9999')"
              >Dozzle Container Monitoring</a
            >
          </p>
          <p></p>
          <p>
            <a
              href=""
              onclick="window.open('http://'+ window.location.hostname + ':3000')"
              >OpenWebUI for AI Chat</a
            >
          </p>
          <p></p>
          <p>
            <a
              href=""
              onclick="window.open('http://'+ window.location.hostname + ':8001/docs')"
              >MCP openai Server for Alfresco</a
            >
          </p>
          <p></p>
          <p>
            <a
              href=""
              onclick="window.open('http://'+ window.location.hostname + ':8400')"
              >LDAP config</a
            >
          </p>
          <p></p>
          <p>
            <a
              href=""
              onclick="window.open('http://'+ window.location.hostname + ':8800')"
              >Email Client</a
            >
          </p>

          <% } else { %>
          <p>
            <b>Cannot find Alfresco Repository on this server.</b> (Does this
            application have access to alfresco-global.properties? Does this
            application have cross-context permissions?)
          </p>
          <p></p>
          <% } %>
        </div>
      </div>
      <iframe src="http://localhost:9999" width="100%" height="800px"></iframe>

      <div class="push"></div>
    </div>
    <div class="footer">
      Alfresco Software, Inc. &copy; 2005-2023 All rights reserved.
    </div>
  </body>
  <script>
    console.log(window.location.hostname);
  </script>
</html>
