all:
	rm -rf api
	epydoc --output api --no-frames --graph=all \
	  --name="SNAKES is the Net Algebra Kit for Editors and Simulators" \
	  --navlink='<img alt="SNAKES logo" src="snakes-logo.jpg" width="120" height="120"/>' \
          --no-private ../snakes
	convert ../logo/snakes-logo.png -background white -scale 120x120 ./api/snakes-logo.jpg
