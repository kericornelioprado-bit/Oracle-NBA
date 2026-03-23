keri@2806-107e-001d-3309-767a-5a1f-87d4-f446:~/projects/Oracle_NBA$ curl -i -H "Authorization: Bearer $(gcloud auth print-identity-token)" $(gcloud run services describe oracle-nba-service --region us-central1 --format='value(status.url)')
HTTP/2 200 
content-type: application/json
x-cloud-trace-context: 9d38ad38ea71c7a21b8c0a8036a8387d;o=1
date: Mon, 23 Mar 2026 23:44:48 GMT
server: Google Frontend
content-length: 55
alt-svc: h3=":443"; ma=2592000,h3-29=":443"; ma=2592000

{"message":"Predicciones enviadas","status":"success"}
keri@2806-107e-001d-3309-767a-5a1f-87d4-f446:~/projects/Oracle_NBA$ 