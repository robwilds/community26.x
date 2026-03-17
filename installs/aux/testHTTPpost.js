//Run this inside javascript console in alfresco admin area
var triggerEndPoint = "https://httpbin.org/post";
var contentType = "application/x-www-form-urlencoded";
var token = "1234";

var theBody = '{"ref" : "1234"}';

var res2 = http2.post(
  triggerEndPoint,
  theBody,
  contentType,
  "Authorization",
  token
);

logger.log("The second response " + res2);
