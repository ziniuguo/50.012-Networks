run: sudo docker-compose up

then run the http requests. they are the tests

they fulfill all checkoff requirements


idempotent:

get requests

for redis and my code, post requests are also idempotent, it won't create duplicate records

delete is not, I return 404 if deleted already