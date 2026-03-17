//Run this inside javascript console in alfresco admin area
var triggerEndPoint = "http://queryalfapi:9600/chat";
var contentType = "application/json";
var token = "";

var theBody =
  '{"prompt":"historian providing brief feedback.  No more than 20 words","question":"are you there?"}';

var res2 = http2.post(
  triggerEndPoint,
  theBody,
  contentType,
  "Authorization",
  token
);
logger.log("response " + res2);
