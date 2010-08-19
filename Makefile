all:
	@echo "Commands:"
	@echo "  release    prepare source for release"
	@echo "  tgz        build a source tarball"
	@echo "  doc        build API documentation"
	@echo "  dput       build and upload Ubuntu packages"
	@echo "  clean      delete some garbage files"
	@echo "  test       run tests through supported Python implementations"
	@echo "  next-deb   increments debian/VERSION"
	@echo "  next-ppa   increments debian/PPA"

committed:
	bzr status -SV|wc -l|grep -q '^0$$'

next-deb:
	echo 1 > debian/PPA
	echo $$((1+$$(cat debian/VERSION))) > debian/VERSION

next-ppa:
	echo $$((1+$$(cat debian/PPA))) > debian/PPA

release: committed test doc tgz
	bzr tag --delete $$(bzr tags|head -n 1|awk '{print $$1}')
	bzr tag version-$$(cat VERSION)
	echo 1 > debian/PPA
	echo 1 > debian/VERSION
	bzr add doc/api/*
	bzr commit -m "version $$(cat VERSION)"
	bzr push

tgz: committed
	bzr export --root=snakes-$$(cat VERSION)-$$(cat debian/VERSION) snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar.gz
	gpg --armor --sign --detach-sig snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar.gz

doc: snakes/*.py snakes/plugins/*.py snakes/utils/*.py snakes/compyler/*.py
	make -C doc

dput.sh: VERSION debian/*
	python mkdeb.py

dput: committed dput.sh
	sh dput.sh

clean:
	rm -f $$(find . -name ",*")
	rm -f $$(find . -name "*.pyc")
	rm -f $$(find . -name "*~")
	rm -f $$(find . -name "*.class")

test:
	python2.5 test.py
	python2.6 test.py
	unladen test.py
	pypy test.py
	spypy test.py
	stackless test.py
	jython test.py
