Welcome to the UC Davis dARChr statuspage!

This webpage displays the results of gem5 tests. To view the tests:

  1) Generate the JSON file by running gem5art/run/bin/gem5art-getruns, call the JSON file  data.json.
  2) Either move the JSON file to the status directory (recomended) OR change the JSONpath variable in the statusPage.html document to the path to the JSON file.
  3) Spin up a Python virtual machine.
  4) Serve the HTML on port 8000 by typing python -m http.server 8000.
  5) Enter the URL http://169.237.7.85:8000/statusPage.html into a browser to view the page!

