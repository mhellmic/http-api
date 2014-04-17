
## Preparation
mkdir /tmp/http_server
echo "Hello, I am a small testfile" > /tmp/http_server/testfile
mkdir /tmp/http_server/testfolder
echo "Hello, I am a small testfile in a nested directory" > /tmp/http_server/testfile

# create 100k dir
# put h1big.root in /tmp

## HTTP/CDMI interface

# 1. list folder in a browser
# go to http://localhost:5000/tmp/http_server
# type in username, password
# navigate into the folder testfolder
# go back
# navigate into the folder 100k

# 2. list folder with curl
curl -u testname:testpass http://localhost:5000/tmp/http_server/

# 3. list folder with curl json
curl -u testname:testpass -H 'accept: application/json' http://localhost:5000/tmp/http_server/

# 4. put file with curl, then list folder
curl -X PUT -u testname:testpass -H 'accept: application/json' http://localhost:5000/tmp/h1big.root /tmp/http_server/h1big.root
curl -u testname:testpass -H 'accept: application/json' http://localhost:5000/tmp/http_server/
# go to http://localhost:5000/tmp/http_server

# 5. get a folder with cdmi
curl -u testname:testpass -H 'accept: application/cdmi-container' -H 'X-CDMI-Specification-Version: 1.0.2' http://localhost:5000/tmp/h1big.root /tmp/http_server/

# 6. get a file with cdmi
curl -u testname:testpass -H 'accept: application/cdmi-container' -H 'X-CDMI-Specification-Version: 1.0.2' http://localhost:5000/tmp/h1big.root /tmp/http_server/h1big.root


## Registering workflow

# 7. Register a file
# go to http://localhost:5000/request/ in a new tab
# go back to the other tab with http://localhost:5000/tmp/http_server
# pick a file with right-click, copy link, paste into register box
# follow the workflow, explain :)
# copy the pid link, paste in new tab, explain
# go to get the file

# 8. Register from the command line
curl -X POST -u testname:testpass -H 'accept: application/json' http://localhost:5000/request/ --data 'src_url=http://localhost:5000/tmp/http_server/h1big.root'
